"""Generate parser_holdout_30_fresh_v2.csv from 30 previously-unused resumes."""
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


def get_excluded_ids() -> tuple[set[str], set[str], set[str], set[str]]:
    """Return (first_100, dev_30, audit_40, dev2_30) ID sets."""
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

    # Fresh holdout 30 (DEV set 2)
    dev2_30 = set()
    with open("data/parser_holdout_30_fresh.csv") as f:
        for row in csv.DictReader(f):
            dev2_30.add(row["resume_id"])

    return first_100, dev_30, audit_40, dev2_30


def find_pdf(resume_id: str, sample_dir: Path) -> Path | None:
    """Find the PDF for a given resume ID in the sample directory."""
    matches = list(sample_dir.rglob(f"{resume_id}.pdf"))
    return matches[0] if matches else None


def main() -> None:
    sample_dir = Path("data/resumes_sample_300")

    first_100, dev_30, audit_40, dev2_30 = get_excluded_ids()
    excluded = first_100 | dev_30 | audit_40 | dev2_30

    all_ids = sorted(set(p.stem for p in sample_dir.rglob("*.pdf")))
    eligible = sorted(set(all_ids) - excluded)

    random.seed(2026)
    selected_30 = sorted(random.sample(eligible, 30))

    # Get git commit hash of the parser
    parser_path = backend_dir / "app" / "core" / "experience_extractor.py"
    git_hash = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", str(parser_path)],
        text=True,
    ).strip()

    csv_path = Path("data/parser_holdout_30_fresh_v2.csv")
    rows = []

    for resume_id in selected_30:
        pdf_path = find_pdf(resume_id, sample_dir)
        if pdf_path is None:
            print(f"WARNING: No PDF found for {resume_id}", file=sys.stderr)
            continue

        result = parse_resume_pdf(str(pdf_path))
        experiences = result.experiences

        if not experiences:
            # Still write one row with empty fields
            raw_lines = (result.sections.get("experience") or result.raw_text)[:300]
            rows.append({
                "resume_id": resume_id,
                "raw_experience_lines": raw_lines,
                "extracted_title": "",
                "extracted_company": "",
                "start_date": "",
                "end_date": "",
            })
        else:
            for exp in experiences:
                raw_line = (exp.raw_text or "")[:300]
                rows.append({
                    "resume_id": resume_id,
                    "raw_experience_lines": raw_line,
                    "extracted_title": exp.title or "",
                    "extracted_company": exp.company or "",
                    "start_date": exp.start_date or "",
                    "end_date": exp.end_date or "",
                })

    # Write CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "resume_id",
                "raw_experience_lines",
                "extracted_title",
                "extracted_company",
                "start_date",
                "end_date",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    # Compute SHA256 of the CSV
    with open(csv_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()

    meta_path = Path("data/parser_holdout_30_fresh_v2.meta.txt")
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(f"parser_commit: {git_hash}\n")
        f.write(f"row_count: {len(rows) + 1}\n")  # including header
        f.write(f"data_rows: {len(rows)}\n")
        f.write(f"resume_ids: {','.join(selected_30)}\n")
        f.write(f"sha256: {sha256}\n")
        f.write("seed: 2026\n")
        f.write(f"excluded_first_100: {len(first_100)}\n")
        f.write(f"excluded_dev_30: {len(dev_30)}\n")
        f.write(f"excluded_audit_40: {len(audit_40)}\n")
        f.write(f"excluded_dev2_30: {len(dev2_30)}\n")
        f.write(f"eligible_pool: {len(eligible)}\n")

    # Copy to ~/recruit_lens_review/parser_holdout_30_fresh_v2.csv
    review_dir = Path.home() / "recruit_lens_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    dest = review_dir / "parser_holdout_30_fresh_v2.csv"
    shutil.copy2(csv_path, dest)

    print("=== Fresh Holdout V2 Generated Successfully ===")
    print(f"Path: {dest.resolve()}")
    print(f"Data Rows: {len(rows)} (Total lines: {len(rows) + 1})")
    print(f"SHA256: {sha256}")
    print(f"Selected Resume IDs ({len(selected_30)}): {selected_30}")


if __name__ == "__main__":
    main()
