"""Tests for experience, seniority, and work history extractor."""

from app.core.experience_extractor import (
    extract_seniority_level,
    extract_structured_experiences,
    extract_years_of_experience,
)


def test_extract_explicit_years() -> None:
    """Verify extraction of explicitly stated years of experience."""
    assert extract_years_of_experience("5+ years of experience in Python") == 5.0
    assert (
        extract_years_of_experience("Over 8 years experience building distributed systems") == 8.0
    )
    assert extract_years_of_experience("Has 3-5 years in full-stack web development") == 5.0
    # Guard against age or college false positives
    assert extract_years_of_experience("Candidate is 24 years old with 4 years college") is None


def test_summed_years_from_date_intervals() -> None:
    """Verify calculation of experience when explicit 'X years' is missing."""
    text_with_dates = """
    Software Engineer, Google: 2018 to 2021
    Senior Software Engineer, Meta: 2021 to 2024
    """
    years = extract_years_of_experience(text_with_dates)
    assert years is not None
    assert years >= 6.0


def test_seniority_level_extraction() -> None:
    """Verify seniority keyword matching and ordinal ranking (0-4)."""
    assert extract_seniority_level("Staff Software Engineer") == 3
    assert extract_seniority_level("Lead Data Scientist") == 3
    assert extract_seniority_level("Principal Systems Architect") == 4
    assert extract_seniority_level("Senior Frontend Developer") == 2
    assert extract_seniority_level("Mid-Level Backend Engineer") == 1
    assert extract_seniority_level("Junior Developer") == 0
    assert extract_seniority_level("Software Engineering Intern") == 0

    # Fallback to years of experience when no keyword in title
    assert extract_seniority_level("Programmer", years=10.0) == 3
    assert extract_seniority_level("Developer", years=6.0) == 2
    assert extract_seniority_level("Developer", years=1.0) == 0


def test_extract_structured_experiences() -> None:
    """Verify decomposition into structured job entries."""
    exp_text = """
    Senior Python Developer , 01/2020 to Present
    Stripe Inc. – San Francisco, CA
    • Architected high-throughput payment processing APIs handling 50k RPS.
    • Mentored junior engineers and led code review standards.

    Software Engineer , 06/2016 to 12/2019
    Lyft – Seattle, WA
    • Implemented dispatch matching algorithms reducing passenger wait time by 12%.
    • Authored unit and integration test suites in Pytest.
    """
    entries = extract_structured_experiences(exp_text)
    assert len(entries) >= 2

    e1 = entries[0]
    assert e1.title is not None
    assert "Developer" in e1.title
    assert "Stripe" in str(e1.company)
    assert e1.is_current is True
    assert len(e1.bullets) >= 2

    e2 = entries[1]
    assert e2.title is not None
    assert "Software Engineer" in e2.title
    assert "Lyft" in str(e2.company)
    assert e2.is_current is False
    assert len(e2.bullets) >= 2
