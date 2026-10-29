"""
measure_taxonomy_coverage.py

Evaluates taxonomy coverage across all 24 resume categories (300 resumes)
and JD job families (2,000 JDs).
Identifies dropped skills and tests whether non-tech coverage falls below 60%.
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
backend_dir = repo_root / "backend"
sys.path.insert(0, str(backend_dir))

from scripts.provenance_helper import get_provenance
from app.core.taxonomy import SkillTaxonomy
from app.core.pdf_parser import parse_resume_pdf


def main():
    repo_root = Path(__file__).resolve().parent.parent
    taxonomy = SkillTaxonomy.get_instance()

    # 1. Dropped skills analysis
    raw_path = repo_root / "data" / "onet_technology_skills.txt"
    all_raw_canonical = {}
    family_counts_all = defaultdict(int)

    with open(raw_path, encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            s = row.get("Example", "").strip()
            fam = row.get("Commodity Title", "Other").strip()
            if s and len(s) >= 2:
                norm = s.lower()
                if norm not in all_raw_canonical:
                    all_raw_canonical[norm] = {"name": s, "family": fam}
                    family_counts_all[fam] += 1

    total_canonical = len(all_raw_canonical)

    with open(repo_root / "backend" / "app" / "data" / "skills_taxonomy.json") as f:
        tax = json.load(f)
    current_skills = {s["canonical_name"].lower(): s for s in tax.get("skills", [])}

    dropped = {k: v for k, v in all_raw_canonical.items() if k not in current_skills}
    dropped_by_family = defaultdict(int)
    for v in dropped.values():
        dropped_by_family[v["family"]] += 1

    top_dropped_families = sorted(dropped_by_family.items(), key=lambda x: x[1], reverse=True)[:10]

    print("=" * 70)
    print("DROPPED SKILLS ANALYSIS (8,754 -> 2,500)")
    print("=" * 70)
    print(f"Total Canonical O*NET Skills in file: {total_canonical}")
    print(f"Retained in current taxonomy: {len(current_skills)}")
    print(f"Dropped count: {len(dropped)} ({len(dropped) / total_canonical * 100:.1f}%)")
    print("\nTop 10 Families of Dropped Skills:")
    for fam, cnt in top_dropped_families:
        print(f"  - {fam}: {cnt} dropped")

    # 2. Coverage across all 24 resume categories (300 resumes)
    resumes_dir = repo_root / "data" / "resumes_sample_300"
    categories = sorted([d.name for d in resumes_dir.iterdir() if d.is_dir()])
    print(f"\nAnalyzing coverage across {len(categories)} resume categories (300 PDFs)...")

    category_stats = {}
    weak_categories = []

    for cat in categories:
        cat_dir = resumes_dir / cat
        pdfs = list(cat_dir.glob("*.pdf"))
        skill_counts = []

        for pdf in pdfs:
            parsed = parse_resume_pdf(pdf, resume_id=pdf.stem)
            skills = taxonomy.extract_skills_from_text(parsed.raw_text)
            skill_counts.append(len(skills))

        n = len(skill_counts)
        if n == 0:
            continue

        median_skills = float(np.median(skill_counts))
        mean_skills = float(np.mean(skill_counts))
        pct_ge_3 = float(np.mean([1.0 if s >= 3 else 0.0 for s in skill_counts])) * 100.0

        category_stats[cat] = {
            "total_resumes": n,
            "median_skills": median_skills,
            "mean_skills": round(mean_skills, 1),
            "pct_ge_3": round(pct_ge_3, 1),
        }

        if pct_ge_3 < 60.0:
            weak_categories.append((cat, pct_ge_3, median_skills))

    print("\n" + "=" * 70)
    print("RESUME TAXONOMY COVERAGE BY CATEGORY (24 Categories, 300 Resumes)")
    print("=" * 70)
    print(f"{'Category':<25} | {'Count':<5} | {'Median':<6} | {'Mean':<6} | {'% >= 3 Skills':<15}")
    print("-" * 70)
    for cat, stats in sorted(category_stats.items(), key=lambda x: x[1]["pct_ge_3"]):
        print(
            f"{cat:<25} | {stats['total_resumes']:<5} | {stats['median_skills']:<6.1f} | "
            f"{stats['mean_skills']:<6.1f} | {stats['pct_ge_3']:<5.1f}%"
        )

    print("\nWeak categories (<60% with >= 3 skills):", weak_categories)

    # 3. Coverage across JD job families in jds_sample_2000.csv
    jds_csv = repo_root / "data" / "jds_sample_2000.csv"
    jd_family_skills = defaultdict(list)

    if jds_csv.exists():

        def classify_title(t: str) -> str:
            tl = t.lower()
            if any(
                k in tl
                for k in [
                    "engineer",
                    "developer",
                    "software",
                    "tech",
                    "data",
                    "cloud",
                    "security",
                    "architect",
                    "sysadmin",
                ]
            ):
                return "Software & Tech"
            if any(
                k in tl
                for k in [
                    "nurse",
                    "medical",
                    "health",
                    "clinical",
                    "physician",
                    "dental",
                    "pharmacy",
                ]
            ):
                return "Healthcare & Medical"
            if any(
                k in tl
                for k in [
                    "finance",
                    "accountant",
                    "accounting",
                    "audit",
                    "tax",
                    "banking",
                    "treasury",
                ]
            ):
                return "Finance & Accounting"
            if any(
                k in tl
                for k in [
                    "sales",
                    "marketing",
                    "business development",
                    "account exec",
                    "advertising",
                ]
            ):
                return "Sales & Marketing"
            if any(
                k in tl
                for k in [
                    "hr",
                    "human resources",
                    "recruiter",
                    "talent",
                    "operations",
                    "logistics",
                    "supply chain",
                ]
            ):
                return "HR & Operations"
            if any(k in tl for k in ["design", "ux", "ui", "graphic", "creative", "art"]):
                return "Design & Creative"
            if any(k in tl for k in ["legal", "counsel", "attorney", "paralegal", "compliance"]):
                return "Legal & Compliance"
            return "Other / General"

        with open(jds_csv, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("title", "")
                fam = classify_title(title)
                desc = (
                    row.get("description", "")
                    or row.get("job_description", "")
                    or row.get("text", "")
                )
                if desc:
                    sk = taxonomy.extract_skills_from_text(desc[:2000])
                    jd_family_skills[fam].append(len(sk))

        print("\n" + "=" * 70)
        print("JD TAXONOMY COVERAGE BY JOB FAMILY")
        print("=" * 70)
        jd_stats = {}
        for fam, counts in sorted(jd_family_skills.items()):
            med = float(np.median(counts))
            mean_val = float(np.mean(counts))
            pct_ge_3 = float(np.mean([1.0 if c >= 3 else 0.0 for c in counts])) * 100.0
            jd_stats[fam] = {
                "count": len(counts),
                "median_skills": med,
                "mean_skills": round(mean_val, 1),
                "pct_ge_3": round(pct_ge_3, 1),
            }
            print(
                f"{fam:<25} | {len(counts):<5} | Med: {med:<4.1f} | Mean: {mean_val:<4.1f} | >=3: {pct_ge_3:<5.1f}%"
            )
    else:
        jd_stats = {}

    onet_skills_retained = total_canonical - len(dropped)
    curated_domain_skills_added = len(current_skills) - onet_skills_retained
    reconciliation_statement = (
        f"Of the {total_canonical:,} raw O*NET technology skills, {onet_skills_retained:,} ({(onet_skills_retained / total_canonical) * 100:.1f}%) "
        f"were retained and {len(dropped):,} ({(len(dropped) / total_canonical) * 100:.1f}%) niche software titles were dropped. "
        f"An additional {curated_domain_skills_added:,} domain-curated and non-technical skills were added, "
        f"yielding a total taxonomy size of {len(current_skills):,} skills."
    )

    out_json = repo_root / "docs" / "taxonomy_coverage_report.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": get_provenance("scripts/measure_taxonomy_coverage.py"),
                "dropped_analysis": {
                    "total_canonical": total_canonical,
                    "retained": len(current_skills),
                    "dropped": len(dropped),
                    "onet_skills_retained": onet_skills_retained,
                    "curated_domain_skills_added": curated_domain_skills_added,
                    "reconciliation_statement": reconciliation_statement,
                    "top_dropped_families": top_dropped_families,
                },
                "category_stats": category_stats,
                "weak_categories": weak_categories,
                "jd_stats": jd_stats,
            },
            f,
            indent=2,
        )
    print(f"\nSaved coverage report to {out_json}")


if __name__ == "__main__":
    main()
