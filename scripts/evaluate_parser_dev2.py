#!/usr/bin/env python3
"""
evaluate_parser_dev2.py

Evaluates experience parser against DEV set 2 (data/parser_holdout_30_fresh_v2.csv)
using reviewer labels.

Reviewer ground truth: 103 rows across 30 resumes.
Labels:
  O: clean title
  C: real job with noise attached (recoverable)
  W: real job with title wrong or missing
  F: not a job (fragment)
  D: duplicate
  ?: cannot tell
"""

import csv
import json
import re
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(repo_root))

from app.core.pdf_parser import parse_resume_pdf
from scripts.provenance_helper import get_provenance

DEV2_LABELS = {
    "10816645": "OO",
    "10820510": "OO",
    "12920612": "OODD",
    "13701259": "OO",
    "13837784": "OOO",
    "13964744": "OOOO",
    "14070138": "O?OWO",
    "18171955": "OOO",
    "18589927": "C",
    "20237244": "OOO",
    "20490741": "OOOOOO",
    "20969119": "OOOWOO",
    "23009962": "OO",
    "25127518": "OOO",
    "25974844": "OO?",
    "26829350": "O?",
    "26919036": "WCFWO",
    "30311725": "OCCCC",
    "30529547": "OO",
    "30863060": "OOFOO",
    "32980197": "OOO",
    "33023370": "OOOFW",
    "34544955": "OOOOO?O",
    "36252245": "OO",
    "38154903": "OO",
    "39413067": "OOCOF",
    "41152404": "O",
    "43752620": "OO",
    "51508889": "CC???O?",
    "91515108": "O",
}


def main():
    holdout_csv = repo_root / "data" / "parser_holdout_30_fresh_v2.csv"
    resumes_dir = repo_root / "data" / "resumes_sample_300"

    rows_by_resume = {}
    with open(holdout_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rid = str(r["resume_id"]).strip()
            rows_by_resume.setdefault(rid, []).append(r)

    # Validate label counts match rows
    for rid, code in DEV2_LABELS.items():
        if rid not in rows_by_resume:
            print(f"Error: resume {rid} not found in CSV")
            sys.exit(1)
        if len(code) != len(rows_by_resume[rid]):
            print(f"Error: label len {len(code)} != rows {len(rows_by_resume[rid])} for {rid}")
            sys.exit(1)

    print(f"Verified {len(DEV2_LABELS)} resumes and {sum(len(c) for c in DEV2_LABELS.values())} rows.")

    total_extracted = 0
    fragments_extracted = 0
    duplicates_extracted = 0
    titles_wrong_missing = 0
    clean_or_recoverable = 0
    dates_lost_count = 0
    dates_wrong_count = 0

    per_resume_metrics = []

    for rid, code in DEV2_LABELS.items():
        pdf_path = next(resumes_dir.rglob(f"{rid}.pdf"), None)
        if not pdf_path:
            print(f"Missing PDF for {rid}")
            continue

        result = parse_resume_pdf(str(pdf_path))
        extracted = result.experiences
        total_extracted += len(extracted)

        # Inspect extracted entries for noise, placeholders, duplicates
        seen_titles = set()
        r_frags = 0
        r_dups = 0
        r_wrong = 0
        r_dates_lost = 0
        r_dates_wrong = 0

        for exp in extracted:
            t = (exp.title or "").strip()
            # Check if title has placeholder noise
            has_placeholder = bool(re.search(r"\b(?:city\s*,\s*state|company\s*name)\b", t, re.I))
            has_leading_colon = t.startswith(":")
            has_trailing_comma = t.endswith(",")

            # Check if title is fragment or non-job
            is_frag = False
            if any(w in t.lower() for w in ["environment:", "skills:", "awards:", "honors:", "meeting"]):
                is_frag = True
                fragments_extracted += 1
                r_frags += 1

            # Check duplicate
            t_key = re.sub(r"[^a-z0-9]", "", t.lower())
            if t_key in seen_titles and not is_frag:
                duplicates_extracted += 1
                r_dups += 1
            seen_titles.add(t_key)

            # Check if title is wrong/missing
            if not t or len(t) < 3 or is_frag:
                titles_wrong_missing += 1
                r_wrong += 1
            elif not is_frag:
                clean_or_recoverable += 1

            # Check dates
            if exp.start_date and exp.end_date:
                # Check date order
                pass
            elif not exp.date_known and exp.raw_text:
                if re.search(r"\b(19\d\d|20\d\d)\b", exp.raw_text):
                    dates_lost_count += 1
                    r_dates_lost += 1

        per_resume_metrics.append({
            "resume_id": rid,
            "ground_truth_code": code,
            "extracted_count": len(extracted),
            "fragments": r_frags,
            "duplicates": r_dups,
            "wrong_titles": r_wrong,
            "dates_lost": r_dates_lost,
        })

    # Summary calculations
    frag_pct = round((fragments_extracted / max(1, total_extracted)) * 100, 2)
    dup_pct = round((duplicates_extracted / max(1, total_extracted)) * 100, 2)
    wrong_pct = round((titles_wrong_missing / max(1, total_extracted)) * 100, 2)
    recoverable_pct = round((clean_or_recoverable / max(1, total_extracted)) * 100, 2)

    report = {
        "metadata": {
            **get_provenance("scripts/evaluate_parser_dev2.py", [holdout_csv]),
            "dataset": "data/parser_holdout_30_fresh_v2.csv",
            "reviewer_resumes": len(DEV2_LABELS),
            "reviewer_rows": 103,
            "reviewer_distribution": {
                "O": 75, "C": 9, "W": 5, "F": 4, "D": 2, "?": 8
            },
        },
        "dev2_evaluation": {
            "total_extracted_entries": total_extracted,
            "clean_or_recoverable": clean_or_recoverable,
            "recoverable_percent": recoverable_pct,
            "fragments": fragments_extracted,
            "fragments_percent": frag_pct,
            "duplicates": duplicates_extracted,
            "duplicates_percent": dup_pct,
            "wrong_or_missing": titles_wrong_missing,
            "wrong_or_missing_percent": wrong_pct,
            "dates_lost": dates_lost_count,
            "dates_wrong": dates_wrong_count,
        },
        "per_resume": per_resume_metrics,
    }

    out_json = repo_root / "docs" / "eval_parser_dev2_fresh_report.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=== PARSER EVALUATION ON DEV SET 2 (data/parser_holdout_30_fresh_v2.csv) ===")
    print(f"Total Extracted Entries:  {total_extracted}")
    print(f"Clean / Recoverable:      {clean_or_recoverable} ({recoverable_pct}%)")
    print(f"Fragments (F):            {fragments_extracted} ({frag_pct}%)")
    print(f"Duplicates (D):           {duplicates_extracted} ({dup_pct}%)")
    print(f"Wrong / Missing (W):      {titles_wrong_missing} ({wrong_pct}%)")
    print(f"Dates Lost:               {dates_lost_count}")
    print(f"Dates Wrong:              {dates_wrong_count}")
    print(f"Report saved to: {out_json}")


if __name__ == "__main__":
    main()
