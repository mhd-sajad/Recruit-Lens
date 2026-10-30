"""
Feature Vector Extractor for Candidate Scoring

Computes explainable, bounded candidate features with:
- Strict defined ranges [min_bound, max_bound]
- Calibrated confidence values (0.0 to 1.0)
- Explicit missing-data handling (never silently 0; flagged with is_missing & reason)
- Keyword stuffing guard: repeated mentions of a skill never increase coverage or count
"""

import re

import numpy as np
from pydantic import BaseModel, Field

from app.core.experience_extractor import extract_years_of_experience
from app.core.jd_requirements import JobRequirements
from app.core.models import ResumeParseResult
from app.core.skill_extractor import CandidateSkillsResult, extract_skills_from_parsed_resume
from app.core.taxonomy import SkillTaxonomy


class FeatureValue(BaseModel):
    """A bounded numerical feature with explicit confidence and missing-data provenance."""

    name: str
    value: float
    confidence: float = 1.0
    is_missing: bool = False
    missing_reason: str | None = None
    min_bound: float
    max_bound: float

    def get_clamped_value(self) -> float:
        """Clamp value to strictly guaranteed bounds."""
        return float(np.clip(self.value, self.min_bound, self.max_bound))


class CandidateFeatureVector(BaseModel):
    """Complete structured feature vector representing a candidate-job comparison."""

    resume_id: str
    job_id: str | None = None

    must_have_coverage: FeatureValue
    nice_to_have_coverage: FeatureValue
    matched_must_count: FeatureValue
    matched_nice_count: FeatureValue
    inferred_count: FeatureValue
    missing_must_count: FeatureValue
    years_gap: FeatureValue
    seniority_gap: FeatureValue
    education_match: FeatureValue
    title_match: FeatureValue
    skill_recency: FeatureValue
    dense_similarity: FeatureValue

    # Audit & anti-cheat metrics
    matched_must_skills: list[str] = Field(default_factory=list)
    missing_must_skills: list[str] = Field(default_factory=list)
    matched_nice_skills: list[str] = Field(default_factory=list)
    inferred_skills_used: list[str] = Field(default_factory=list)
    total_raw_skill_mentions: int = 0
    unique_skills_matched: int = 0

    def to_feature_dict(self) -> dict[str, float]:
        """Convert bounded features to key-value float dictionary for ML/scoring."""
        return {
            "must_have_coverage": self.must_have_coverage.get_clamped_value(),
            "nice_to_have_coverage": self.nice_to_have_coverage.get_clamped_value(),
            "matched_must_count": self.matched_must_count.get_clamped_value(),
            "matched_nice_count": self.matched_nice_count.get_clamped_value(),
            "inferred_count": self.inferred_count.get_clamped_value(),
            "missing_must_count": self.missing_must_count.get_clamped_value(),
            "years_gap": self.years_gap.get_clamped_value(),
            "seniority_gap": self.seniority_gap.get_clamped_value(),
            "education_match": self.education_match.get_clamped_value(),
            "title_match": self.title_match.get_clamped_value(),
            "skill_recency": self.skill_recency.get_clamped_value(),
            "dense_similarity": self.dense_similarity.get_clamped_value(),
        }

    def to_numpy_array(self) -> np.ndarray:
        """Convert ordered feature vector to 1D float32 numpy array."""
        d = self.to_feature_dict()
        ordered_keys = [
            "must_have_coverage",
            "nice_to_have_coverage",
            "matched_must_count",
            "matched_nice_count",
            "inferred_count",
            "missing_must_count",
            "years_gap",
            "seniority_gap",
            "education_match",
            "title_match",
            "skill_recency",
            "dense_similarity",
        ]
        return np.array([d[k] for k in ordered_keys], dtype=np.float32)


def compute_title_similarity(target_title: str | None, past_titles: list[str]) -> float:
    """Compute token Jaccard similarity between target JD title and candidate past titles."""
    if not target_title or not past_titles:
        return 0.0

    target_tokens = set(re.findall(r"\w+", target_title.lower()))
    if not target_tokens:
        return 0.0

    max_sim = 0.0
    for pt in past_titles:
        pt_tokens = set(re.findall(r"\w+", pt.lower()))
        if not pt_tokens:
            continue
        sim = len(target_tokens & pt_tokens) / len(target_tokens | pt_tokens)
        if sim > max_sim:
            max_sim = sim

    return float(max_sim)


def infer_seniority_level(title: str | None) -> int:
    """Infer seniority rank (0=Entry, 1=Junior, 2=Mid, 3=Senior, 4=Staff/Director)."""
    if not title:
        return 2  # Default to Mid
    t = title.lower()
    lead_keywords = ["principal", "director", "vp", "head", "chief", "executive", "architect"]
    if any(w in t for w in lead_keywords):
        return 4
    if any(w in t for w in ["senior", "sr", "lead", "staff", "manager"]):
        return 3
    if any(w in t for w in ["junior", "jr", "associate", "intern", "entry"]):
        return 1
    return 2


