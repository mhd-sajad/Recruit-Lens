"""
compile_taxonomy.py

Processes O*NET Technology Skills and domain-specific non-tech skills (Education, Healthcare,
Sales, HR, Operations, Legal) into an expanded, production-ready taxonomy JSON packaged within
backend/app/data/skills_taxonomy.json.
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
    "react": [
        {"skill": "JavaScript", "confidence": 0.95},
        {"skill": "Frontend Development", "confidence": 0.90},
    ],
    "angular": [
        {"skill": "TypeScript", "confidence": 0.95},
        {"skill": "Frontend Development", "confidence": 0.90},
    ],
    "vue.js": [
        {"skill": "JavaScript", "confidence": 0.95},
        {"skill": "Frontend Development", "confidence": 0.90},
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

# Comprehensive non-tech domain skills covering Education, Healthcare, Sales, HR, Legal, and Operations
DOMAIN_NON_TECH_SKILLS: list[dict[str, Any]] = [
    # Education & Teaching
    {
        "name": "Curriculum Development",
        "family": "Education & Teaching",
        "aliases": ["curriculum design", "curriculum planning"],
    },
    {"name": "Lesson Planning", "family": "Education & Teaching", "aliases": ["lesson design"]},
    {
        "name": "Classroom Management",
        "family": "Education & Teaching",
        "aliases": ["classroom discipline", "student behavior management"],
    },
    {
        "name": "Student Assessment",
        "family": "Education & Teaching",
        "aliases": ["formative assessment", "summative assessment", "grading"],
    },
    {
        "name": "Special Education",
        "family": "Education & Teaching",
        "aliases": ["sped", "special needs education", "iep development"],
    },
    {
        "name": "Differentiated Instruction",
        "family": "Education & Teaching",
        "aliases": ["differentiated learning"],
    },
    {
        "name": "Pedagogy",
        "family": "Education & Teaching",
        "aliases": ["pedagogical methods", "teaching methodology"],
    },
    {"name": "STEM Education", "family": "Education & Teaching", "aliases": ["stem teaching"]},
    {
        "name": "Literacy Instruction",
        "family": "Education & Teaching",
        "aliases": ["reading instruction", "phonics", "guided reading"],
    },
    {
        "name": "Educational Technology",
        "family": "Education & Teaching",
        "aliases": ["edtech", "instructional technology"],
    },
    {
        "name": "Classroom Instruction",
        "family": "Education & Teaching",
        "aliases": ["direct instruction", "student instruction"],
    },
    {
        "name": "Individualized Education Program",
        "family": "Education & Teaching",
        "aliases": ["iep", "ieps"],
    },
    {
        "name": "Instructional Design",
        "family": "Education & Teaching",
        "aliases": ["e-learning development", "course design"],
    },
    {"name": "Canvas LMS", "family": "Education & Teaching", "aliases": ["canvas"]},
    {"name": "Blackboard", "family": "Education & Teaching", "aliases": ["blackboard learn"]},
    {"name": "Moodle", "family": "Education & Teaching", "aliases": []},
    {"name": "Google Classroom", "family": "Education & Teaching", "aliases": []},
    {
        "name": "Early Childhood Education",
        "family": "Education & Teaching",
        "aliases": ["ece", "preschool teaching"],
    },
    {"name": "Adult Education", "family": "Education & Teaching", "aliases": ["andragogy"]},
    # Healthcare & Medical
    {
        "name": "Patient Care",
        "family": "Healthcare & Medical",
        "aliases": ["direct patient care", "patient support"],
    },
    {
        "name": "Clinical Assessment",
        "family": "Healthcare & Medical",
        "aliases": ["nursing assessment", "patient evaluation"],
    },
    {"name": "Triage", "family": "Healthcare & Medical", "aliases": ["emergency triage"]},
    {
        "name": "Vital Signs",
        "family": "Healthcare & Medical",
        "aliases": ["vitals monitoring", "blood pressure monitoring"],
    },
    {
        "name": "Phlebotomy",
        "family": "Healthcare & Medical",
        "aliases": ["blood draw", "venipuncture"],
    },
    {"name": "CPR", "family": "Healthcare & Medical", "aliases": ["cardiopulmonary resuscitation"]},
    {"name": "Basic Life Support", "family": "Healthcare & Medical", "aliases": ["bls"]},
    {
        "name": "Advanced Cardiovascular Life Support",
        "family": "Healthcare & Medical",
        "aliases": ["acls"],
    },
    {
        "name": "Electronic Health Records",
        "family": "Healthcare & Medical",
        "aliases": ["ehr", "emr", "electronic medical records"],
    },
    {
        "name": "Medication Administration",
        "family": "Healthcare & Medical",
        "aliases": ["administering medications", "pharmacotherapy"],
    },
    {
        "name": "Infection Control",
        "family": "Healthcare & Medical",
        "aliases": ["aseptic technique", "sanitation protocols"],
    },
    {
        "name": "HIPAA Compliance",
        "family": "Healthcare & Medical",
        "aliases": ["hipaa", "patient privacy"],
    },
    {
        "name": "Patient Advocacy",
        "family": "Healthcare & Medical",
        "aliases": ["patient counseling"],
    },
    {"name": "Wound Care", "family": "Healthcare & Medical", "aliases": ["dressing changes"]},
    {
        "name": "Diagnostic Testing",
        "family": "Healthcare & Medical",
        "aliases": ["clinical diagnostics"],
    },
    {
        "name": "Clinical Documentation",
        "family": "Healthcare & Medical",
        "aliases": ["charting", "medical charting"],
    },
    {"name": "Medical Terminology", "family": "Healthcare & Medical", "aliases": []},
    {"name": "Epic Systems", "family": "Healthcare & Medical", "aliases": ["epic ehr"]},
    {"name": "Cerner", "family": "Healthcare & Medical", "aliases": []},
    {"name": "Meditech", "family": "Healthcare & Medical", "aliases": []},
    # Sales & Marketing
    {
        "name": "Business Development",
        "family": "Sales & Marketing",
        "aliases": ["biz dev", "b2b development"],
    },
    {
        "name": "Lead Generation",
        "family": "Sales & Marketing",
        "aliases": ["lead prospecting", "prospecting"],
    },
    {
        "name": "Cold Calling",
        "family": "Sales & Marketing",
        "aliases": ["outbound calling", "telesales"],
    },
    {
        "name": "Account Management",
        "family": "Sales & Marketing",
        "aliases": ["client management", "key account management"],
    },
    {"name": "CRM", "family": "Sales & Marketing", "aliases": ["customer relationship management"]},
    {
        "name": "B2B Sales",
        "family": "Sales & Marketing",
        "aliases": ["business to business sales", "enterprise sales"],
    },
    {
        "name": "Market Research",
        "family": "Sales & Marketing",
        "aliases": ["competitive analysis", "industry research"],
    },
    {"name": "Digital Marketing", "family": "Sales & Marketing", "aliases": ["online marketing"]},
    {"name": "Search Engine Optimization", "family": "Sales & Marketing", "aliases": ["seo"]},
    {
        "name": "Content Marketing",
        "family": "Sales & Marketing",
        "aliases": ["content creation", "copywriting"],
    },
    {
        "name": "Sales Forecasting",
        "family": "Sales & Marketing",
        "aliases": ["revenue forecasting", "sales projections"],
    },
    {"name": "Pipeline Management", "family": "Sales & Marketing", "aliases": ["sales pipeline"]},
    {
        "name": "Client Relations",
        "family": "Sales & Marketing",
        "aliases": ["customer retention", "client communication"],
    },
    # HR & Talent Management
    {
        "name": "Talent Acquisition",
        "family": "Human Resources",
        "aliases": ["recruiting", "recruitment", "headhunting"],
    },
    {
        "name": "Employee Relations",
        "family": "Human Resources",
        "aliases": ["workplace relations", "conflict resolution"],
    },
    {
        "name": "Onboarding",
        "family": "Human Resources",
        "aliases": ["new hire onboarding", "employee induction"],
    },
    {
        "name": "Performance Management",
        "family": "Human Resources",
        "aliases": ["performance reviews", "kpi evaluation"],
    },
    {
        "name": "Payroll Administration",
        "family": "Human Resources",
        "aliases": ["payroll processing", "payroll"],
    },
    {
        "name": "Benefits Administration",
        "family": "Human Resources",
        "aliases": ["compensation & benefits", "employee benefits"],
    },
    {"name": "Workforce Planning", "family": "Human Resources", "aliases": ["staffing planning"]},
    {"name": "Applicant Tracking Systems", "family": "Human Resources", "aliases": ["ats"]},
    {
        "name": "Human Resources Information System",
        "family": "Human Resources",
        "aliases": ["hris"],
    },
    # Operations & Supply Chain
    {
        "name": "Supply Chain Management",
        "family": "Operations & Supply Chain",
        "aliases": ["supply chain", "scm"],
    },
    {
        "name": "Inventory Control",
        "family": "Operations & Supply Chain",
        "aliases": ["inventory management", "stock management"],
    },
    {
        "name": "Vendor Management",
        "family": "Operations & Supply Chain",
        "aliases": ["vendor relations", "supplier management"],
    },
    {
        "name": "Process Optimization",
        "family": "Operations & Supply Chain",
        "aliases": ["process improvement", "operational efficiency"],
    },
    {
        "name": "Logistics Management",
        "family": "Operations & Supply Chain",
        "aliases": ["logistics", "freight forwarding"],
    },
    {
        "name": "Quality Assurance",
        "family": "Operations & Supply Chain",
        "aliases": ["qa", "quality control", "qc"],
    },
    {
        "name": "Six Sigma",
        "family": "Operations & Supply Chain",
        "aliases": ["lean six sigma", "green belt", "black belt"],
    },
    {
        "name": "Lean Manufacturing",
        "family": "Operations & Supply Chain",
        "aliases": ["lean operations", "5s"],
    },
    {
        "name": "Warehouse Operations",
        "family": "Operations & Supply Chain",
        "aliases": ["warehouse management"],
    },
    # Legal & Compliance
    {
        "name": "Contract Negotiation",
        "family": "Legal & Compliance",
        "aliases": ["contract drafting", "contract review"],
    },
    {"name": "Due Diligence", "family": "Legal & Compliance", "aliases": ["legal due diligence"]},
    {
        "name": "Compliance Management",
        "family": "Legal & Compliance",
        "aliases": ["regulatory compliance", "corporate compliance"],
    },
    {
        "name": "Legal Research",
        "family": "Legal & Compliance",
        "aliases": ["case law research", "lexis"],
    },
    {
        "name": "Litigation Support",
        "family": "Legal & Compliance",
        "aliases": ["trial prep", "e-discovery"],
    },
    {
        "name": "Intellectual Property",
        "family": "Legal & Compliance",
        "aliases": ["ip law", "patents", "trademarks"],
    },
    {
        "name": "Corporate Governance",
        "family": "Legal & Compliance",
        "aliases": ["board governance"],
    },
]


def clean_skill_name(name: str) -> str:
    """Clean skill title, stripping version numbers or bracket notes."""
    name = re.sub(r"\s*\(.*?\)", "", name)
    name = re.sub(r"\s+software$", "", name, flags=re.IGNORECASE)
    return name.strip()


def compile_taxonomy() -> dict[str, Any]:
    raw_path = Path(__file__).resolve().parent.parent / "data" / "onet_technology_skills.txt"
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

    # Integrate non-tech domain skills
    for dskill in DOMAIN_NON_TECH_SKILLS:
        cname = dskill["name"]
        norm_cname = cname.lower()
        fam = dskill["family"]
        aliases = [norm_cname] + [a.lower() for a in dskill.get("aliases", [])]

        if norm_cname not in skills_by_canonical:
            skills_by_canonical[norm_cname] = {
                "canonical_name": cname,
                "family": fam,
                "aliases": aliases,
                "hot_technology": True,
                "in_demand": True,
            }
            family_counts[fam] = family_counts.get(fam, 0) + 1
        else:
            for a in aliases:
                if a not in skills_by_canonical[norm_cname]["aliases"]:
                    skills_by_canonical[norm_cname]["aliases"].append(a)

    # Retain ALL canonical skills (full O*NET 8,746 + domain non-tech + curated)
    selected_skills = list(skills_by_canonical.values())

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
            "source": "O*NET 29.0 Technology Skills & ESCO/Domain Expanded Taxonomy",
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
