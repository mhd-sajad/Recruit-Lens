"""Generate parser_holdout_30_fresh_v3.csv from 30 previously-unused resumes."""

import csv
import hashlib
import random
import shutil
import subprocess
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.pdf_parser import parse_resume_pdf  # noqa: E402


def get_excluded_ids() -> tuple[set[str], set[str], set[str], set[str], set[str]]:
    """Return (first_100, dev_30, audit_40, dev_fresh_30, dev2_30) ID sets."""
    sample_dir = Path("data/resumes_sample_300")
    all_real_pdfs = sorted(sample_dir.rglob("*.pdf"))

    # First-100 (same logic as measure_parser.py)
    random.seed(42)
    selected_100 = random.sample(all_real_pdfs, 100)
    first_100 = set(p.stem for p in selected_100)

    # Dev holdout 30 (DEV set 1)
    dev_30 = set()
    with open("data/parser_holdout_30.csv") as f:
        for row in csv.DictReader(f):
            dev_30.add(row["resume_id"])

    # Audit 40
    audit_40 = set()
    with open("data/parser_audit_40.csv") as f:
        for row in csv.DictReader(f):
            audit_40.add(row["resume_id"])

    # Fresh holdout 30 (DEV set 1 fresh)
    dev_fresh = set()
    with open("data/parser_holdout_30_fresh.csv") as f:
        for row in csv.DictReader(f):
            dev_fresh.add(row["resume_id"])

    # Fresh holdout 30 v2 (DEV set 2)
    dev2_30 = set()
    with open("data/parser_holdout_30_fresh_v2.csv") as f:
        for row in csv.DictReader(f):
            dev2_30.add(row["resume_id"])

    return first_100, dev_30, audit_40, dev_fresh, dev2_30


def find_pdf(resume_id: str, sample_dir: Path) -> Path | None:
    """Find the PDF for a given resume ID in the sample directory."""
    matches = list(sample_dir.rglob(f"{resume_id}.pdf"))
    return matches[0] if matches else None


def main() -> None:
    sample_dir = Path("data/resumes_sample_300")

    first_100, dev_30, audit_40, dev_fresh, dev2_30 = get_excluded_ids()
    excluded = first_100 | dev_30 | audit_40 | dev_fresh | dev2_30

    all_ids = sorted(set(p.stem for p in sample_dir.rglob("*.pdf")))
    eligible = sorted(set(all_ids) - excluded)

    random.seed(2027)
    selected_30 = sorted(random.sample(eligible, 30))

    # Get git commit hash of the parser
    parser_path = backend_dir / "app" / "core" / "experience_extractor.py"
    git_hash = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", str(parser_path)],
        text=True,
    ).strip()

    csv_path = Path("data/parser_holdout_30_fresh_v3.csv")
    rows = []

    for resume_id in selected_30:
        pdf_path = find_pdf(resume_id, sample_dir)
        if pdf_path is None:
            print(f"WARNING: No PDF found for {resume_id}", file=sys.stderr)
            continue

        result = parse_resume_pdf(str(pdf_path))
        experiences = result.experiences

        if not experiences:
            raw_lines = (result.sections.get("experience") or result.raw_text)[:300]
            rows.append(
                {
                    "resume_id": resume_id,
                    "raw_experience_lines": raw_lines,
                    "extracted_title": "",
                    "extracted_company": "",
                    "start_date": "",
                    "end_date": "",
                }
            )
        else:
            for exp in experiences:
                raw_lines = exp.raw_text or ""
                if exp.bullets:
                    raw_lines = raw_lines + " | " + " | ".join(exp.bullets[:3])
                rows.append(
                    {
                        "resume_id": resume_id,
                        "raw_experience_lines": raw_lines[:300],
                        "extracted_title": exp.title or "",
                        "extracted_company": exp.company or "",
                        "start_date": exp.start_date or "",
                        "end_date": exp.end_date or "",
                    }
                )

    fieldnames = [
        "resume_id",
        "raw_experience_lines",
        "extracted_title",
        "extracted_company",
        "start_date",
        "end_date",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with open(csv_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    meta_path = Path("data/parser_holdout_30_fresh_v3.meta.txt")
    meta_content = f"""parser_commit: {git_hash}
row_count: {len(rows) + 1}
data_rows: {len(rows)}
resume_ids: {','.join(selected_30)}
sha256: {file_hash}
seed: 2027
excluded_first_100: {len(first_100)}
excluded_dev_30: {len(dev_30)}
excluded_audit_40: {len(audit_40)}
excluded_dev_fresh: {len(dev_fresh)}
excluded_dev2_30: {len(dev2_30)}
eligible_pool: {len(eligible)}
"""
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(meta_content)

    # Copy ONLY the CSV to ~/recruit_lens_review/parser_holdout_30_fresh_v3.csv
    review_dir = Path.home() / "recruit_lens_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    target_csv = review_dir / "parser_holdout_30_fresh_v3.csv"
    shutil.copy2(csv_path, target_csv)

    print(f"Generated {csv_path} ({len(rows)} rows from 30 resumes)")
    print(f"Metadata written to {meta_path}")
    print(f"Copied CSV to {target_csv}")


if __name__ == "__main__":
    main()
