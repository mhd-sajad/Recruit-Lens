"""Generate per-module router coverage report from coverage.json with audit provenance."""

import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from scripts.provenance_helper import get_provenance


def main() -> None:
    coverage_file = repo_root / "docs" / "coverage.json"
    if not coverage_file.exists():
        print(f"Error: {coverage_file} does not exist", file=sys.stderr)
        sys.exit(1)

    with open(coverage_file, encoding="utf-8") as f:
        cov_data = json.load(f)

    files_cov = cov_data.get("files", {})
    router_modules = {}

    for file_path, data in sorted(files_cov.items()):
        if "backend/app/api/v1/" in file_path or "app/api/v1/" in file_path:
            mod_name = Path(file_path).name
            summary = data.get("summary", {})
            router_modules[mod_name] = {
                "num_statements": summary.get("num_statements", 0),
                "covered_lines": summary.get("covered_lines", 0),
                "missing_lines": summary.get("missing_lines", 0),
                "percent_covered": round(summary.get("percent_covered", 0.0), 2),
            }

    prov = get_provenance("scripts/generate_router_coverage_report.py", [coverage_file])
    output = {
        "metadata": prov,
        **router_modules,
    }

    out_file = repo_root / "docs" / "eval_router_modules_coverage.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved router coverage report to {out_file} with {len(router_modules)} modules.")


if __name__ == "__main__":
    main()
