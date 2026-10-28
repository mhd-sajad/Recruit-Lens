"""
compile_taxonomy.py

Processes O*NET Technology Skills into a compact, production-ready taxonomy JSON
packaged within backend/app/data/skills_taxonomy.json.
Enriches with curated aliases, skill families, and inference relations.
"""

import csv
import json
import re
from pathlib import Path
from typing import Any

# Standard curated aliases for fast lookup
CURATED_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "k8s": "Kubernetes",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "nlp": "Natural Language Processing",
    "cv": "Computer Vision",
    "aws": "Amazon Web Services",
    "gcp": "Google Cloud Platform",
    "azure": "Microsoft Azure",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "angularjs": "Angular",
    "node": "Node.js",
    "nodejs": "Node.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "tf": "TensorFlow",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "sklearn": "Scikit-learn",
    "scikit-learn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "rest": "RESTful APIs",
    "rest api": "RESTful APIs",
    "restful api": "RESTful APIs",
    "rest apis": "RESTful APIs",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "jenkins": "Jenkins",
    "docker": "Docker",
    "containers": "Containerization",
    "containerization": "Containerization",
    "etl": "ETL",
    "bi": "Business Intelligence",
    "pbi": "Power BI",
    "powerbi": "Power BI",
    "power bi": "Power BI",
    "tableau": "Tableau",
    "db": "Databases",
    "sql": "SQL",
    "nosql": "NoSQL",
    "scrum": "Agile Scrum",
    "agile": "Agile Methodologies",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "graphql": "GraphQL",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "golang": "Go",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    ".net": ".NET",
    "dotnet": ".NET",
    "spark": "Apache Spark",
    "hadoop": "Apache Hadoop",
    "kafka": "Apache Kafka",
    "redis": "Redis",
    "linux": "Linux",
    "bash": "Bash",
    "shell": "Shell Scripting",
}

# Skill inference relationships: Key skill implies target skills with confidence (0.0 to 1.0)
INFERENCE_RELATIONS: dict[str, list[dict[str, Any]]] = {
    "django": [{"skill": "Python", "confidence": 0.95}],
    "flask": [{"skill": "Python", "confidence": 0.95}],
    "fastapi": [{"skill": "Python", "confidence": 0.95}],
    "pandas": [
        {"skill": "Python", "confidence": 0.95},
        {"skill": "Data Analysis", "confidence": 0.85},
    ],
    "numpy": [{"skill": "Python", "confidence": 0.95}],
    "scikit-learn": [
        {"skill": "Python", "confidence": 0.95},
        {"skill": "Machine Learning", "confidence": 0.90},
    ],
    "pytorch": [
        {"skill": "Python", "confidence": 0.95},
        {"skill": "Deep Learning", "confidence": 0.90},
    ],
    "tensorflow": [
        {"skill": "Python", "confidence": 0.90},
        {"skill": "Deep Learning", "confidence": 0.90},
    ],
    "keras": [
        {"skill": "Python", "confidence": 0.90},
        {"skill": "Deep Learning", "confidence": 0.90},
    ],
    "react": [{"skill": "JavaScript", "confidence": 0.95}],
    "vue.js": [{"skill": "JavaScript", "confidence": 0.95}],
    "angular": [
        {"skill": "TypeScript", "confidence": 0.90},
        {"skill": "JavaScript", "confidence": 0.90},
    ],
    "next.js": [
        {"skill": "React", "confidence": 0.95},
        {"skill": "JavaScript", "confidence": 0.95},
    ],
    "express": [
        {"skill": "Node.js", "confidence": 0.95},
        {"skill": "JavaScript", "confidence": 0.95},
    ],
    "node.js": [{"skill": "JavaScript", "confidence": 0.95}],
    "spring boot": [{"skill": "Java", "confidence": 0.95}],
    "asp.net": [
        {"skill": "C#", "confidence": 0.95},
        {"skill": ".NET", "confidence": 0.95},
    ],
    "kubernetes": [
        {"skill": "Docker", "confidence": 0.85},
        {"skill": "Containerization", "confidence": 0.90},
    ],
    "helm": [{"skill": "Kubernetes", "confidence": 0.95}],
    "terraform": [{"skill": "Infrastructure as Code", "confidence": 0.95}],
    "ansible": [{"skill": "Configuration Management", "confidence": 0.90}],
    "tableau": [{"skill": "Data Visualization", "confidence": 0.95}],
    "power bi": [
        {"skill": "Data Visualization", "confidence": 0.95},
        {"skill": "Business Intelligence", "confidence": 0.90},
    ],
    "apache spark": [{"skill": "Big Data", "confidence": 0.90}],
    "apache kafka": [
        {"skill": "Distributed Systems", "confidence": 0.85},
        {"skill": "Data Streaming", "confidence": 0.85},
    ],
}


