"""
Metamorphic Robustness and Non-Discrimination Tests

Validates non-negotiable metamorphic properties of the scoring and tier engine:
1. Monotonicity: Adding a must-have skill never lowers score; removing one never raises it.
2. Demographic Invariance: Name, gender cues (pronouns, titles), email, or contact info
   leaves the score 100% mathematically identical.
3. Section Order Invariance: Reordering resume sections yields stable scoring.
4. Keyword Stuffing Guard: Repeating a matched skill 50 times provides exactly 0 gain.
5. Garbage / Non-Resume Handling: Corrupt, non-resume, or empty documents trigger Abstain.
"""

import copy

from app.core.features import extract_candidate_features
from app.core.jd_requirements import JobRequirements
from app.core.models import ContactPII, EducationEntry, ResumeParseResult, WorkExperienceEntry
from app.core.scoring import WeightedBaselineScorer
from app.core.taxonomy import SkillTaxonomy
from app.core.tiers import assign_candidate_tier


def create_base_candidate() -> ResumeParseResult:
    return ResumeParseResult(
        resume_id="cand_meta_01",
        is_resume=True,
        gate_confidence=1.0,
        gate_signals={"has_experience": True, "has_education": True, "has_skills": True},
        parse_confidence=0.95,
        page_count=2,
        layout_type="single_column",
        pii=ContactPII(name="David Miller", email="david.miller@example.com"),
        scoring_text=(
            "David Miller\n"
            "Software Engineer with 4 years experience in Python and PostgreSQL.\n"
            "Built scalable APIs and managed relational databases."
        ),
        raw_text=(
            "David Miller\n"
            "Software Engineer with 4 years experience in Python and PostgreSQL.\n"
            "Built scalable APIs and managed relational databases."
        ),
        sections={
            "summary": "Software Engineer with 4 years experience in Python and PostgreSQL.",
            "experience": (
                "Software Engineer at TechCorp (2020 - 2024). "
                "Developed backend Python microservices."
            ),
            "education": "B.S. in Computer Science, State University, 2020.",
            "skills": "Python, PostgreSQL, Git",
        },
        experiences=[
            WorkExperienceEntry(
                title="Software Engineer",
                company="TechCorp",
                duration_months=48,
                raw_text="Developed backend Python microservices.",
            )
        ],
        educations=[
            EducationEntry(
                degree="B.S. Computer Science",
                ordinal_rank=2,
                raw_text="B.S. Computer Science, 2020",
            )
        ],
        skills=["Python", "PostgreSQL", "Git"],
    )


def compute_cand_score(
    cand: ResumeParseResult,
    job: JobRequirements,
    taxonomy: SkillTaxonomy,
    scorer: WeightedBaselineScorer,
) -> float:
    feats = extract_candidate_features(cand, job, taxonomy=taxonomy)
    return scorer.score(feats).final_score


def test_property_adding_must_have_never_lowers_score() -> None:
    """Metamorphic Property 1: Adding a must-have skill must never decrease score."""
    taxonomy = SkillTaxonomy.get_instance()
    scorer = WeightedBaselineScorer()

    job = JobRequirements(
        title="Software Engineer",
        min_years_experience=3.0,
        must_have_skills=["Python", "Docker", "PostgreSQL"],
    )

    base_cand = create_base_candidate()
    base_score = compute_cand_score(base_cand, job, taxonomy, scorer)

    # Add must-have skill 'Docker' to candidate
    enhanced_cand = copy.deepcopy(base_cand)
    enhanced_cand.sections["skills"] += ", Docker"
    enhanced_cand.scoring_text += "\nDocker containerization"
    enhanced_cand.skills.append("Docker")

    enhanced_score = compute_cand_score(enhanced_cand, job, taxonomy, scorer)
    assert enhanced_score >= base_score, f"Lowered: {base_score} -> {enhanced_score}"


def test_property_removing_must_have_never_raises_score() -> None:
    """Metamorphic Property 2: Removing a must-have skill must never increase score."""
    taxonomy = SkillTaxonomy.get_instance()
    scorer = WeightedBaselineScorer()

    job = JobRequirements(
        title="Software Engineer",
        min_years_experience=3.0,
        must_have_skills=["Python", "PostgreSQL"],
    )

    base_cand = create_base_candidate()
    base_score = compute_cand_score(base_cand, job, taxonomy, scorer)

    # Remove 'Python' from candidate
    stripped_cand = copy.deepcopy(base_cand)
    stripped_cand.sections["skills"] = "PostgreSQL, Git"
    stripped_cand.scoring_text = stripped_cand.scoring_text.replace("Python", "legacy systems")
    stripped_cand.sections["experience"] = stripped_cand.sections["experience"].replace(
        "Python", "legacy systems"
    )
    stripped_cand.skills = ["PostgreSQL", "Git"]

    stripped_score = compute_cand_score(stripped_cand, job, taxonomy, scorer)
    assert stripped_score <= base_score, f"Raised: {base_score} -> {stripped_score}"


