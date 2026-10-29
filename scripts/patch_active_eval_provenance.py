"""Attach standard audit provenance to active evaluation reports where missing."""
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from scripts.provenance_helper import get_provenance


def main() -> None:
    docs_dir = repo_root / "docs"

    # 1. eval_parser_dev30_measurement.json
    pdev_path = docs_dir / "eval_parser_dev30_measurement.json"
    if pdev_path.exists():
        with open(pdev_path, encoding="utf-8") as f:
            data = json.load(f)
        prov = get_provenance("scripts/measure_parser.py", [repo_root / "data" / "parser_holdout_30.csv"])
        data["metadata"]["generated_by"] = prov["generated_by"]
        data["metadata"]["git_commit"] = prov["git_commit"]
        data["metadata"]["input_sha256"] = prov["input_sha256"]
        with open(pdev_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print("Updated provenance for eval_parser_dev30_measurement.json")

    # 2. eval_llm_agents_report.json & eval_llm_agents_batch4.json
    llm_script = repo_root / "scripts" / "evaluate_llm_agents.py"
    prov_llm = get_provenance("scripts/evaluate_llm_agents.py", [llm_script])
    for fname in ["eval_llm_agents_report.json", "eval_llm_agents_batch4.json"]:
        fpath = docs_dir / fname
        if fpath.exists():
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            if "metadata" not in data or not isinstance(data["metadata"], dict):
                data["metadata"] = {}
            data["metadata"]["generated_by"] = prov_llm["generated_by"]
            data["metadata"]["git_commit"] = prov_llm["git_commit"]
            data["metadata"]["input_sha256"] = prov_llm["input_sha256"]
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"Updated provenance for {fname}")

    # 3. eval_model_comparison_report.json & eval_llm_comparison_batch4.json
    model_script = repo_root / "scripts" / "compare_llm_models.py"
    prov_model = get_provenance("scripts/compare_llm_models.py", [model_script])
    for fname in ["eval_model_comparison_report.json", "eval_llm_comparison_batch4.json"]:
        fpath = docs_dir / fname
        if fpath.exists():
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            if "metadata" not in data or not isinstance(data["metadata"], dict):
                data["metadata"] = {}
            data["metadata"]["generated_by"] = prov_model["generated_by"]
            data["metadata"]["git_commit"] = prov_model["git_commit"]
            data["metadata"]["input_sha256"] = prov_model["input_sha256"]
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"Updated provenance for {fname}")


if __name__ == "__main__":
    main()
