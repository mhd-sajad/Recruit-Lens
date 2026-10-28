"""
Resume Skill Extractor with Citation Evidence and Taxonomy Inference

Extracts both explicit skills (anchored to chunk IDs and character offsets)
and inferred skills (derived from taxonomy parent-child/framework-language relations)
with calibrated confidence values.
"""

from collections.abc import Sequence

from pydantic import BaseModel, Field

from app.core.models import ResumeChunk, ResumeParseResult
from app.core.resume_chunker import chunk_resume
from app.core.taxonomy import SkillTaxonomy


class SkillEvidence(BaseModel):
    """Exact citation provenance for an extracted skill occurrence."""

    chunk_id: str
    section: str
    snippet: str
    char_start: int
    char_end: int


class ExtractedSkill(BaseModel):
    """Structured candidate skill with explicit provenance or inference metadata."""

    skill: str
    canonical_name: str
    family: str
    is_inferred: bool = False
    confidence: float = 1.0  # 1.0 for explicit, <1.0 for inferred
    inferred_from: str | None = None
    occurrences: int = 1
    evidence: list[SkillEvidence] = Field(default_factory=list)


class CandidateSkillsResult(BaseModel):
    """Unified collection of candidate skills segregated by provenance."""

    resume_id: str
    explicit_skills: dict[str, ExtractedSkill] = Field(default_factory=dict)
    inferred_skills: dict[str, ExtractedSkill] = Field(default_factory=dict)
    all_canonical_skills: set[str] = Field(default_factory=set)


def extract_skills_from_chunks(
    resume_id: str,
    chunks: Sequence[ResumeChunk],
    taxonomy: SkillTaxonomy | None = None,
) -> CandidateSkillsResult:
    """
    Extract explicit skills with exact citation provenance across chunks,
    and derive inferred skills with calibrated confidence scores.
    """
    if taxonomy is None:
        taxonomy = SkillTaxonomy.get_instance()

    explicit_map: dict[str, ExtractedSkill] = {}

    for chunk in chunks:
        text = chunk.text
        extracted_items = taxonomy.extract_skills_from_text(text)

        for item in extracted_items:
            canon = item["skill"]
            canon_lower = canon.lower()
            family = item.get("family", "General Technology")

            for start, end in item["spans"]:
                # Generate surrounding context snippet (~40 chars on each side)
                snip_start = max(0, start - 40)
                snip_end = min(len(text), end + 40)
                snippet = text[snip_start:snip_end].strip()

                evidence = SkillEvidence(
                    chunk_id=chunk.chunk_id,
                    section=chunk.section,
                    snippet=snippet,
                    char_start=start,
                    char_end=end,
                )

                if canon_lower not in explicit_map:
                    explicit_map[canon_lower] = ExtractedSkill(
                        skill=canon,
                        canonical_name=canon,
                        family=family,
                        is_inferred=False,
                        confidence=1.0,
                        inferred_from=None,
                        occurrences=1,
                        evidence=[evidence],
                    )
                else:
                    explicit_map[canon_lower].occurrences += 1
                    explicit_map[canon_lower].evidence.append(evidence)

    # 2. Derive inferred skills
    inferred_map: dict[str, ExtractedSkill] = {}

    for explicit_skill in explicit_map.values():
        relations = taxonomy.get_inferred_skills(explicit_skill.canonical_name)
        for inf_name, conf in relations:
            inf_lower = inf_name.lower()
            # If already explicitly matched, explicit takes precedence (confidence 1.0)
            if inf_lower in explicit_map:
                continue

            # If already inferred with lower confidence, upgrade confidence
            if inf_lower in inferred_map:
                if conf > inferred_map[inf_lower].confidence:
                    inferred_map[inf_lower].confidence = conf
                    inferred_map[inf_lower].inferred_from = explicit_skill.canonical_name
            else:
                inferred_map[inf_lower] = ExtractedSkill(
                    skill=inf_name,
                    canonical_name=inf_name,
                    family=taxonomy.get_family(inf_name),
                    is_inferred=True,
                    confidence=conf,
                    inferred_from=explicit_skill.canonical_name,
                    occurrences=1,
                    evidence=list(explicit_skill.evidence[:1]),  # Anchor to parent's evidence
                )

    all_canonical = set(explicit_map.keys()) | set(inferred_map.keys())

    return CandidateSkillsResult(
        resume_id=resume_id,
        explicit_skills=explicit_map,
        inferred_skills=inferred_map,
        all_canonical_skills=all_canonical,
    )


def extract_skills_from_parsed_resume(
    parsed_resume: ResumeParseResult,
    taxonomy: SkillTaxonomy | None = None,
) -> CandidateSkillsResult:
    """Extract skills directly from a ResumeParseResult by first converting to chunks."""
    chunks = chunk_resume(parsed_resume)
    return extract_skills_from_chunks(
        resume_id=parsed_resume.resume_id,
        chunks=chunks,
        taxonomy=taxonomy,
    )
