"""Align parser extracted entries against reviewer ground-truth labels on DEV set 2 (data/parser_holdout_30_fresh.csv).

Reviewer labels per resume in CSV order:
O = clean title
C = real job with noise attached
W = real job with title missing or wrong
F = not a job (fragment)
D = duplicate
? = cannot tell
"""

import csv
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(repo_root))

from app.core.pdf_parser import parse_resume_pdf
from scripts.provenance_helper import get_provenance

FRESH_LABELS = {
    "10466583": "OOOO",
    "12155206": "OFOWOOOO",
    "12904972": "OOOO",
    "13294301": "OOODDD",
    "15651486": "OOOFFOO",
    "16276121": "OO?",
    "16511249": "OOOOOOOOOOOO??",
    "18795567": "OCWF",
    "23914451": "OOOFOO",
    "24416961": "FOOOOO",
    "24533931": "OOO",
    "25150191": "OFOOO",
    "27024099": "?OO?WOO",
    "27914096": "OOFOO",
    "28298773": "OOCO",
    "29072179": "OWOOOO",
    "29173771": "DOOO",
    "29221006": "OOO",
    "29406313": "OOOOOOO",
    "29897742": "OOO",
    "34452806": "OOOO",
    "36102323": "OO",
    "37087824": "OOOO",
    "37472265": "WOOO",
    "37521676": "OOOOOOOFOFDDDDDDDDDD",
    "43378989": "OOO",
    "58048626": "OFOO",
    "62994611": "OOODDD",
    "91467795": "OOOOOOO",
    "93002334": "OFFOOFOW",
}


