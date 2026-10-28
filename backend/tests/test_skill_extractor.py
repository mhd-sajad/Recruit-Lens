"""Unit tests for Resume Skill Extractor with Citation Evidence and Inference."""

from app.core.models import ContactPII, ResumeChunk, ResumeParseResult
from app.core.skill_extractor import (
    CandidateSkillsResult,
    extract_skills_from_chunks,
    extract_skills_from_parsed_resume,
)


def test_extract_explicit_skills_with_evidence() -> None:
    chunks = [
        ResumeChunk(
            chunk_id="res_01_001",
            resume_id="res_01",
            section="experience",
            text="Developed high-throughput backend services using FastAPI and PostgreSQL on AWS.",
        ),
        ResumeChunk(
            chunk_id="res_01_002",
            resume_id="res_01",
            section="skills",
            text="Skills: Docker, Kubernetes, CI/CD, Git.",
        ),
    ]

    result = extract_skills_from_chunks("res_01", chunks)
    assert isinstance(result, CandidateSkillsResult)
    assert result.resume_id == "res_01"

    # Explicit skills verification
    assert "fastapi" in result.explicit_skills
    assert "postgresql" in result.explicit_skills
    assert "amazon web services" in result.explicit_skills or "aws" in result.explicit_skills
    assert "docker" in result.explicit_skills
    assert "kubernetes" in result.explicit_skills

    fastapi_skill = result.explicit_skills["fastapi"]
    assert not fastapi_skill.is_inferred
    assert fastapi_skill.confidence == 1.0
    assert len(fastapi_skill.evidence) >= 1

    ev = fastapi_skill.evidence[0]
    assert ev.chunk_id == "res_01_001"
    assert ev.section == "experience"
    assert "FastAPI" in ev.snippet
    assert ev.char_start < ev.char_end


def test_inferred_skills_from_relations() -> None:
    # Candidate mentions Django, but does NOT explicitly write "Python"
    chunks = [
        ResumeChunk(
            chunk_id="res_02_001",
            resume_id="res_02",
            section="experience",
            text="Architected enterprise portal using Django and Celery.",
        )
    ]

    result = extract_skills_from_chunks("res_02", chunks)

    # Django is explicit
    assert "django" in result.explicit_skills
    assert not result.explicit_skills["django"].is_inferred

    # Python must be inferred
    assert "python" in result.inferred_skills
    inferred_py = result.inferred_skills["python"]
    assert inferred_py.is_inferred
    assert inferred_py.inferred_from == "Django"
    assert inferred_py.confidence >= 0.90
    assert len(inferred_py.evidence) >= 1
    assert inferred_py.evidence[0].chunk_id == "res_02_001"


def test_explicit_match_takes_precedence_over_inference() -> None:
    # Candidate mentions both Django and Python explicitly
    chunks = [
        ResumeChunk(
            chunk_id="res_03_001",
            resume_id="res_03",
            section="experience",
            text="Developed applications using Django and Python.",
        )
    ]

    result = extract_skills_from_chunks("res_03", chunks)

    assert "python" in result.explicit_skills
    assert result.explicit_skills["python"].confidence == 1.0
    assert not result.explicit_skills["python"].is_inferred
    assert "python" not in result.inferred_skills


def test_keyword_stuffing_deduplication() -> None:
    # Repeating Python 10 times in multiple chunks
    chunks = [
        ResumeChunk(
            chunk_id="res_04_001",
            resume_id="res_04",
            section="experience",
            text="Python Python Python Python developer.",
        ),
        ResumeChunk(
            chunk_id="res_04_002",
            resume_id="res_04",
            section="skills",
            text="Python, Python programming, Python scripts.",
        ),
    ]

    result = extract_skills_from_chunks("res_04", chunks)
    assert "python" in result.explicit_skills
    py_skill = result.explicit_skills["python"]

    # Multiple occurrences are noted for audit, but it counts as exactly 1 distinct skill entry
    assert py_skill.occurrences >= 2
    assert len(py_skill.evidence) >= 2
    assert len(result.all_canonical_skills) >= 1


def test_extract_skills_from_parsed_resume_end_to_end() -> None:
    parsed = ResumeParseResult(
        resume_id="parsed_01",
        is_resume=True,
        gate_confidence=0.95,
        gate_signals={"has_experience": True},
        parse_confidence=0.90,
        page_count=1,
        layout_type="single_column",
        pii=ContactPII(),
        scoring_text="Software Engineer with Python, React, and Docker experience.",
        raw_text="Software Engineer with Python, React, and Docker experience.",
        sections={
            "summary": "Full stack engineer specializing in Python and React.",
            "skills": "Python, React, Docker, Linux",
        },
        experiences=[],
        educations=[],
        skills=["Python", "React", "Docker", "Linux"],
    )

    result = extract_skills_from_parsed_resume(parsed)
    assert result.resume_id == "parsed_01"
    assert "python" in result.explicit_skills
    assert "react" in result.explicit_skills
    assert "docker" in result.explicit_skills
