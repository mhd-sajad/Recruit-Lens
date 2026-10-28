"""Unit tests for What-If Simulator."""

from app.core.jd_requirements import JobRequirements
from app.core.models import ContactPII, EducationEntry, ResumeParseResult, WorkExperienceEntry
from app.core.simulator import WhatIfSimulationResult, simulate_candidate_adjustments


def create_sample_candidate() -> ResumeParseResult:
    return ResumeParseResult(
        resume_id="cand_sim_01",
        is_resume=True,
        gate_confidence=1.0,
        gate_signals={},
        parse_confidence=0.95,
        page_count=2,
        layout_type="single_column",
        pii=ContactPII(name="Test Developer"),
        scoring_text="Software Developer with experience in Python and MySQL.",
        raw_text="Software Developer with experience in Python and MySQL.",
        sections={
            "summary": "Software Developer with 2 years experience in Python and MySQL.",
            "skills": "Python, MySQL",
        },
        experiences=[
            WorkExperienceEntry(
                title="Junior Developer",
                company="Startup Inc",
                duration_months=24,
                raw_text="Built Python backend scripts.",
            )
        ],
        educations=[EducationEntry(degree="B.S. Computer Science", ordinal_rank=2)],
        skills=["Python", "MySQL"],
    )


def test_what_if_simulator_skill_addition() -> None:
    candidate = create_sample_candidate()
    job = JobRequirements(
        title="Senior Software Engineer",
        min_years_experience=4.0,
        must_have_skills=["Python", "Docker", "FastAPI"],
        nice_to_have_skills=["Kubernetes"],
    )

    # Base candidate only has Python -> missing Docker and FastAPI
    # Simulate adding Docker and FastAPI
    sim_res = simulate_candidate_adjustments(
        candidate,
        job,
        added_skills=["Docker", "FastAPI"],
        added_years=2.5,
    )

    assert isinstance(sim_res, WhatIfSimulationResult)
    assert sim_res.is_estimate
    assert "Hypothetical" in sim_res.disclaimer
    # Score must increase after adding required skills and experience
    assert sim_res.simulated_score > sim_res.base_score
    assert sim_res.score_delta > 0.05
    assert "Docker" in sim_res.newly_covered_must_skills
    assert "FastAPI" in sim_res.newly_covered_must_skills
