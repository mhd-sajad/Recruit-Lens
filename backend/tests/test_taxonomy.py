import pytest

from app.core.taxonomy import SkillTaxonomy


@pytest.fixture
def taxonomy() -> SkillTaxonomy:
    return SkillTaxonomy.get_instance()


def test_taxonomy_loads_required_minimum_skills(taxonomy: SkillTaxonomy) -> None:
    assert taxonomy.total_skills >= 2000, f"Expected >= 2000 skills, found {taxonomy.total_skills}"


def test_taxonomy_canonicalization(taxonomy: SkillTaxonomy) -> None:
    assert taxonomy.canonicalize("k8s") == "Kubernetes"
    assert taxonomy.canonicalize("py") == "Python"
    assert taxonomy.canonicalize("js") == "JavaScript"
    assert taxonomy.canonicalize("reactjs") == "React"
    assert taxonomy.canonicalize("ml") == "Machine Learning"
    assert taxonomy.canonicalize("postgres") == "PostgreSQL"
    assert taxonomy.canonicalize("unknown_nonexistent_xyz_skill") is None


def test_taxonomy_skill_inference(taxonomy: SkillTaxonomy) -> None:
    inferred_django = taxonomy.get_inferred_skills("Django")
    inferred_names = [s for s, _ in inferred_django]
    assert "Python" in inferred_names

    inferred_k8s = taxonomy.get_inferred_skills("Kubernetes")
    inferred_k8s_names = [s for s, _ in inferred_k8s]
    assert "Docker" in inferred_k8s_names or "Containerization" in inferred_k8s_names


def test_extract_skills_from_text(taxonomy: SkillTaxonomy) -> None:
    sample_text = (
        "Senior Software Engineer experienced with Python, FastAPI, and Docker. "
        "Built microservices deployed on k8s using CI/CD pipelines."
    )
    extracted = taxonomy.extract_skills_from_text(sample_text)
    skills = [e["skill"] for e in extracted]

    assert "Python" in skills
    assert "FastAPI" in skills
    assert "Docker" in skills
    assert "Kubernetes" in skills
    assert "CI/CD" in skills

    # Verify spans and families
    for e in extracted:
        assert len(e["spans"]) >= 1
        assert "family" in e
        start, end = e["spans"][0]
        assert sample_text[start:end].lower() in [
            e["first_matched_text"].lower(),
            "k8s",
            "ci/cd",
            "fastapi",
            "python",
            "docker",
        ]


def test_keyword_boundary_prevents_false_positives(taxonomy: SkillTaxonomy) -> None:
    # 'js' shouldn't match in 'this' or 'jobs', 'py' shouldn't match in 'happy'
    tricky_text = "This happy puppy works in daily jobs with python."
    extracted = taxonomy.extract_skills_from_text(tricky_text)
    skills = [e["skill"] for e in extracted]
    assert "Python" in skills
    assert "JavaScript" not in skills  # should not match 'jobs'
