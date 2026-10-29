"""
measure_chunk_cleanliness.py

Verifies that the updated resume_chunker eliminates UTF-8 mojibake and
placeholder redaction headers before windowing.
Outputs docs/eval_chunker_cleanliness.json.
"""

import json
import re
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from scripts.provenance_helper import get_provenance

MOJIBAKE_PAT = re.compile(r"[\xc2\xa0Ââ€\x80-\x9fï]")
PLACEHOLDER_PAT = re.compile(r"(Name\s+City\s*,\s*State|\bPhone\s*:|\bEmail\s*:)", re.IGNORECASE)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    chunks_dir = repo_root / "data" / "chunks_batch1_verified"

    chunk_files = sorted(chunks_dir.glob("*.json"))
    print(f"Auditing {len(chunk_files)} chunk files in {chunks_dir}...")

    total_chunks = 0
    mojibake_chunks = 0
    placeholder_chunks = 0

    mojibake_examples = []
    placeholder_examples = []

    for cf in chunk_files:
        with open(cf, encoding="utf-8") as f:
            chunks = json.load(f)
        for c in chunks:
            total_chunks += 1
            t = c.get("text", "")
            if MOJIBAKE_PAT.search(t):
                mojibake_chunks += 1
                if len(mojibake_examples) < 3:
                    mojibake_examples.append({"chunk_id": c["chunk_id"], "text": t[:100]})
            if PLACEHOLDER_PAT.search(t):
                placeholder_chunks += 1
                if len(placeholder_examples) < 3:
                    placeholder_examples.append({"chunk_id": c["chunk_id"], "text": t[:100]})

    # Historical values before chunker fix
    before_total_chunks = 2318
    before_mojibake_chunks = 994
    before_placeholder_chunks = 147

    target_met = (mojibake_chunks == 0) and (placeholder_chunks == 0)

    report = {
        "metadata": {
            **get_provenance("scripts/measure_chunk_cleanliness.py"),
            "chunks_directory": "data/chunks_batch1_verified",
            "total_resumes_chunked": len(chunk_files),
        },
        "before_cleaning": {
            "total_chunks": before_total_chunks,
            "mojibake_chunks": before_mojibake_chunks,
            "placeholder_chunks": before_placeholder_chunks,
        },
        "after_cleaning": {
            "total_chunks": total_chunks,
            "mojibake_chunks": mojibake_chunks,
            "placeholder_chunks": placeholder_chunks,
        },
        "target_met": target_met,
    }

    out_file = repo_root / "docs" / "eval_chunker_cleanliness.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n--- CHUNKER CLEANLINESS REPORT ---")
    print(f"Total Chunks: {total_chunks}")
    print(f"Before: Mojibake={before_mojibake_chunks}, Placeholders={before_placeholder_chunks}")
    print(f"After:  Mojibake={mojibake_chunks}, Placeholders={placeholder_chunks}")
    print(f"Target Met (0 dirty chunks): {target_met}")
    print(f"Saved to {out_file}")


if __name__ == "__main__":
    main()
