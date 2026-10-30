"""
Weak-Supervision Pair Dataset Generator

Crosses resume categories with job description titles to construct:
1. Positives: Candidates and jobs from the same family with varying must-have coverage.
2. Hard Negatives: Candidates and jobs from adjacent/neighboring functional families.
3. Easy Negatives: Candidates and jobs from completely disjoint functional families.

Computes 10-feature vectors with keyword stuffing guards, graded proxy scores,
and discrete recruitment tiers.

LIMITATIONS & DISCLAIMER:
Labels in this dataset are weak supervision heuristic proxies. They reflect automated
must-have skill coverage and occupational family alignment, NOT empirical hiring outcomes,
human interview performance, or job success.
"""

import csv
import json
import logging
import random
from pathlib import Path
from typing import Any

from app.core.features import CandidateFeatureVector, extract_candidate_features
from app.core.jd_requirements import extract_job_requirements
from app.core.pdf_parser import parse_resume_pdf
from app.core.skill_extractor import extract_skills_from_parsed_resume
from app.core.taxonomy import SkillTaxonomy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("weak_supervision")

# Occupational family taxonomy mapping 24 resume folders to macro families
RESUME_CATEGORY_FAMILIES: dict[str, str] = {
    "INFORMATION-TECHNOLOGY": "Technology & Engineering",
    "ENGINEERING": "Technology & Engineering",
    "FINANCE": "Finance & Accounting",
    "ACCOUNTANT": "Finance & Accounting",
    "BANKING": "Finance & Accounting",
    "SALES": "Sales & Business",
    "BUSINESS-DEVELOPMENT": "Sales & Business",
    "CONSULTANT": "Sales & Business",
    "BPO": "Sales & Business",
    "HR": "Human Resources & Admin",
    "PUBLIC-RELATIONS": "Human Resources & Admin",
    "HEALTHCARE": "Healthcare & Wellness",
    "FITNESS": "Healthcare & Wellness",
    "DESIGNER": "Creative & Design",
    "DIGITAL-MEDIA": "Creative & Design",
    "ARTS": "Creative & Design",
    "APPAREL": "Creative & Design",
    "TEACHER": "Education & Instruction",
    "ADVOCATE": "Legal & Compliance",
    "CHEF": "Culinary & Hospitality",
    "AVIATION": "Transport & Logistics",
    "AUTOMOBILE": "Transport & Logistics",
    "CONSTRUCTION": "Trades & Industrial",
    "AGRICULTURE": "Trades & Industrial",
}

# Adjacent families for generating hard negatives
ADJACENT_FAMILIES: dict[str, list[str]] = {
    "Technology & Engineering": [
        "Creative & Design",
        "Sales & Business",
        "Trades & Industrial",
    ],
    "Finance & Accounting": [
        "Sales & Business",
        "Legal & Compliance",
        "Human Resources & Admin",
    ],
    "Sales & Business": [
        "Finance & Accounting",
        "Human Resources & Admin",
        "Technology & Engineering",
    ],
    "Human Resources & Admin": [
        "Sales & Business",
        "Legal & Compliance",
        "Education & Instruction",
    ],
    "Healthcare & Wellness": ["Education & Instruction", "Creative & Design"],
    "Creative & Design": ["Technology & Engineering", "Sales & Business"],
    "Education & Instruction": ["Human Resources & Admin", "Healthcare & Wellness"],
    "Legal & Compliance": ["Finance & Accounting", "Human Resources & Admin"],
    "Culinary & Hospitality": ["Healthcare & Wellness", "Sales & Business"],
    "Transport & Logistics": ["Trades & Industrial", "Technology & Engineering"],
    "Trades & Industrial": ["Transport & Logistics", "Technology & Engineering"],
}


