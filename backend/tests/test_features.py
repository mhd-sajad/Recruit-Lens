"""Unit tests for Feature Vector Extractor with Keyword Stuffing Guard."""

from app.core.features import (
    CandidateFeatureVector,
    compute_title_similarity,
    extract_candidate_features,
    infer_seniority_level,
)
from app.core.jd_requirements import JobRequirements
from app.core.models import ContactPII, EducationEntry, ResumeParseResult, WorkExperienceEntry


def create_sample_job_reqs() -> JobRequirements:
    return JobRequirements(
        job_id="job_dev_01",
        title="Senior Software Engineer",
        min_years_experience=4.0,
        min_education_rank=2,  # Bachelor's
        min_education_name="Bachelor",
        must_have_skills=["Python", "FastAPI", "Docker"],
        nice_to_have_skills=["Kubernetes", "AWS"],
    )


def test_infer_seniority_level() -> None:
    assert infer_seniority_level("Senior Backend Engineer") == 3
    assert infer_seniority_level("Junior Developer") == 1
    assert infer_seniority_level("Principal Architect") == 4
    assert infer_seniority_level("Software Engineer") == 2


def test_compute_title_similarity() -> None:
    sim = compute_title_similarity(
        "Senior Software Engineer",
        ["Software Engineer", "Lead Developer", "Intern"],
    )
    assert sim >= 0.5
    assert compute_title_similarity("Software Engineer", []) == 0.0


def test_extract_candidate_features_perfect_match() -> None:
    job = create_sample_job_reqs()
    parsed = ResumeParseResult(
        resume_id="cand_001",
        is_resume=True,
        gate_confidence=1.0,
        gate_signals={},
        parse_confidence=0.95,
        page_count=2,
        layout_type="single_column",
        pii=ContactPII(),
        scoring_text="Senior Software Engineer experienced with Python, FastAPI, Docker, and AWS.",
        raw_text="Senior Software Engineer experienced with Python, FastAPI, Docker, and AWS.",
        sections={
            "summary": "Senior Software Engineer with 6 years experience in Python and FastAPI.",
            "skills": "Python, FastAPI, Docker, AWS",
        },
        experiences=[
            WorkExperienceEntry(
                title="Senior Software Engineer",
                company="Tech Corp",
                duration_months=36,
                raw_text="Built FastAPI microservices deployed on Docker.",
            ),
            WorkExperienceEntry(
                title="Software Engineer",
                company="Startup Inc",
                duration_months=36,
                raw_text="Developed Python backend systems.",
            ),
        ],
        educations=[EducationEntry(degree="B.S. Computer Science", ordinal_rank=2)],
        skills=["Python", "FastAPI", "Docker", "AWS"],
    )

    features = extract_candidate_features(
        parsed,
        job,
        dense_similarity_score=0.88,
    )
    assert isinstance(features, CandidateFeatureVector)
    assert features.resume_id == "cand_001"

    # Coverage: covers all 3 must-haves
    assert features.must_have_coverage.value == 1.0
    assert not features.must_have_coverage.is_missing
    assert features.matched_must_count.value == 3.0
    assert "Python" in features.matched_must_skills
    assert "FastAPI" in features.matched_must_skills
    assert "Docker" in features.matched_must_skills

    # Nice-to-haves: AWS matched, Kubernetes missing
    assert features.nice_to_have_coverage.value == 0.5
    assert features.matched_nice_count.value == 1.0

    # Years gap: 72 months = 6.0 years -> gap = 6.0 - 4.0 = 2.0
    assert features.years_gap.value == 2.0
    assert not features.years_gap.is_missing

    # Education match: Bachelor matches required Bachelor
    assert features.education_match.value == 1.0

    # Seniority gap: candidate max Senior (3) - job Senior (3) = 0
    assert features.seniority_gap.value == 0.0

    # Dense similarity
    assert features.dense_similarity.value == 0.88

    # Numpy array generation
    arr = features.to_numpy_array()
    assert arr.shape == (12,)
    assert arr.dtype.name == "float32"


def test_keyword_stuffing_guard() -> None:
    job = create_sample_job_reqs()

    # Candidate repeats "Python" 30 times, but has no FastAPI or Docker
    stuffed_text = "Python " * 30
    parsed = ResumeParseResult(
        resume_id="cand_stuffer",
        is_resume=True,
        gate_confidence=1.0,
        gate_signals={},
        parse_confidence=0.9,
        page_count=1,
        layout_type="single_column",
        pii=ContactPII(),
        scoring_text=stuffed_text,
        raw_text=stuffed_text,
        sections={"skills": stuffed_text},
        experiences=[],
        educations=[],
        skills=["Python"],
    )

    features = extract_candidate_features(parsed, job)

    # Must-have coverage should be 1/3 (33.33%), NOT multiplied or inflated by repetition
    assert abs(features.must_have_coverage.value - (1.0 / 3.0)) < 1e-4
    assert features.matched_must_count.value == 1.0
    assert features.total_raw_skill_mentions >= 10
    assert features.unique_skills_matched == 1


def test_explicit_missing_data_handling() -> None:
    # Empty job without education requirements or must-have skills
    empty_job = JobRequirements(
        job_id="job_minimal",
        title=None,
        min_years_experience=0.0,
        min_education_rank=0,
        must_have_skills=[],
        nice_to_have_skills=[],
    )

    empty_parsed = ResumeParseResult(
        resume_id="cand_empty",
        is_resume=True,
        gate_confidence=0.5,
        gate_signals={},
        parse_confidence=0.3,
        page_count=1,
        layout_type="single_column",
        pii=ContactPII(),
        scoring_text="Minimal candidate text.",
        raw_text="Minimal candidate text.",
        sections={},
        experiences=[],
        educations=[],
        skills=[],
    )

    features = extract_candidate_features(empty_parsed, empty_job)

    # Missing features must be explicitly marked with is_missing=True and missing_reason
    assert features.must_have_coverage.is_missing
    assert features.must_have_coverage.missing_reason is not None

    assert features.years_gap.is_missing
    assert features.years_gap.confidence == 0.0

    assert features.education_match.is_missing
    assert features.education_match.missing_reason is not None

    assert features.title_match.is_missing
    assert features.title_match.missing_reason is not None