def test_property_demographic_and_blind_invariance() -> None:
    """Metamorphic Property 3: Changing name, gender cues, email leaves score 100% identical."""
    taxonomy = SkillTaxonomy.get_instance()
    scorer = WeightedBaselineScorer()

    job = JobRequirements(
        title="Software Engineer",
        min_years_experience=3.0,
        must_have_skills=["Python", "PostgreSQL"],
    )

    base_cand = create_base_candidate()
    base_score = compute_cand_score(base_cand, job, taxonomy, scorer)

    # Variations: Male cue, Female cue, Arabic name, Chinese name, Hispanic name
    variations = [
        (
            "Jane Doe",
            "jane.doe@example.com",
            "Ms. Jane Doe is an experienced engineer. She developed APIs.",
        ),
        ("Amina Al-Mansoor", "amina.mansoor@example.org", "Amina is an experienced engineer."),
        (
            "Wei Zhang",
            "wei.zhang@tech.cn",
            "Mr. Wei Zhang developed microservices. He managed databases.",
        ),
        ("Carlos Rodriguez", "carlos.r@correo.es", "Carlos has 4 years experience."),
    ]

    for name, email, intro in variations:
        cand_var = copy.deepcopy(base_cand)
        cand_var.pii.name = name
        cand_var.pii.email = email
        cand_var.scoring_text = intro + "\n" + cand_var.scoring_text

        var_score = compute_cand_score(cand_var, job, taxonomy, scorer)
        assert abs(var_score - base_score) < 1e-5, f"Demographic bias detected: {name}"


def test_property_section_reordering_stability() -> None:
    """Metamorphic Property 4: Section order reordering yields stable scores."""
    taxonomy = SkillTaxonomy.get_instance()
    scorer = WeightedBaselineScorer()

    job = JobRequirements(
        title="Software Engineer",
        min_years_experience=3.0,
        must_have_skills=["Python", "PostgreSQL"],
    )

    base_cand = create_base_candidate()
    base_score = compute_cand_score(base_cand, job, taxonomy, scorer)

    # Invert sections order: Education first, then Skills, then Experience, then Summary
    reordered_cand = copy.deepcopy(base_cand)
    reordered_cand.sections = {
        "education": base_cand.sections["education"],
        "skills": base_cand.sections["skills"],
        "experience": base_cand.sections["experience"],
        "summary": base_cand.sections["summary"],
    }

    reordered_score = compute_cand_score(reordered_cand, job, taxonomy, scorer)
    assert abs(reordered_score - base_score) < 1e-4, "Section reordering instability"


def test_property_keyword_stuffing_gives_zero_gain() -> None:
    """Metamorphic Property 5: Mentioning a skill 50 times yields zero score gain."""
    taxonomy = SkillTaxonomy.get_instance()
    scorer = WeightedBaselineScorer()

    job = JobRequirements(
        title="Software Engineer",
        min_years_experience=3.0,
        must_have_skills=["Python", "PostgreSQL"],
    )

    base_cand = create_base_candidate()
    base_score = compute_cand_score(base_cand, job, taxonomy, scorer)

    # Stuffed resume with 50 repetitions of 'Python'
    stuffed_cand = copy.deepcopy(base_cand)
    stuffed_text = "\n".join(["Python Python Python Python Python"] * 10)
    stuffed_cand.sections["skills"] += f"\n{stuffed_text}"
    stuffed_cand.scoring_text += f"\n{stuffed_text}"

    stuffed_score = compute_cand_score(stuffed_cand, job, taxonomy, scorer)
    assert abs(stuffed_score - base_score) < 1e-4, "Keyword stuffing exploit succeeded"


def test_property_garbage_and_empty_document_abstains() -> None:
    """Metamorphic Property 6: Empty or garbage documents strictly trigger Abstain."""
    job = JobRequirements(title="Software Engineer", must_have_skills=["Python"])

    # 1. Empty document
    empty_cand = ResumeParseResult(
        resume_id="cand_empty",
        is_resume=False,
        gate_confidence=0.0,
        gate_signals={},
        parse_confidence=0.0,
        page_count=0,
        layout_type="unknown",
        pii=ContactPII(),
        scoring_text="",
        raw_text="",
        sections={},
        experiences=[],
        educations=[],
        skills=[],
    )

    feats_empty = extract_candidate_features(empty_cand, job)
    score_empty = WeightedBaselineScorer().score(feats_empty)
    tier_empty = assign_candidate_tier(
        score_empty,
        feats_empty,
        parse_confidence=empty_cand.parse_confidence,
        is_verified_resume=empty_cand.is_resume,
    )

    assert tier_empty.tier == "Abstain"
    assert tier_empty.is_abstain

    # 2. Low parse confidence document
    garbage_cand = create_base_candidate()
    garbage_cand.parse_confidence = 0.25  # Below 0.50 threshold

    feats_garb = extract_candidate_features(garbage_cand, job)
    score_garb = WeightedBaselineScorer().score(feats_garb)
    tier_garb = assign_candidate_tier(
        score_garb,
        feats_garb,
        parse_confidence=garbage_cand.parse_confidence,
        is_verified_resume=garbage_cand.is_resume,
    )

    assert tier_garb.tier == "Abstain"
    assert tier_garb.is_abstain
