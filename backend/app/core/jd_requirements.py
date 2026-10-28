"""
Job Description Requirement Extractor

Extracts structured job requirements:
- Section segmentation (Requirements vs Preferred vs Responsibilities)
- Years of experience (min and max)
- Education requirement (ordinal rank 0-4)
- Must-have vs Nice-to-have skills via taxonomy matching and cue words
- Typed JobRequirements output with Batch 3 LLM refinement hook
"""

import re
from typing import Any

from pydantic import BaseModel, Field

from app.core.taxonomy import SkillTaxonomy

MUST_HAVE_HEADERS = [
    "requirements",
    "basic qualifications",
    "minimum qualifications",
    "required qualifications",
    "required experience",
    "required skills",
    "what you'll need",
    "what you need",
    "must have",
    "who you are",
    "qualifications",
]

NICE_TO_HAVE_HEADERS = [
    "preferred qualifications",
    "preferred skills",
    "bonus qualifications",
    "nice to have",
    "preferred experience",
    "bonus points",
    "what will set you apart",
    "what sets you apart",
    "desired skills",
    "additional qualifications",
]

MUST_HAVE_CUES = [
    r"\brequired\b",
    r"\bmust\s+have\b",
    r"\bmust\s+possess\b",
    r"\bessential\b",
    r"\bminimum\b",
    r"\bmandatory\b",
    r"\bneeds?\s+to\s+have\b",
]

NICE_TO_HAVE_CUES = [
    r"\bpreferred\b",
    r"\bplus\b",
    r"\bbonus\b",
    r"\bnice\s+to\s+have\b",
    r"\bideally\b",
    r"\badvantage\b",
    r"\bdesirable\b",
    r"\boptional\b",
    r"\bgreat\s+to\s+have\b",
]

DEGREE_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\b(ph\.?d|doctorate|doctoral)\b", re.IGNORECASE), 4, "Doctorate"),
    (re.compile(r"\b(master'?s?|m\.?s|m\.?tech|mca|m\.?eng|mba)\b", re.IGNORECASE), 3, "Master"),
    (
        re.compile(
            r"\b(bachelor'?s?|b\.?s|b\.?tech|b\.?e|bba|undergraduate degree)\b", re.IGNORECASE
        ),
        2,
        "Bachelor",
    ),
    (re.compile(r"\b(associate'?s?|a\.?s)\b", re.IGNORECASE), 1, "Associate"),
]

YEARS_PATTERNS = [
    re.compile(
        r"(\d+)\s*(?:-|to)\s*(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+experience)?",
        re.IGNORECASE,
    ),
    re.compile(r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+experience)?", re.IGNORECASE),
    re.compile(r"at\s+least\s+(\d+)\s*(?:years?|yrs?)", re.IGNORECASE),
    re.compile(r"minimum\s+(?:of\s+)?(\d+)\s*(?:years?|yrs?)", re.IGNORECASE),
]


class JobRequirements(BaseModel):
    """Typed structured requirements extracted from a Job Description."""

    job_id: str | None = None
    title: str | None = None
    min_years_experience: float = 0.0
    max_years_experience: float | None = None
    min_education_rank: int = 0  # 0=None/HS, 1=Associate, 2=Bachelor, 3=Master, 4=Doctorate
    min_education_name: str | None = None
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    raw_sections: dict[str, str] = Field(default_factory=dict)
    confidence: float = 1.0
    llm_refined: bool = False


def segment_jd_sections(jd_text: str) -> dict[str, str]:
    """Segment raw job description into canonical functional sections."""
    lines = [line.strip() for line in jd_text.split("\n")]
    sections: dict[str, list[str]] = {"general": []}
    current_sec = "general"

    for line in lines:
        if not line:
            continue
        line_clean = line.strip().rstrip(":").lower()

        # Check section transitions
        matched_section = None
        for h in NICE_TO_HAVE_HEADERS:
            if h in line_clean and len(line_clean) < 40:
                matched_section = "nice_to_have"
                break
        if not matched_section:
            for h in MUST_HAVE_HEADERS:
                if h in line_clean and len(line_clean) < 40:
                    matched_section = "must_have"
                    break

        if matched_section:
            current_sec = matched_section
            if current_sec not in sections:
                sections[current_sec] = []
            continue

        sections[current_sec].append(line)

    return {k: "\n".join(v) for k, v in sections.items() if v}


def extract_years_of_experience(text: str) -> tuple[float, float | None]:
    """Extract minimum and optional maximum years of experience from text."""
    min_years = 0.0
    max_years = None

    for pattern in YEARS_PATTERNS:
        match = pattern.search(text)
        if match:
            groups = match.groups()
            if len(groups) == 2 and groups[1] is not None:
                min_years = float(groups[0])
                max_years = float(groups[1])
                return min_years, max_years
            elif len(groups) >= 1 and groups[0] is not None:
                min_years = float(groups[0])
                return min_years, None

    return min_years, max_years


def extract_education_requirement(text: str) -> tuple[int, str | None]:
    """Extract minimum required education rank and degree name."""
    for pattern, rank, deg_name in DEGREE_PATTERNS:
        if pattern.search(text):
            return rank, deg_name
    return 0, None


def extract_job_requirements(
    jd_text: str,
    job_id: str | None = None,
    title: str | None = None,
    taxonomy: SkillTaxonomy | None = None,
) -> JobRequirements:
    """
    Parse free-text JD and produce validated, typed JobRequirements.
    """
    if taxonomy is None:
        taxonomy = SkillTaxonomy.get_instance()

    sections = segment_jd_sections(jd_text)

    # 1. Experience years
    min_yrs, max_yrs = extract_years_of_experience(jd_text)

    # 2. Education requirement
    edu_rank, edu_name = extract_education_requirement(jd_text)

    # 3. Skills classification
    must_haves: set[str] = set()
    nice_to_haves: set[str] = set()

    for sec_name, sec_text in sections.items():
        lines = [line.strip() for line in sec_text.split("\n") if line.strip()]
        for line in lines:
            line_lower = line.lower()
            has_nice_cue = any(re.search(cue, line_lower) for cue in NICE_TO_HAVE_CUES)
            has_must_cue = any(re.search(cue, line_lower) for cue in MUST_HAVE_CUES)
            is_nice = (sec_name == "nice_to_have") or has_nice_cue
            is_must = (sec_name == "must_have") or has_must_cue

            extracted = taxonomy.extract_skills_from_text(line)
            for item in extracted:
                skill_name = item["skill"]
                if is_nice and not is_must:
                    nice_to_haves.add(skill_name)
                else:
                    must_haves.add(skill_name)

    # Resolve overlaps: if a skill is explicitly marked must-have anywhere, it remains must-have
    nice_to_haves = nice_to_haves - must_haves

    return JobRequirements(
        job_id=job_id,
        title=title,
        min_years_experience=min_yrs,
        max_years_experience=max_yrs,
        min_education_rank=edu_rank,
        min_education_name=edu_name,
        must_have_skills=sorted(must_haves),
        nice_to_have_skills=sorted(nice_to_haves),
        raw_sections=sections,
        confidence=0.9 if must_haves else 0.6,
        llm_refined=False,
    )


def refine_requirements_with_llm(reqs: JobRequirements, llm_client: Any = None) -> JobRequirements:
    """
    Batch 3 Hook: Refines extracted requirements using LLM critique and disambiguation.
    Passes through unchanged when no LLM client is configured.
    """
    if llm_client is None:
        return reqs
    # In Batch 3, prompt LLM to confirm must-haves vs nice-to-haves and return validated JSON
    return reqs
