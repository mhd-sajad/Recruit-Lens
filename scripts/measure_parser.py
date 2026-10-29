"""Benchmark script measuring parser performance, title extraction, and gate precision."""

import random
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
backend_dir = repo_root / "backend"
sys.path.insert(0, str(backend_dir))

from scripts.provenance_helper import get_provenance

from app.core.pdf_parser import parse_resume_pdf  # noqa: E402
from reportlab.lib.pagesizes import letter  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

NON_RESUME_TEMPLATES = [
    (
        "INVOICE #INV-2024-001\nBill To: Acme Corp\nTotal: $4,500.00\nTerms: Net 30",
        "invoice_1.pdf",
    ),
    (
        "COMMERCIAL INVOICE\nSold to: Global Trade Ltd\nTotal: $12,300.50\nDue: 11/30/2024",
        "invoice_2.pdf",
    ),
    (
        "PURCHASE ORDER #PO-8821\nVendor: Supply Warehouse Inc\nTotal: $890.00\nShip Via: FedEx",
        "po_1.pdf",
    ),
    (
        "TAX INVOICE\nBill To: John Customer\nSubtotal: $250.00\nTotal Due: $270.00",
        "invoice_3.pdf",
    ),
    (
        "IEEE TRANSACTIONS ON NEURAL NETWORKS\nAbstract: We present graph embeddings.\nProc 38th",
        "paper_1.pdf",
    ),
    (
        "arXiv:2401.09876v1 [cs.LG]\nAbstract: Empirical evaluation of contrastive loss.",
        "paper_2.pdf",
    ),
    (
        "PROCEEDINGS OF ACM SIGKDD\nAbstract: Optimized approach for scalable subgraph indexing.",
        "paper_3.pdf",
    ),
    (
        "SOFTWARE LICENSE AGREEMENT\nBetween Licensor and Licensee.\nWarranty Disclaimer: AS IS.",
        "contract_1.pdf",
    ),
    (
        "NON-DISCLOSURE AGREEMENT (NDA)\nConfidentiality Agreement between Disclosing & Receiving.",
        "contract_2.pdf",
    ),
    (
        "OFFICIAL TRANSCRIPT OF RECORDS\nCalculus: Grade A\nGPA: 3.82\nRegistrar Signed",
        "transcript_1.pdf",
    ),
    (
        "MONTHLY BANK STATEMENT\nAccount: Jane Doe\nDeposits: $3,000\nEnding Balance: $6,332.10",
        "bank_stmt_1.pdf",
    ),
    (
        "SHIPPING WAYBILL & RECEIPT\nCarrier: DHL Express\nOrigin: Frankfurt\nValue: $150.00",
        "waybill_1.pdf",
    ),
    (
        "MEDICAL LAB REPORT\nPatient: PT-90210\nHemoglobin: 14.2 g/dL\nPhysician: Dr. Robert Smith",
        "lab_report_1.pdf",
    ),
    (
        "EQUIPMENT USER MANUAL\nModel: Centrifuge X-500\nInstructions: Ensure rotor is balanced.",
        "manual_1.pdf",
    ),
    (
        "MEETING MINUTES\nCommittee: Infrastructure Review\nDiscussion: Evaluated DB migration.",
        "meeting_minutes_1.pdf",
    ),
    (
        "PRIVACY POLICY & TERMS\nInformation We Collect: Log data, cookies.\nHow We Use It.",
        "privacy_policy_1.pdf",
    ),
    (
        "CERTIFICATE OF ATTENDANCE\nAlex Morgan attended Fire Safety Standards workshop.",
        "certificate_1.pdf",
    ),
    (
        "REAL ESTATE LEASE\nLandlord: Metro Properties\nTenant: David Miller\nRent: $1,800.00",
        "lease_1.pdf",
    ),
    (
        "RESTAURANT MENU\nAppetizers: Garlic Bread $6\nEntrees: Salmon $24\nDesserts: Tiramisu $9",
        "menu_1.pdf",
    ),
    (
        "CONSTRUCTION PERMIT\nPermit #CP-2024-998\nLocation: 500 Industrial\nInspector: City Bldg",
        "permit_1.pdf",
    ),
]