def map_jd_title_to_family(title: str) -> str | None:
    """Classify a JD title into a macro family using deterministic pattern matching."""
    t = title.lower()
    if any(
        w in t
        for w in [
            "software",
            "developer",
            "engineer",
            "devops",
            "cloud",
            "data",
            "it",
            "architect",
            "programmer",
            "tech",
        ]
    ):
        return "Technology & Engineering"
    if any(
        w in t
        for w in [
            "accountant",
            "accounting",
            "financial",
            "finance",
            "audit",
            "tax",
            "banking",
            "treasury",
            "credit",
        ]
    ):
        return "Finance & Accounting"
    if any(
        w in t
        for w in [
            "sales",
            "account executive",
            "business development",
            "consultant",
            "bpo",
            "client",
            "commercial",
            "revenue",
        ]
    ):
        return "Sales & Business"
    if any(
        w in t
        for w in [
            "hr",
            "human resources",
            "talent",
            "recruiter",
            "people",
            "public relations",
            "pr",
            "communications",
        ]
    ):
        return "Human Resources & Admin"
    if any(
        w in t
        for w in [
            "nurse",
            "medical",
            "health",
            "clinical",
            "physician",
            "fitness",
            "trainer",
            "therapy",
        ]
    ):
        return "Healthcare & Wellness"
    if any(
        w in t
        for w in [
            "designer",
            "ui",
            "ux",
            "graphic",
            "art",
            "media",
            "creative",
            "video",
            "content",
        ]
    ):
        return "Creative & Design"
    if any(
        w in t
        for w in [
            "teacher",
            "instructor",
            "professor",
            "education",
            "tutor",
            "academic",
            "faculty",
        ]
    ):
        return "Education & Instruction"
    if any(
        w in t
        for w in [
            "attorney",
            "counsel",
            "legal",
            "lawyer",
            "paralegal",
            "compliance",
            "regulatory",
        ]
    ):
        return "Legal & Compliance"
    if any(
        w in t
        for w in [
            "chef",
            "cook",
            "culinary",
            "restaurant",
            "hospitality",
            "hotel",
            "food",
        ]
    ):
        return "Culinary & Hospitality"
    if any(
        w in t
        for w in [
            "pilot",
            "flight",
            "aviation",
            "mechanic",
            "driver",
            "transport",
            "logistics",
            "fleet",
        ]
    ):
        return "Transport & Logistics"
    if any(
        w in t
        for w in [
            "construction",
            "site",
            "civil",
            "carpenter",
            "electrician",
            "plumber",
            "farm",
            "agriculture",
        ]
    ):
        return "Trades & Industrial"
    return None


def calculate_weak_supervision_target(
    pair_type: str,
    features: CandidateFeatureVector,
    has_same_family: bool,
) -> tuple[float, int]:
    """
    Compute continuous target score [0.0, 1.0] and discrete tier [0, 1, 2, 3]
    (0=Reject, 1=Hold, 2=Interview, 3=Strong Fit).
    """
    must_cov = features.must_have_coverage.value
    nice_cov = features.nice_to_have_coverage.value
    years_gap = features.years_gap.value
    edu_match = features.education_match.value
    title_sim = features.title_match.value

    if pair_type == "easy_negative":
        # Disjoint functional domain: strictly low score and Reject tier
        score = min(0.18, 0.05 + 0.10 * title_sim)
        return round(float(score), 4), 0

    if pair_type == "hard_negative":
        # Adjacent family: partial overlap, typically Hold or Reject
        score = 0.15 + 0.20 * must_cov + 0.05 * title_sim
        score = min(0.40, max(0.10, score))
        tier = 1 if (must_cov >= 0.5 and score >= 0.30) else 0
        return round(float(score), 4), tier

    # Positive pair: same macro family
    # Must-have coverage is the dominant component
    years_penalty = 0.10 if years_gap < -2.0 else 0.0
    edu_bonus = 0.05 * edu_match

    score = 0.20 + 0.50 * must_cov + 0.15 * nice_cov + 0.10 * title_sim + edu_bonus - years_penalty
    score = min(1.0, max(0.15, score))

    # Tier assignment with strict must-have override:
    # Strong Fit requires 100% must-have coverage (0 missing must-haves) and meeting experience bounds
    missing_must_cnt = features.missing_must_count.value
    if must_cov >= 1.0 and missing_must_cnt == 0 and years_gap >= -1.0 and score >= 0.72:
        tier = 3  # Strong Fit
    elif must_cov >= 0.50 and score >= 0.50:
        tier = 2  # Interview
    elif must_cov >= 0.25 or score >= 0.35:
        tier = 1  # Hold
    else:
        tier = 0  # Reject

    return round(float(score), 4), tier


