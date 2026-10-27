#!/usr/bin/env python3
"""
label_pairs.py — Interactive CLI tool for annotating query-chunk evaluation pairs.

Allows recruiters and developers to grow the ground-truth gold set by presenting
a search query alongside candidate resume chunks and recording y/n relevance labels.
"""

import argparse
import json
import random
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


def load_available_chunks(chunks_dir: Path) -> dict[str, list[dict]]:
    """Load pre-parsed candidate chunks from local storage."""
    all_chunks: dict[str, list[dict]] = {}
    chunk_files = list(chunks_dir.glob("*.json"))
    for cf in chunk_files:
        try:
            with open(cf, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    all_chunks[cf.stem] = data
        except Exception:
            continue
    return all_chunks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive CLI tool for annotating query-chunk relevance pairs."
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "docs"
        / "eval_pairs_labeled.json",
        help="Path to JSON file where labeled pairs will be saved.",
    )
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "chunks",
        help="Directory containing pre-chunked resume JSON files.",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run non-interactively for automated test verification.",
    )

    args = parser.parse_args()

    print("=" * 60)
    print(" RECRUIT LENS: EVALUATION PAIR ANNOTATOR (CLI)")
    print("=" * 60)

    if not args.chunks_dir.exists():
        print(f"Error: Chunks directory does not exist at {args.chunks_dir}")
        sys.exit(1)

    candidate_chunks = load_available_chunks(args.chunks_dir)
    if not candidate_chunks:
        print("No chunk files found in data/chunks/.")
        sys.exit(1)

    print(f"Loaded {len(candidate_chunks)} candidate resumes for labeling.")
    print(f"Labels will be saved to: {args.output_file}")

    # Load existing labels if output file exists
    labeled_pairs: list[dict] = []
    if args.output_file.exists():
        try:
            with open(args.output_file, encoding="utf-8") as f:
                labeled_pairs = json.load(f)
            print(f"Found {len(labeled_pairs)} existing labeled pairs.")
        except Exception:
            labeled_pairs = []

    if args.test_mode:
        print("\n[Test Mode] Executing non-interactive verification...")
        sample_pair = {
            "domain": "Test Domain",
            "query": "Sample test query for CLI verification.",
            "relevant_chunk_id": "test_chunk_001",
            "relevance_score": 2,
        }
        labeled_pairs.append(sample_pair)
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(labeled_pairs, f, indent=2)
        print(f"Successfully recorded 1 test pair to {args.output_file}.")
        return

    # Interactive Annotation Loop
    resumes_list = list(candidate_chunks.keys())
    random.shuffle(resumes_list)

    print(
        "\nCommands: [y]es (relevant), [n]o (not relevant), [s]kip, [q]uit and save\n"
    )

    for resume_id in resumes_list:
        chunks = candidate_chunks[resume_id]
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", f"{resume_id}_chunk")
            section = chunk.get("section", "unknown")
            text = chunk.get("text", "").strip()

            print("-" * 60)
            print(f"Resume: {resume_id} | Chunk: {chunk_id} | Section: {section}")
            print(f"Content:\n{text[:300]}...")
            print("-" * 60)

            user_query = input(
                "Enter query statement (or press Enter to skip): "
            ).strip()
            if not user_query:
                continue

            domain = (
                input("Domain category [e.g. Software Engineering]: ").strip()
                or "General"
            )

            ans = input("Is this chunk relevant? [y/n/s/q]: ").strip().lower()
            if ans == "q":
                print("\nSaving annotations and exiting...")
                with open(args.output_file, "w", encoding="utf-8") as f:
                    json.dump(labeled_pairs, f, indent=2)
                print(f"Saved {len(labeled_pairs)} pairs to {args.output_file}.")
                return
            elif ans == "y":
                labeled_pairs.append(
                    {
                        "domain": domain,
                        "query": user_query,
                        "relevant_chunk_id": chunk_id,
                        "relevance_score": 2,
                    }
                )
                print("-> Recorded positive pair.")
                with open(args.output_file, "w", encoding="utf-8") as f:
                    json.dump(labeled_pairs, f, indent=2)
            else:
                print("-> Skipped.")


if __name__ == "__main__":
    main()