def extract_candidate_features(
    parsed_resume: ResumeParseResult,
    job_reqs: JobRequirements,
    candidate_skills: CandidateSkillsResult | None = None,
    dense_similarity_score: float | None = None,
    taxonomy: SkillTaxonomy | None = None,
) -> CandidateFeatureVector:
    """
    Extract bounded, explainable feature vector for a candidate evaluated against a job.
    Enforces the keyword stuffing guard (set-based matching per distinct skill).
    """
    if taxonomy is None:
        taxonomy = SkillTaxonomy.get_instance()

    if candidate_skills is None:
        candidate_skills = extract_skills_from_parsed_resume(parsed_resume, taxonomy=taxonomy)

    # 1. Must-Have & Nice-to-Have Skill Matching (Keyword Stuffing Guard Enforced)
    req_must = set(job_reqs.must_have_skills)
    req_nice = set(job_reqs.nice_to_have_skills)

    matched_must: list[str] = []
    missing_must: list[str] = []
    matched_nice: list[str] = []
    inferred_used: list[str] = []

    # Map all candidate skills (explicit and inferred) by canonical lower name
    cand_explicit = candidate_skills.explicit_skills
    cand_inferred = candidate_skills.inferred_skills

    total_mentions = sum(s.occurrences for s in cand_explicit.values())

    def resolve_key(s_name: str) -> str:
        canon = taxonomy.canonicalize(s_name)
        return canon.lower() if canon else s_name.lower()

    for skill in req_must:
        s_key = resolve_key(skill)
        if s_key in cand_explicit or skill.lower() in cand_explicit:
            matched_must.append(skill)
        elif s_key in cand_inferred or skill.lower() in cand_inferred:
            matched_must.append(skill)
            inferred_used.append(skill)
        else:
            missing_must.append(skill)

    for skill in req_nice:
        s_key = resolve_key(skill)
        if s_key in cand_explicit or skill.lower() in cand_explicit:
            matched_nice.append(skill)
        elif s_key in cand_inferred or skill.lower() in cand_inferred:
            matched_nice.append(skill)
            inferred_used.append(skill)

    # Compute coverage features
    if len(req_must) > 0:
        must_cov_val = len(matched_must) / len(req_must)
        must_cov = FeatureValue(
            name="must_have_coverage",
            value=must_cov_val,
            confidence=1.0,
            is_missing=False,
            min_bound=0.0,
            max_bound=1.0,
        )
    else:
        must_cov = FeatureValue(
            name="must_have_coverage",
            value=1.0,
            confidence=0.5,
            is_missing=True,
            missing_reason="JD has no explicitly parsed must-have skills",
            min_bound=0.0,
            max_bound=1.0,
        )

    if len(req_nice) > 0:
        nice_cov_val = len(matched_nice) / len(req_nice)
        nice_cov = FeatureValue(
            name="nice_to_have_coverage",
            value=nice_cov_val,
            confidence=1.0,
            is_missing=False,
            min_bound=0.0,
            max_bound=1.0,
        )
    else:
        nice_cov = FeatureValue(
            name="nice_to_have_coverage",
            value=1.0,
            confidence=0.5,
            is_missing=True,
            missing_reason="JD has no explicitly parsed nice-to-have skills",
            min_bound=0.0,
            max_bound=1.0,
        )

    matched_must_count_feat = FeatureValue(
        name="matched_must_count",
        value=float(len(matched_must)),
        confidence=1.0,
        is_missing=False,
        min_bound=0.0,
        max_bound=50.0,
    )

    matched_nice_count_feat = FeatureValue(
        name="matched_nice_count",
        value=float(len(matched_nice)),
        confidence=1.0,
        is_missing=False,
        min_bound=0.0,
        max_bound=50.0,
    )

    inferred_count_feat = FeatureValue(
        name="inferred_count",
        value=float(len(inferred_used)),
        confidence=0.85,
        is_missing=False,
        min_bound=0.0,
        max_bound=50.0,
    )

    missing_must_count_feat = FeatureValue(
        name="missing_must_count",
        value=float(len(missing_must)),
        confidence=1.0,
        is_missing=False,
        min_bound=0.0,
        max_bound=50.0,
    )

    # 2. Years Gap Feature
    cand_total_years = 0.0
    has_duration = False
    for exp in parsed_resume.experiences:
        if exp.duration_months is not None:
            cand_total_years += exp.duration_months / 12.0
            has_duration = True

    if not has_duration:
        extracted_yrs = extract_years_of_experience(
            parsed_resume.sections.get("experience", "") or parsed_resume.scoring_text
        )
        if extracted_yrs is not None:
            cand_total_years = extracted_yrs
            has_duration = True

    if has_duration and cand_total_years > 0.0:
        years_gap_val = cand_total_years - job_reqs.min_years_experience
        years_gap_feat = FeatureValue(
            name="years_gap",
            value=years_gap_val,
            confidence=0.9,
            is_missing=False,
            min_bound=-10.0,
            max_bound=15.0,
        )
    else:
        years_gap_feat = FeatureValue(
            name="years_gap",
            value=0.0,
            confidence=0.0,
            is_missing=True,
            missing_reason="Candidate experience dates could not be parsed",
            min_bound=-10.0,
            max_bound=15.0,
        )

    # 3. Seniority Gap Feature
    req_seniority = infer_seniority_level(job_reqs.title)
    cand_seniorities = [
        infer_seniority_level(e.title) for e in parsed_resume.experiences if e.title
    ]
    cand_max_seniority = max(cand_seniorities) if cand_seniorities else 2

    seniority_gap_val = float(cand_max_seniority - req_seniority)
    seniority_gap_feat = FeatureValue(
        name="seniority_gap",
        value=seniority_gap_val,
        confidence=0.85 if cand_seniorities else 0.4,
        is_missing=not bool(cand_seniorities),
        missing_reason="No past job titles extracted" if not cand_seniorities else None,
        min_bound=-4.0,
        max_bound=4.0,
    )

    # 4. Education Match Feature
    cand_max_edu_rank = max([e.ordinal_rank for e in parsed_resume.educations], default=0)
    req_edu_rank = job_reqs.min_education_rank

    if req_edu_rank == 0:
        edu_match_feat = FeatureValue(
            name="education_match",
            value=1.0,
            confidence=0.5,
            is_missing=True,
            missing_reason="No formal education requirement specified in JD",
            min_bound=0.0,
            max_bound=1.0,
        )
    elif cand_max_edu_rank >= req_edu_rank:
        edu_match_feat = FeatureValue(
            name="education_match",
            value=1.0,
            confidence=1.0,
            is_missing=False,
            min_bound=0.0,
            max_bound=1.0,
        )
    elif cand_max_edu_rank == req_edu_rank - 1:
        # Partial match within 1 rank (e.g. Bachelor applying for Master requirement)
        edu_match_feat = FeatureValue(
            name="education_match",
            value=0.5,
            confidence=0.9,
            is_missing=False,
            min_bound=0.0,
            max_bound=1.0,
        )
    else:
        edu_match_feat = FeatureValue(
            name="education_match",
            value=0.0,
            confidence=1.0,
            is_missing=False,
            min_bound=0.0,
            max_bound=1.0,
        )

    # 5. Title Match Feature
    past_titles = [e.title for e in parsed_resume.experiences if e.title]
    title_sim = compute_title_similarity(job_reqs.title, past_titles)
    title_match_feat = FeatureValue(
        name="title_match",
        value=title_sim,
        confidence=0.9 if past_titles else 0.0,
        is_missing=not bool(past_titles),
        missing_reason=(
            "No past structured job titles extracted from resume" if not past_titles else None
        ),
        min_bound=0.0,
        max_bound=1.0,
    )

    # 6. Skill Recency Feature
    # Measure fraction of matched skills appearing in recent experiences
    recent_skills = set()
    all_matched = {s.lower() for s in matched_must + matched_nice}
    if all_matched:
        for exp in parsed_resume.experiences[:2]:  # Top 2 most recent roles
            if exp.raw_text:
                exp_text_lower = exp.raw_text.lower()
                for s in all_matched:
                    if s in exp_text_lower:
                        recent_skills.add(s)
        recent_overlap = len(recent_skills & all_matched) / len(all_matched)
        skill_recency_feat = FeatureValue(
            name="skill_recency",
            value=float(recent_overlap),
            confidence=0.85 if recent_skills else 0.5,
            is_missing=False,
            min_bound=0.0,
            max_bound=1.0,
        )
    else:
        skill_recency_feat = FeatureValue(
            name="skill_recency",
            value=0.0,
            confidence=0.0,
            is_missing=True,
            missing_reason="Zero skills matched against JD",
            min_bound=0.0,
            max_bound=1.0,
        )

    # 7. Dense Semantic Similarity Feature
    if dense_similarity_score is not None:
        dense_feat = FeatureValue(
            name="dense_similarity",
            value=float(dense_similarity_score),
            confidence=1.0,
            is_missing=False,
            min_bound=0.0,
            max_bound=1.0,
        )
    else:
        dense_feat = FeatureValue(
            name="dense_similarity",
            value=0.5,
            confidence=0.0,
            is_missing=True,
            missing_reason="Dense embedding search score not provided",
            min_bound=0.0,
            max_bound=1.0,
        )

    return CandidateFeatureVector(
        resume_id=parsed_resume.resume_id,
        job_id=job_reqs.job_id,
        must_have_coverage=must_cov,
        nice_to_have_coverage=nice_cov,
        matched_must_count=matched_must_count_feat,
        matched_nice_count=matched_nice_count_feat,
        inferred_count=inferred_count_feat,
        missing_must_count=missing_must_count_feat,
        years_gap=years_gap_feat,
        seniority_gap=seniority_gap_feat,
        education_match=edu_match_feat,
        title_match=title_match_feat,
        skill_recency=skill_recency_feat,
        dense_similarity=dense_feat,
        matched_must_skills=matched_must,
        missing_must_skills=missing_must,
        matched_nice_skills=matched_nice,
        inferred_skills_used=inferred_used,
        total_raw_skill_mentions=total_mentions,
        unique_skills_matched=len(matched_must) + len(matched_nice),
    )
