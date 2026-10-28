"""Tests for PDF parser layout handling, resume gate heuristics, and PII isolation."""

from pathlib import Path

import pytest

from app.core.pdf_parser import (
    calculate_parse_confidence,
    evaluate_resume_gate,
    extract_and_isolate_pii,
    parse_resume_pdf,
    segment_sections,
)


def test_resume_gate_positive_signals() -> None:
    """Verify resume gate detects authentic resume text."""
    sample_resume = """
    John Doe
    john.doe@example.com | (555) 123-4567 | San Francisco, CA

    PROFESSIONAL SUMMARY
    Senior Software Engineer with 7+ years of experience building distributed backend systems.

    EXPERIENCE
    Senior Backend Engineer - Uber (2020 - Present)
    • Architected microservices in Python and Go.
    Software Engineer - Twitter (2017 - 2020)
    • Built data pipelines in Apache Kafka and Spark.

    EDUCATION
    Bachelor of Science in Computer Science, UC Berkeley, 2017

    SKILLS
    Python, FastAPI, Docker, Kubernetes, AWS, SQL
    """
    is_resume, conf, signals = evaluate_resume_gate(sample_resume, page_count=2)
    assert is_resume is True
    assert conf >= 0.8
    assert signals["experience_section"] is True
    assert signals["education_section"] is True
    assert signals["skills_section"] is True


def test_resume_gate_rejects_invoices_and_papers() -> None:
    """Verify resume gate rejects commercial invoices and academic papers."""
    invoice_text = """
    TAX INVOICE #INV-99812
    Bill To: Global Logistics Inc.
    Total Amount Due: $15,400.00
    Payment Terms: Net 30 Days
    Itemized Services: Consulting 100 hrs @ $150/hr
    Subtotal: $15,000
    Tax: $400
    Please remit payment to account #123456789.
    """
    is_res, conf, signals = evaluate_resume_gate(invoice_text, page_count=1)
    assert is_res is False
    assert conf <= 0.3

    paper_text = """
    IEEE Transactions on Pattern Analysis and Machine Intelligence
    Abstract: We present an asymptotic convergence analysis for non-convex optimization.
    Proceedings of the 2024 International Conference on Computer Vision.
    References:
    1. Goodfellow et al.
    2. He et al.
    """
    is_res_paper, _, _ = evaluate_resume_gate(paper_text, page_count=10)
    assert is_res_paper is False


def test_pii_isolation_and_sanitization() -> None:
    """Verify PII extraction creates a clean ContactPII object and sanitizes scoring text."""
    raw_text = """
    Jane Smith
    jane.smith@corporation.org
    (415) 555-2671
    https://linkedin.com/in/janesmith

    PROFESSIONAL EXPERIENCE
    Senior Lead Designer at Acme Inc. from 2019 to Present.
    Worked with Jane Smith to lead branding.
    """
    pii, scoring_text = extract_and_isolate_pii(raw_text)

    assert pii.name == "Jane Smith"
    assert pii.email == "jane.smith@corporation.org"
    assert pii.phone == "(415) 555-2671"
    assert len(pii.links) >= 1

    # Verify scoring text is redacted for blind review
    assert "jane.smith@corporation.org" not in scoring_text
    assert "[CANDIDATE_EMAIL]" in scoring_text
    assert "(415) 555-2671" not in scoring_text
    assert "[CANDIDATE_PHONE]" in scoring_text


def test_calculate_parse_confidence() -> None:
    """Verify calculation of parse fidelity score."""
    normal_text = "Standard resume text content with healthy character count. " * 30
    conf_good = calculate_parse_confidence(normal_text, page_count=1, is_resume=True)
    assert conf_good >= 0.8

    # Low character count per page
    conf_low_chars = calculate_parse_confidence("Too short", page_count=2, is_resume=True)
    assert conf_low_chars < 0.6

    # Non-resume penalty
    conf_non_resume = calculate_parse_confidence(normal_text, page_count=1, is_resume=False)
    assert conf_non_resume <= 0.3


def test_segment_sections() -> None:
    """Verify section segmentation correctly splits content into canonical dictionary."""
    text = """
    SUMMARY
    Experienced financial accountant with expertise in GAAP auditing.

    WORK EXPERIENCE
    Senior Accountant at Deloitte from 2018 to 2023.

    EDUCATION
    Master of Accounting, Ohio State University, 2017.

    SKILLS
    QuickBooks, SAP, GAAP, Financial Modeling, Excel
    """
    sections = segment_sections(text)
    assert "summary" in sections
    assert "experience" in sections
    assert "education" in sections
    assert "skills" in sections
    assert "Deloitte" in sections["experience"]
    assert "Ohio State" in sections["education"]


def test_parse_resume_pdf_real_file() -> None:
    """Verify parse_resume_pdf executes end-to-end on real sampled resume."""
    data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "resumes_sample_300"
    pdfs = list(data_dir.rglob("*.pdf"))
    if not pdfs:
        pytest.skip("Sampled resumes not present in data/resumes_sample_300")

    result = parse_resume_pdf(pdfs[0])
    assert result.is_resume is True
    assert result.page_count >= 1
    assert result.parse_confidence > 0.5
    assert len(result.scoring_text) > 100
    assert result.layout_type in ["single_column", "multi_column"]