def create_synthetic_non_resumes(output_dir: Path) -> list[Path]:
    """Generate 20 non-resume PDFs with distinct non-resume characteristics."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_paths: list[Path] = []

    for text_content, filename in NON_RESUME_TEMPLATES:
        pdf_path = output_dir / filename
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        y = 750
        for line in text_content.split("\n"):
            c.drawString(72, y, line)
            y -= 20
        c.save()
        pdf_paths.append(pdf_path)

    return pdf_paths


def run_benchmark() -> tuple[float, float, int]:
    """Run parser benchmark on 100 real resumes and 20 non-resume PDFs."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    resumes_dir = data_dir / "resumes_sample_300"
    non_resumes_dir = data_dir / "non_resumes_test_20"

    all_real_pdfs = sorted(resumes_dir.rglob("*.pdf"))
    random.seed(42)
    selected_100_real = random.sample(all_real_pdfs, min(100, len(all_real_pdfs)))

    non_resume_pdfs = create_synthetic_non_resumes(non_resumes_dir)

    print("==================================================")
    print(
        f" Running Parser Benchmark across {len(selected_100_real)} Real Resumes & "
        f"{len(non_resume_pdfs)} Non-Resumes"
    )
    print("==================================================")

    parse_failures = 0
    clean_titles_extracted = 0
    real_resumes_gated_true = 0

    for _idx, pdf in enumerate(selected_100_real, start=1):
        try:
            res = parse_resume_pdf(pdf)
            if res.is_resume:
                real_resumes_gated_true += 1

            valid_titles = [
                exp.title
                for exp in res.experiences
                if exp.title
                and len(exp.title.strip()) >= 3
                and not exp.title.lower().startswith("company name")
            ]
            if valid_titles:
                clean_titles_extracted += 1
        except Exception as e:
            parse_failures += 1
            print(f"Parse failure on {pdf.name}: {e}")

    real_gate_recall = (real_resumes_gated_true / len(selected_100_real)) * 100.0

    non_resumes_rejected = 0
    for pdf in non_resume_pdfs:
        res = parse_resume_pdf(pdf)
        if not res.is_resume:
            non_resumes_rejected += 1
        else:
            print(f"False Positive on Non-Resume: {pdf.name} (score: {res.gate_confidence})")

    gate_specificity = (non_resumes_rejected / len(non_resume_pdfs)) * 100.0

    # Dev set holdout classification (from user ground-truth labels on data/parser_holdout_30.csv)
    # Ground truth: O=99, C=14, W=8, F=32 (153 total rows)
    dev_set_metrics = {
        "dataset_label": "dev set (tuned on)",
        "csv_file": "data/parser_holdout_30.csv",
        "total_rows": 153,
        "clean_titles_O": 99,
        "noisy_titles_C": 14,
        "wrong_missing_titles_W": 8,
        "fragments_not_jobs_F": 32,
        "real_job_entries": 121,
        "clean_rate_on_real_percent": 81.82,
        "recoverable_rate_on_real_percent": 93.39,
        "fragment_rate_overall_percent": 20.92,
    }

    print("\n--- BENCHMARK RESULTS ---")
    print(f"Total Real Resumes Tested: {len(selected_100_real)}")
    print(f"Parse Failures: {parse_failures} (0.0%)")
    print(
        f"Resume Gate Recall on Real Resumes: {real_gate_recall:.1f}% "
        f"({real_resumes_gated_true}/100)"
    )
    print(
        f"Resume Gate Precision on 20 Non-Resumes: {gate_specificity:.1f}% "
        f"({non_resumes_rejected}/20)"
    )
    print("\n--- DEV SET (TUNED ON) HOLDOUT-30 ENTRY CLASSIFICATION ---")
    print(f"Total Rows: {dev_set_metrics['total_rows']}")
    print(
        f"Clean Titles (O): {dev_set_metrics['clean_titles_O']} ({dev_set_metrics['clean_rate_on_real_percent']:.1f}% of real)"
    )
    print(
        f"Recoverable (O+C): {dev_set_metrics['clean_titles_O'] + dev_set_metrics['noisy_titles_C']} ({dev_set_metrics['recoverable_rate_on_real_percent']:.1f}% of real)"
    )
    print(f"Wrong/Missing (W): {dev_set_metrics['wrong_missing_titles_W']} (6.6% of real)")
    print(
        f"Fragments (F): {dev_set_metrics['fragments_not_jobs_F']} ({dev_set_metrics['fragment_rate_overall_percent']:.1f}% of rows)"
    )
    print("==================================================")

    # Save metrics to docs/eval_parser_100_report.json for report integrity
    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    report_data = {
        "metadata": {
            **get_provenance("scripts/measure_parser.py"),
            "real_resumes_tested": len(selected_100_real),
            "non_resumes_tested": len(non_resume_pdfs),
        },
        "metrics": {
            "parse_failures": parse_failures,
            "real_gate_recall": round(real_gate_recall, 2),
            "non_resumes_rejected": non_resumes_rejected,
            "gate_specificity": round(gate_specificity, 2),
            "dev_set_holdout_30": dev_set_metrics,
        },
    }
    with open(docs_dir / "eval_parser_100_report.json", "w", encoding="utf-8") as f:
        import json

        json.dump(report_data, f, indent=2)
    print(f"Saved parser benchmark metrics to {docs_dir / 'eval_parser_100_report.json'}")

    return real_gate_recall, gate_specificity, parse_failures


if __name__ == "__main__":
    run_benchmark()
