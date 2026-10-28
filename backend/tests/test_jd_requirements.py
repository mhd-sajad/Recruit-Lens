"""Unit tests for Job Description Requirements Extractor."""

from app.core.jd_requirements import (
    JobRequirements,
    extract_education_requirement,
    extract_job_requirements,
    extract_years_of_experience,
    refine_requirements_with_llm,
    segment_jd_sections,
)


def test_segment_jd_sections() -> None:
    jd = """
    About the Company:
    We are a leading cloud software provider.

    Basic Qualifications:
    - 5+ years of Python backend development.
    - Solid knowledge of PostgreSQL and Docker.

    Preferred Qualifications:
    - Experience with Kubernetes and Terraform is a plus.
    - Familiarity with AWS.
    """
    sections = segment_jd_sections(jd)
    assert "must_have" in sections
    assert "nice_to_have" in sections
    assert "Python" in sections["must_have"]
    assert "Kubernetes" in sections["nice_to_have"]


def test_extract_years_of_experience() -> None:
    min_yrs, max_yrs = extract_years_of_experience("Requires 5+ years of software experience.")
    assert min_yrs == 5.0
    assert max_yrs is None

    min_yrs2, max_yrs2 = extract_years_of_experience("Must have 3 to 5 years of data engineering.")
    assert min_yrs2 == 3.0
    assert max_yrs2 == 5.0

    min_yrs3, _ = extract_years_of_experience("At least 7 years in tech leadership.")
    assert min_yrs3 == 7.0


def test_extract_education_requirement() -> None:
    rank, name = extract_education_requirement("Bachelor's degree in Computer Science required.")
    assert rank == 2
    assert name == "Bachelor"

    rank2, name2 = extract_education_requirement("Master's or Ph.D. preferred.")
    assert rank2 in (3, 4)


def test_extract_job_requirements_end_to_end() -> None:
    jd_text = """
    Senior Python Developer
    Location: Remote

    Requirements:
    - Bachelor's degree in Computer Science or related field.
    - 4+ years of professional software development experience.
    - Strong proficiency in Python and FastAPI.
    - Hands-on experience with Docker.

    Nice to have:
    - Experience with Kubernetes.
    - Familiarity with GraphQL is a plus.
    """
    reqs = extract_job_requirements(jd_text, job_id="job_001", title="Senior Python Developer")

    assert isinstance(reqs, JobRequirements)
    assert reqs.job_id == "job_001"
    assert reqs.min_years_experience == 4.0
    assert reqs.min_education_rank == 2
    assert reqs.min_education_name == "Bachelor"

    # Skills check
    assert "Python" in reqs.must_have_skills
    assert "FastAPI" in reqs.must_have_skills
    assert "Docker" in reqs.must_have_skills

    assert "Kubernetes" in reqs.nice_to_have_skills
    assert "GraphQL" in reqs.nice_to_have_skills

    # Hook check
    refined = refine_requirements_with_llm(reqs)
    assert refined.job_id == reqs.job_id