def clean_skill_name(name: str) -> str:
    """Clean skill title, stripping version numbers or bracket notes."""
    name = re.sub(r"\s*\(.*?\)", "", name)
    name = re.sub(r"\s+software$", "", name, flags=re.IGNORECASE)
    return name.strip()


def compile_taxonomy() -> dict[str, Any]:
    raw_path = (
        Path(__file__).resolve().parent.parent / "data" / "onet_technology_skills.txt"
    )
    out_dir = Path(__file__).resolve().parent.parent / "backend" / "app" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "skills_taxonomy.json"

    skills_by_canonical: dict[str, dict[str, Any]] = {}
    family_counts: dict[str, int] = {}

    if raw_path.exists():
        with open(raw_path, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                raw_skill = row.get("Example", "").strip()
                fam = row.get("Commodity Title", "General Technology").strip()
                hot = row.get("Hot Technology", "N") == "Y"
                in_demand = row.get("In Demand", "N") == "Y"

                if not raw_skill or len(raw_skill) < 2:
                    continue

                cleaned = clean_skill_name(raw_skill)
                if not cleaned:
                    continue

                norm_key = cleaned.lower()
                if norm_key not in skills_by_canonical:
                    skills_by_canonical[norm_key] = {
                        "canonical_name": cleaned,
                        "family": fam,
                        "aliases": [cleaned.lower()],
                        "hot_technology": hot,
                        "in_demand": in_demand,
                    }
                    family_counts[fam] = family_counts.get(fam, 0) + 1
                else:
                    if hot:
                        skills_by_canonical[norm_key]["hot_technology"] = True
                    if in_demand:
                        skills_by_canonical[norm_key]["in_demand"] = True

    # Integrate curated aliases
    for alias, canonical in CURATED_ALIASES.items():
        norm_canonical = canonical.lower()
        if norm_canonical not in skills_by_canonical:
            skills_by_canonical[norm_canonical] = {
                "canonical_name": canonical,
                "family": "Software Engineering & Data",
                "aliases": [norm_canonical],
                "hot_technology": True,
                "in_demand": True,
            }
        if alias.lower() not in skills_by_canonical[norm_canonical]["aliases"]:
            skills_by_canonical[norm_canonical]["aliases"].append(alias.lower())

    # Select top 2,500 skills prioritizing curated aliases, hot technologies, and in-demand skills
    def priority_score(item: dict[str, Any]) -> int:
        canon_lower = item["canonical_name"].lower()
        score = 0
        if canon_lower in CURATED_ALIASES or any(
            canon_lower == c.lower() for c in CURATED_ALIASES.values()
        ):
            score += 100
        if item.get("hot_technology"):
            score += 20
        if item.get("in_demand"):
            score += 20
        if len(item["canonical_name"]) <= 30:
            score += 5
        return score

    sorted_skills = sorted(
        skills_by_canonical.values(), key=priority_score, reverse=True
    )
    selected_skills = sorted_skills[:2500]

    # Build reverse alias lookup map
    alias_to_canonical: dict[str, str] = {}
    for item in selected_skills:
        canon = item["canonical_name"]
        alias_to_canonical[canon.lower()] = canon
        for a in item.get("aliases", []):
            alias_to_canonical[a.lower()] = canon
    for alias, canonical in CURATED_ALIASES.items():
        alias_to_canonical[alias.lower()] = canonical

    # Build taxonomy payload
    taxonomy_payload = {
        "metadata": {
            "source": "O*NET 29.0 Technology Skills & Curated Tech Taxonomy",
            "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
            "total_canonical_skills": len(selected_skills),
            "total_aliases": len(alias_to_canonical),
            "total_families": len(family_counts),
        },
        "skills": selected_skills,
        "alias_to_canonical": alias_to_canonical,
        "inference_relations": INFERENCE_RELATIONS,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(taxonomy_payload, f, separators=(",", ":"))

    print(f"Taxonomy compiled to {out_path}:")
    print(f"  Canonical Skills: {len(selected_skills)}")
    print(f"  Total Alias Mappings: {len(alias_to_canonical)}")
    print(f"  Skill Families: {len(family_counts)}")

    return taxonomy_payload


if __name__ == "__main__":
    compile_taxonomy()
