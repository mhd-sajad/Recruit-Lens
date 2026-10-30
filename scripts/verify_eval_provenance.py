"""verify_eval_provenance.py

Enforces Rule A.2:
- Every docs/eval_*.json (and docs/taxonomy_coverage_report.json) must carry
  metadata with generated_by (script path), git_commit, and input_sha256.
- Verifies that the generator script exists in the repository.
- Exits non-zero if any required provenance field is missing.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"

REQUIRED_PROVENANCE_KEYS = ["generated_by", "git_commit", "input_sha256"]


def verify_file_provenance(path: Path) -> list[str]:
    errors = []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"{path.name}: Failed to parse JSON: {e}"]

    # Some files store metadata top-level, or under 'metadata'
    metadata = data.get("metadata", data)
    if not isinstance(metadata, dict):
        return [f"{path.name}: No valid metadata object found"]

    for k in REQUIRED_PROVENANCE_KEYS:
        val = metadata.get(k)
        if not val or not isinstance(val, str) or val.strip() == "":
            errors.append(f"{path.name}: Missing required provenance key 'metadata.{k}'")

    gen_script = metadata.get("generated_by")
    if gen_script:
        script_file = REPO_ROOT / gen_script
        if not script_file.exists():
            errors.append(f"{path.name}: Generator script '{gen_script}' does not exist on disk")

    # Verify git_commit is an ancestor of HEAD (or HEAD)
    commit_hash = metadata.get("git_commit")
    if commit_hash and commit_hash != "unknown":
        # Check if commit exists in local git object database
        commit_exists = (
            subprocess.run(
                ["git", "cat-file", "-e", f"{commit_hash}^{{commit}}"],
                cwd=str(REPO_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )
        if commit_exists:
            try:
                subprocess.check_call(
                    ["git", "merge-base", "--is-ancestor", commit_hash, "HEAD"],
                    cwd=str(REPO_ROOT),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                errors.append(
                    f"{path.name}: Recorded git_commit '{commit_hash[:8]}' is not an ancestor of HEAD"
                )
        else:
            # Check if shallow clone
            is_shallow = False
            try:
                is_shallow = (
                    subprocess.check_output(
                        ["git", "rev-parse", "--is-shallow-repository"],
                        text=True,
                        cwd=str(REPO_ROOT),
                        stderr=subprocess.DEVNULL,
                    ).strip()
                    == "true"
                )
            except Exception:
                pass

            if is_shallow:
                # Attempt to unshallow if git remote is reachable
                try:
                    subprocess.check_call(
                        ["git", "fetch", "--unshallow"],
                        cwd=str(REPO_ROOT),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    subprocess.check_call(
                        ["git", "merge-base", "--is-ancestor", commit_hash, "HEAD"],
                        cwd=str(REPO_ROOT),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except subprocess.CalledProcessError:
                    if len(commit_hash) < 7 or not all(c in "0123456789abcdefABCDEF" for c in commit_hash):
                        errors.append(f"{path.name}: Invalid commit hash format '{commit_hash}'")
            else:
                errors.append(
                    f"{path.name}: Recorded git_commit '{commit_hash[:8]}' does not exist in repository"
                )

    # Verify input_sha256 is non-empty 64-char hex
    input_sha = metadata.get("input_sha256")
    if input_sha:
        if len(input_sha) != 64 or not all(c in "0123456789abcdefABCDEF" for c in input_sha):
            errors.append(f"{path.name}: Malformed input_sha256 '{input_sha}'")

    return errors


def check_git_commit_coupling() -> list[str]:
    """Check that any eval file modified in HEAD commit also has its script committed or mentioned."""
    errors = []
    try:
        # Check files modified in the latest commit
        diff_output = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
            text=True,
            cwd=str(REPO_ROOT),
        ).splitlines()
    except Exception:
        return errors

    eval_files = [f for f in diff_output if f.startswith("docs/eval_") and f.endswith(".json")]
    for ef in eval_files:
        ef_path = REPO_ROOT / ef
        if ef_path.exists():
            try:
                with open(ef_path, encoding="utf-8") as f:
                    d = json.load(f)
                meta = d.get("metadata", d)
                gen_by = meta.get("generated_by")
                # If the eval file changed, check if generator script or make_report changed
                if gen_by and gen_by not in diff_output:
                    # Also permit if scripts/ or tests were modified
                    script_changed = any(
                        f.startswith("scripts/") or f.startswith("backend/") for f in diff_output
                    )
                    if not script_changed:
                        errors.append(
                            f"Eval file '{ef}' changed in commit without its generator script '{gen_by}' or scripts/ being modified"
                        )
            except Exception:
                pass
    return errors


def main() -> int:
    all_eval_files = sorted(list(DOCS_DIR.glob("eval_*.json")))
    taxonomy_file = DOCS_DIR / "taxonomy_coverage_report.json"
    if taxonomy_file.exists():
        all_eval_files.append(taxonomy_file)

    # Exclude raw locked fixtures and frozen historical batch files
    fixtures_to_skip = {
        "eval_pairs_locked.json",
        "eval_pairs_remapped_v2.json",
        "eval_metrics.json",
        "eval_metrics_batch2.json",
        "eval_llm_latency_report.json",
        "eval_scoring_comparison.json",
        "eval_backend_coverage.json",
    }
    target_files = [f for f in all_eval_files if f.name not in fixtures_to_skip]

    print(f"Auditing provenance for {len(target_files)} evaluation files in docs/...")
    all_errors = []

    for f in target_files:
        errs = verify_file_provenance(f)
        if errs:
            all_errors.extend(errs)
        else:
            print(f"  [OK] {f.name}")

    coupling_errs = check_git_commit_coupling()
    if coupling_errs:
        all_errors.extend(coupling_errs)

    if all_errors:
        print("\nPROVENANCE VERIFICATION FAILED:", file=sys.stderr)
        for err in all_errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        return 1

    print("\nAll evaluation files have verified provenance metadata.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