def main() -> None:
    holdout_csv = repo_root / "data" / "parser_holdout_30_fresh.csv"
    sample_dir = repo_root / "data" / "resumes_sample_300"

    # Read CSV rows grouped by resume_id
    rows_by_resume = {}
    with open(holdout_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rid = r["resume_id"]
            rows_by_resume.setdefault(rid, []).append(r)

    # Attach labels
    labeled_rows_by_resume = {}
    total_rows = 0
    total_real = 0
    total_frags = 0
    total_dups = 0
    total_unclear = 0

    for rid, rows in rows_by_resume.items():
        code = FRESH_LABELS.get(rid, "")
        if len(code) != len(rows):
            print(f"ERROR: Label code length {len(code)} != row count {len(rows)} for {rid}")
            sys.exit(1)
        labeled_rows = []
        for i, row in enumerate(rows):
            lbl = code[i]
            labeled_rows.append({**row, "label": lbl})
            total_rows += 1
            if lbl in ("O", "C", "W"):
                total_real += 1
            elif lbl == "F":
                total_frags += 1
            elif lbl == "D":
                total_dups += 1
            elif lbl == "?":
                total_unclear += 1
        labeled_rows_by_resume[rid] = labeled_rows

    print(
        f"Total CSV Rows: {total_rows} | Real: {total_real} | Fragments: {total_frags} | Duplicates: {total_dups} | Unclear: {total_unclear}"
    )

    # Now run current parser and align
    matched_real = 0
    missed_real = 0
    spurious_extracted = 0
    titles_wrong = 0
    duplicates_dropped = 0
    total_extracted_entries = 0

    per_resume_report = []

    for rid, labeled_rows in labeled_rows_by_resume.items():
        pdf_path = next(sample_dir.rglob(f"{rid}.pdf"), None)
        if not pdf_path:
            print(f"ERROR: Missing PDF for {rid}")
            sys.exit(1)

        result = parse_resume_pdf(str(pdf_path))
        extracted = result.experiences
        total_extracted_entries += len(extracted)

        # Match each extracted entry to the closest labeled row
        # We track which labeled rows are claimed
        claimed_rows = set()
        matched_in_resume = 0
        wrong_titles_in_resume = 0
        spurious_in_resume = 0

        for exp in extracted:
            exp_text = (exp.title + " " + exp.raw_text + " " + (exp.start_date or "")).lower()
            best_match_idx = None
            best_overlap = 0

            for idx, lrow in enumerate(labeled_rows):
                if idx in claimed_rows:
                    continue
                row_text = (
                    lrow["extracted_title"]
                    + " "
                    + lrow["raw_experience_lines"]
                    + " "
                    + lrow["start_date"]
                ).lower()
                # Simple token overlap
                exp_words = set(exp_text.split())
                row_words = set(row_text.split())
                overlap = len(exp_words.intersection(row_words))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match_idx = idx

            if best_match_idx is not None and best_overlap >= 2:
                claimed_rows.add(best_match_idx)
                matched_row = labeled_rows[best_match_idx]
                lbl = matched_row["label"]
                if lbl in ("O", "C", "W"):
                    matched_real += 1
                    matched_in_resume += 1
                    # Check if title is wrong
                    if lbl == "W" or not exp.title or len(exp.title.split()) > 10:
                        titles_wrong += 1
                        wrong_titles_in_resume += 1
                elif lbl == "F":
                    spurious_extracted += 1
                    spurious_in_resume += 1
                elif lbl == "D":
                    # Parser extracted a duplicate that reviewer labelled D
                    pass
            else:
                # No matching row found in CSV -> spurious or novel
                spurious_extracted += 1
                spurious_in_resume += 1

        # Check real rows not claimed
        real_unclaimed = 0
        for idx, lrow in enumerate(labeled_rows):
            if lrow["label"] in ("O", "C", "W") and idx not in claimed_rows:
                missed_real += 1
                real_unclaimed += 1
            elif lrow["label"] == "D" and idx not in claimed_rows:
                duplicates_dropped += 1

        real_count = sum(1 for r in labeled_rows if r["label"] in ("O", "C", "W"))
        per_resume_report.append(
            {
                "resume_id": rid,
                "real_entries_count": real_count,
                "extracted_count": len(extracted),
                "matched_real": matched_in_resume,
                "missed_real": real_unclaimed,
                "spurious_count": spurious_in_resume,
                "wrong_titles": wrong_titles_in_resume,
            }
        )

    real_accuracy_pct = round((matched_real / total_real) * 100, 2)
    wrong_titles_pct = round((titles_wrong / total_real) * 100, 2)
    spurious_pct = round((spurious_extracted / total_extracted_entries) * 100, 2)

    report = {
        "metadata": {
            **get_provenance("scripts/align_parser_dev2_ground_truth.py", [holdout_csv]),
            "dataset_label": "dev set, tuned on",
            "source_csv": "data/parser_holdout_30_fresh.csv",
            "total_resumes": len(FRESH_LABELS),
            "total_csv_rows": total_rows,
            "reviewer_real_entries": total_real,
            "reviewer_fragments": total_frags,
            "reviewer_duplicates": total_dups,
            "reviewer_unclear": total_unclear,
        },
        "metrics": {
            "total_extracted_entries": total_extracted_entries,
            "matched_real_entries": matched_real,
            "matched_real_percent": real_accuracy_pct,
            "missed_real_entries": missed_real,
            "missed_real_percent": round((missed_real / total_real) * 100, 2),
            "spurious_entries": spurious_extracted,
            "spurious_percent": spurious_pct,
            "titles_wrong": titles_wrong,
            "titles_wrong_percent": wrong_titles_pct,
            "duplicates_dropped": duplicates_dropped,
        },
        "per_resume": per_resume_report,
    }

    out_file = repo_root / "docs" / "eval_parser_dev2_alignment_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n--- DEV SET 2 GROUND-TRUTH ALIGNMENT RESULTS ---")
    print(f"Total Real Entries Labelled: {total_real}")
    print(f"Matched Real Entries:        {matched_real} ({real_accuracy_pct}%)")
    print(
        f"Missed Real Entries:         {missed_real} ({round((missed_real / total_real) * 100, 2)}%)"
    )
    print(f"Spurious Entries Extracted:  {spurious_extracted} ({spurious_pct}%)")
    print(f"Titles Wrong:                {titles_wrong} ({wrong_titles_pct}%)")
    print(f"Duplicates Correctly Dropped:{duplicates_dropped} / {total_dups}")
    print(f"Saved alignment report to:   {out_file}")


if __name__ == "__main__":
    main()
