"""Tests for education and career chronology extractor."""

from app.core.education_extractor import (
    detect_career_gap,
    extract_education_entries,
    extract_highest_education_level,
)


def test_highest_education_level_ranking() -> None:
    """Verify ordinal ranking from PhD to High School."""
    assert extract_highest_education_level("Candidate holds a Ph.D. in Computer Science") == 4
    assert extract_highest_education_level("Completed Doctor of Philosophy in Physics") == 4
    assert extract_highest_education_level("Master of Science in Software Engineering, M.Sc.") == 3
    assert extract_highest_education_level("MBA from Stanford University") == 3
    assert extract_highest_education_level("Bachelor of Technology (B.Tech) in IT") == 2
    assert extract_highest_education_level("B.Sc. in Mathematics, B.A. in Economics") == 2
    assert extract_highest_education_level("Associate Degree in Applied Sciences") == 1
    assert extract_highest_education_level("Graduated from Central High School with GED") == 0
    assert extract_highest_education_level("No education mentioned") == 0


def test_foreign_degree_abbreviations() -> None:
    """Verify non-standard foreign degree abbreviations are recognized."""
    assert extract_highest_education_level("Education: MCA from Anna University") == 3
    assert extract_highest_education_level("Degree: M.Tech in Electrical Engineering") == 3
    assert extract_highest_education_level("Graduated with Dipl.-Ing. from TU Munich") == 3
    assert extract_highest_education_level("Completed BTech in Computer Science") == 2
    assert extract_highest_education_level("Holds MBBS degree") == 2
    assert extract_highest_education_level("Awarded BCA degree") == 2


def test_structured_education_entry_extraction() -> None:
    """Verify structured fields are extracted from education text."""
    edu_text = """
    Master of Science in Artificial Intelligence
    Carnegie Mellon University, Pittsburgh, PA
    Graduated: 2021

    Bachelor of Science in Computer Science
    Rowan University, Glassboro, NJ
    Expected in 2018
    """
    entries = extract_education_entries(edu_text)
    assert len(entries) >= 2
    assert entries[0].ordinal_rank == 3
    assert entries[0].graduation_year == 2021
    assert "Carnegie Mellon" in str(entries[0].institution)

    assert entries[1].ordinal_rank == 2
    assert entries[1].graduation_year == 2018
    assert "Rowan University" in str(entries[1].institution)


def test_career_gap_detection() -> None:
    """Verify detection of significant career gaps."""
    # Employment with a gap between 2016 and 2020 (48 months gap)
    exp_with_gap = """
    Software Engineer, Acme Corp: Jan 2014 to Jun 2016
    Senior Engineer, Beta Inc: Sep 2020 to Present
    """
    gap_months = detect_career_gap(exp_with_gap, threshold_months=6)
    assert gap_months >= 36

    # Continuous employment with minimal gap
    exp_continuous = """
    Junior Developer: Jan 2018 to Dec 2020
    Mid Developer: Feb 2021 to Present
    """
    assert detect_career_gap(exp_continuous, threshold_months=6) == 0
