"""Helper to attach standard audit provenance metadata to evaluation reports."""

import hashlib
import subprocess
from pathlib import Path


def get_provenance(script_name: str, input_files: list[str | Path] | None = None) -> dict[str, str]:
    """Return standard provenance dict with generated_by, git_commit, and input_sha256."""
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"

    hasher = hashlib.sha256()
    if input_files:
        for p in input_files:
            path = Path(p)
            if path.exists():
                hasher.update(path.read_bytes())
    else:
        script_path = Path(script_name)
        if script_path.exists():
            hasher.update(script_path.read_bytes())

    return {
        "generated_by": script_name,
        "git_commit": commit,
        "input_sha256": hasher.hexdigest(),
    }
