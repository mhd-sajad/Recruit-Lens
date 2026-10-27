"""Tests for resume and JD chunking modules."""

from app.core.jd_chunker import chunk_jd_text
from app.core.models import ContactPII, ResumeParseResult
from app.core.resume_chunker import chunk_resume, word_sliding_window


def test_word_sliding_window() -> None:
    """Verify sliding window with overlap produces expected boundaries."""
    text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"
    windows = word_sliding_window(text, chunk_size=5, overlap=2)
    assert len(windows) == 3
    assert windows[0] == "word1 word2 word3 word4 word5"
    assert windows[1] == "word4 word5 word6 word7 word8"
    assert windows[2] == "word7 word8 word9 word10"


def test_chunk_jd_text() -> None:
    """Verify JD chunker handles short and long JDs."""
    short_jd = "Senior Python Developer required with experience in FastAPI and PostgreSQL."
    short_chunks = chunk_jd_text(short_jd, "jd_101", chunk_size=50)
    assert len(short_chunks) == 1
    assert short_chunks[0].chunk_id == "jd_101_001"
    assert short_chunks[0].jd_id == "jd_101"

    long_jd = " ".join(f"skill_{i}" for i in range(250))
    long_chunks = chunk_jd_text(long_jd, "jd_202", chunk_size=100, overlap=20)
    assert len(long_chunks) >= 3
    for c in long_chunks:
        assert c.jd_id == "jd_202"
        assert c.chunk_id.startswith("jd_202_")


def test_chunk_resume_section_provenance() -> None:
    """Verify parsed resume sections map into distinct chunks with correct tags."""
    parsed = ResumeParseResult(
        resume_id="cand_test_01",
        is_resume=True,
        gate_confidence=0.95,
        gate_signals={"has_experience": True},
        parse_confidence=0.9,
        page_count=1,
        layout_type="single_column",
        pii=ContactPII(name="Test Candidate", email="test@example.com"),
        scoring_text="Scoring text summary",
        raw_text="Raw text summary",
        sections={
            "summary": "Experienced software architect with 10 years in cloud computing.",
            "skills": "Python, Docker, Kubernetes, AWS, PostgreSQL, Redis",
            "education": "BS in Computer Science from MIT, 2015",
            "experience": "Lead Architect at Acme Cloud: Built distributed streaming platform.",
            "projects": "Open source maintainer for distributed task queue.",
        },
        experiences=[],
        educations=[],
        skills=["Python", "Docker", "Kubernetes"],
    )

    chunks = chunk_resume(parsed)
    assert len(chunks) == 5

    sections = [c.section for c in chunks]
    assert "summary" in sections
    assert "skills" in sections
    assert "education" in sections
    assert "experience" in sections
    assert "projects" in sections

    for c in chunks:
        assert c.resume_id == "cand_test_01"
        assert c.chunk_id.startswith("cand_test_01_")
        assert c.metadata["word_count"] > 0