def main() -> None:
    random.seed(42)
    taxonomy = SkillTaxonomy.get_instance()

    # 1. Load and parse representative candidate resumes (5 per category = 120 resumes)
    resumes_dir = Path("data/resumes_sample_300")
    candidate_cache: list[dict[str, Any]] = []

    cache_path = Path("data/parsed_resumes_cache_120.json")
    if cache_path.exists():
        logger.info("Loading cached parsed resumes from %s...", cache_path)
        with open(cache_path, encoding="utf-8") as f:
            raw_cache = json.load(f)
        for item in raw_cache:
            parsed = (
                parse_resume_pdf.models.ResumeParseResult.model_validate(item["parsed"])
                if hasattr(parse_resume_pdf, "models")
                else None
            )
            # Reconstruct ResumeParseResult from dict
            from app.core.models import ResumeParseResult

            parsed_obj = ResumeParseResult.model_validate(item["parsed"])
            skills = extract_skills_from_parsed_resume(parsed_obj, taxonomy=taxonomy)
            candidate_cache.append(
                {
                    "resume_id": item["resume_id"],
                    "category": item["category"],
                    "family": item["family"],
                    "parsed": parsed_obj,
                    "skills": skills,
                }
            )
    else:
        logger.info("Scanning and parsing resumes from %s...", resumes_dir)
        cat_dirs = sorted([d for d in resumes_dir.iterdir() if d.is_dir()])
        serializable_cache: list[dict[str, Any]] = []

        for cat_dir in cat_dirs:
            cat_name = cat_dir.name
            family = RESUME_CATEGORY_FAMILIES.get(cat_name, "General")
            pdf_files = sorted(cat_dir.glob("*.pdf"))[:5]  # Take 5 balanced per category

            for pdf_path in pdf_files:
                try:
                    parsed = parse_resume_pdf(pdf_path)
                    skills = extract_skills_from_parsed_resume(parsed, taxonomy=taxonomy)
                    candidate_cache.append(
                        {
                            "resume_id": parsed.resume_id,
                            "category": cat_name,
                            "family": family,
                            "parsed": parsed,
                            "skills": skills,
                        }
                    )
                    serializable_cache.append(
                        {
                            "resume_id": parsed.resume_id,
                            "category": cat_name,
                            "family": family,
                            "parsed": parsed.model_dump(),
                        }
                    )
                except (ValueError, OSError, RuntimeError) as e:
                    logger.warning("Failed to parse %s: %s", pdf_path, e)

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(serializable_cache, f)
        logger.info("Saved %d parsed resumes to %s", len(serializable_cache), cache_path)

    logger.info("Loaded %d candidates for weak supervision.", len(candidate_cache))

    # 2. Load and filter diverse JDs from sample CSV
    jds_csv = Path("data/jds_sample_2000.csv")
    jds_by_family: dict[str, list[dict[str, Any]]] = {}

    logger.info("Reading JDs from %s...", jds_csv)
    with open(jds_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get("title", "").strip()
            desc = row.get("description", "").strip()
            if not title or len(desc) < 100:
                continue

            family = map_jd_title_to_family(title)
            if not family:
                continue

            if family not in jds_by_family:
                jds_by_family[family] = []

            if len(jds_by_family[family]) < 10:  # Up to 10 JDs per family
                job_id = row.get("job_id", f"job_{len(jds_by_family[family])}")
                reqs = extract_job_requirements(desc, job_id=job_id, title=title, taxonomy=taxonomy)
                # Keep JDs with at least some skills identified
                if len(reqs.must_have_skills) + len(reqs.nice_to_have_skills) >= 2:
                    jds_by_family[family].append(
                        {
                            "job_id": job_id,
                            "title": title,
                            "family": family,
                            "reqs": reqs,
                        }
                    )

    total_jds = sum(len(j) for j in jds_by_family.values())
    logger.info(
        "Extracted requirements for %d JDs across %d families.",
        total_jds,
        len(jds_by_family),
    )

    # 3. Construct Balanced Pairs (Positives, Hard Negatives, Easy Negatives)
    pairs: list[dict[str, Any]] = []
    pair_id_counter = 1

    for cand in candidate_cache:
        cand_family = cand["family"]
        cand_parsed = cand["parsed"]
        cand_skills = cand["skills"]

        # Positive pairs: JDs in the same family
        same_jds = jds_by_family.get(cand_family, [])
        for jd in same_jds[:4]:
            feats = extract_candidate_features(
                cand_parsed,
                jd["reqs"],
                candidate_skills=cand_skills,
                taxonomy=taxonomy,
            )
            score, tier = calculate_weak_supervision_target("positive", feats, True)
            pairs.append(
                {
                    "pair_id": f"pair_{pair_id_counter:05d}",
                    "pair_type": "positive",
                    "resume_id": cand["resume_id"],
                    "resume_category": cand["category"],
                    "candidate_family": cand_family,
                    "job_id": jd["job_id"],
                    "job_title": jd["title"],
                    "job_family": jd["family"],
                    "features": feats.to_feature_dict(),
                    "target_score": score,
                    "target_tier": tier,
                    "label_provenance": "weak_supervision_proxy_v1",
                }
            )
            pair_id_counter += 1

        # Hard negative pairs: JDs in adjacent families
        adj_families = ADJACENT_FAMILIES.get(cand_family, [])
        adj_jds: list[dict[str, Any]] = []
        for af in adj_families:
            adj_jds.extend(jds_by_family.get(af, []))

        if adj_jds:
            sampled_adj = random.sample(adj_jds, min(len(adj_jds), 3))
            for jd in sampled_adj:
                feats = extract_candidate_features(
                    cand_parsed,
                    jd["reqs"],
                    candidate_skills=cand_skills,
                    taxonomy=taxonomy,
                )
                score, tier = calculate_weak_supervision_target("hard_negative", feats, False)
                pairs.append(
                    {
                        "pair_id": f"pair_{pair_id_counter:05d}",
                        "pair_type": "hard_negative",
                        "resume_id": cand["resume_id"],
                        "resume_category": cand["category"],
                        "candidate_family": cand_family,
                        "job_id": jd["job_id"],
                        "job_title": jd["title"],
                        "job_family": jd["family"],
                        "features": feats.to_feature_dict(),
                        "target_score": score,
                        "target_tier": tier,
                        "label_provenance": "weak_supervision_proxy_v1",
                    }
                )
                pair_id_counter += 1

        # Easy negative pairs: completely disjoint families
        disjoint_families = [f for f in jds_by_family if f != cand_family and f not in adj_families]
        disjoint_jds: list[dict[str, Any]] = []
        for df in disjoint_families:
            disjoint_jds.extend(jds_by_family.get(df, []))

        if disjoint_jds:
            sampled_disjoint = random.sample(disjoint_jds, min(len(disjoint_jds), 2))
            for jd in sampled_disjoint:
                feats = extract_candidate_features(
                    cand_parsed,
                    jd["reqs"],
                    candidate_skills=cand_skills,
                    taxonomy=taxonomy,
                )
                score, tier = calculate_weak_supervision_target("easy_negative", feats, False)
                pairs.append(
                    {
                        "pair_id": f"pair_{pair_id_counter:05d}",
                        "pair_type": "easy_negative",
                        "resume_id": cand["resume_id"],
                        "resume_category": cand["category"],
                        "candidate_family": cand_family,
                        "job_id": jd["job_id"],
                        "job_title": jd["title"],
                        "job_family": jd["family"],
                        "features": feats.to_feature_dict(),
                        "target_score": score,
                        "target_tier": tier,
                        "label_provenance": "weak_supervision_proxy_v1",
                    }
                )
                pair_id_counter += 1

    # 4. Output dataset with metadata and honest limitations
    output_path = Path("data/weak_supervision_pairs.json")
    dataset_summary = {
        "metadata": {
            "total_pairs": len(pairs),
            "total_candidates": len(candidate_cache),
            "total_jobs": total_jds,
            "pair_distribution": {
                "positive": sum(1 for p in pairs if p["pair_type"] == "positive"),
                "hard_negative": sum(1 for p in pairs if p["pair_type"] == "hard_negative"),
                "easy_negative": sum(1 for p in pairs if p["pair_type"] == "easy_negative"),
            },
            "tier_distribution": {
                "3_strong_fit": sum(1 for p in pairs if p["target_tier"] == 3),
                "2_interview": sum(1 for p in pairs if p["target_tier"] == 2),
                "1_hold": sum(1 for p in pairs if p["target_tier"] == 1),
                "0_reject": sum(1 for p in pairs if p["target_tier"] == 0),
            },
            "limitations_disclaimer": (
                "Weak supervision labels are automated heuristic proxies derived from occupational "
                "family alignment, must-have skill coverage, and structured date parsing. They are NOT "
                "empirical hiring outcomes, real interview performance scores, or human recruitment decisions. "
                "Models trained or evaluated on this dataset learn deterministic requirement matching rules, "
                "not holistic workplace suitability."
            ),
        },
        "pairs": pairs,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset_summary, f, indent=2)

    logger.info(
        "Successfully generated %d weak supervision pairs saved to %s",
        len(pairs),
        output_path,
    )
    logger.info("Distribution: %s", dataset_summary["metadata"]["pair_distribution"])
    logger.info("Tier Distribution: %s", dataset_summary["metadata"]["tier_distribution"])


if __name__ == "__main__":
    main()
