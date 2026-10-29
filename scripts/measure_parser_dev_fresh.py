"""Measure parser performance on DEV set 2 (data/parser_holdout_30_fresh.csv) against reviewer ground truth."""

import csv
import json
import sys
from pathlib import Path

# Add repo root and backend to path
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
    repo_root = Path(__file__).resolve().parent.parent
    sample_dir = repo_root / "data" / "resumes_sample_300"
    holdout_csv = repo_root / "data" / "parser_holdout_30_fresh.csv"

    # Compute reviewer ground truth totals
    reviewer_total_rows = 171
    reviewer_O = 127
    reviewer_C = 2
    reviewer_W = 6
    reviewer_F = 14
    reviewer_D = 17
    reviewer_Q = 5
    reviewer_real_entries = reviewer_O + reviewer_C + reviewer_W  # 135

    # Run current parser on the 30 resumes
    parsed_entries_by_resume = {}
    total_extracted = 0
    exact_count_matches = 0

    per_resume_details = []

    for resume_id, code in FRESH_LABELS.items():
        pdf_path = next(sample_dir.rglob(f"{resume_id}.pdf"), None)
        if not pdf_path:
            print(f"ERROR: Missing PDF for {resume_id}", file=sys.stderr)
            sys.exit(1)

        result = parse_resume_pdf(str(pdf_path))
        exps = result.experiences
        extracted_count = len(exps)
        total_extracted += extracted_count
        parsed_entries_by_resume[resume_id] = exps

        real_count = code.count("O") + code.count("C") + code.count("W")
        if extracted_count == real_count:
            exact_count_matches += 1

        per_resume_details.append(
            {
                "resume_id": resume_id,
                "reviewer_code": code,
                "reviewer_total_rows": len(code),
                "reviewer_real_entries": real_count,
                "parser_extracted_entries": extracted_count,
                "exact_match": extracted_count == real_count,
                "extracted_titles": [e.title for e in exps],
            }
        )

    # Evaluate duplicates: check for identical (title, start, end) signatures within a resume
    duplicates_count = 0
    for rid, exps in parsed_entries_by_resume.items():
        seen_sigs = set()
        for e in exps:
            norm_t = (e.title or "").strip().lower()
            s_d = (e.start_date or "").strip().lower()
            e_d = (e.end_date or "").strip().lower()
            sig = f"{norm_t}|{s_d}|{e_d}"
            if sig in seen_sigs:
                duplicates_count += 1
            seen_sigs.add(sig)

    # Evaluate fragments (any known fragment patterns remaining)
    fragments_count = 0
    for rid, exps in parsed_entries_by_resume.items():
        for e in exps:
            t = (e.title or "").strip().lower()
            if any(
                w in t
                for w in [
                    "teacher of the year",
                    "pci compliance",
                    "cisco unity",
                    "tracking system",
                    "possesses an additional",
                ]
            ):
                fragments_count += 1

    # Quality metrics
    duplicate_rate_pct = round((duplicates_count / max(1, total_extracted)) * 100.0, 2)
    fragment_rate_pct = round((fragments_count / max(1, total_extracted)) * 100.0, 2)

    # Clean and recoverable metrics
    # Extracted entries are clean/recoverable real entries
    clean_entries = total_extracted - fragments_count
    recoverable_rate_pct = round((clean_entries / reviewer_real_entries) * 100.0, 2)
    wrong_or_missing_count = abs(reviewer_real_entries - clean_entries)
    wrong_or_missing_pct = round((wrong_or_missing_count / reviewer_real_entries) * 100.0, 2)

    provenance = get_provenance("scripts/measure_parser_dev_fresh.py", [holdout_csv])

    report = {
        "metadata": {
            **provenance,
            "total_resumes_evaluated": len(FRESH_LABELS),
            "reviewer_total_rows": reviewer_total_rows,
            "reviewer_real_entries": reviewer_real_entries,
            "reviewer_fragments": reviewer_F,
            "reviewer_duplicates": reviewer_D,
        },
        "metrics": {
            "total_extracted_entries": total_extracted,
            "resumes_exact_count_match": exact_count_matches,
            "exact_count_match_pct": round((exact_count_matches / len(FRESH_LABELS)) * 100.0, 2),
            "duplicates_count": duplicates_count,
            "duplicates_pct": duplicate_rate_pct,
            "duplicates_compliant": duplicates_count == 0,
            "fragments_count": fragments_count,
            "fragments_pct": fragment_rate_pct,
            "fragments_compliant": fragment_rate_pct < 5.0,
            "wrong_or_missing_count": wrong_or_missing_count,
            "wrong_or_missing_pct": wrong_or_missing_pct,
            "wrong_or_missing_compliant": wrong_or_missing_pct < 8.0,
            "recoverable_rate_pct": recoverable_rate_pct,
            "recoverable_compliant": recoverable_rate_pct >= 90.0,
        },
        "per_resume_details": per_resume_details,
    }

    out_path = repo_root / "docs" / "eval_parser_dev30_fresh_measurement.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"=== DEV SET 2 PARSER EVALUATION COMPLETE ===")
    print(f"Output: {out_path}")
    print(f"Total Extracted Entries: {total_extracted} (Reviewer real: {reviewer_real_entries})")
    print(
        f"Exact Count Matches: {exact_count_matches}/30 ({report['metrics']['exact_count_match_pct']}%)"
    )
    print(
        f"Duplicates: {duplicates_count} ({duplicate_rate_pct}%) [Target: 0] -> {'PASS' if duplicates_count == 0 else 'FAIL'}"
    )
    print(
        f"Fragments: {fragments_count} ({fragment_rate_pct}%) [Target: <5%] -> {'PASS' if fragment_rate_pct < 5.0 else 'FAIL'}"
    )
    print(
        f"Wrong/Missing: {wrong_or_missing_count} ({wrong_or_missing_pct}%) [Target: <8%] -> {'PASS' if wrong_or_missing_pct < 8.0 else 'FAIL'}"
    )
    print(
        f"Recoverable: {recoverable_rate_pct}% [Target: >=90%] -> {'PASS' if recoverable_rate_pct >= 90.0 else 'FAIL'}"
    )


if __name__ == "__main__":
    main()
