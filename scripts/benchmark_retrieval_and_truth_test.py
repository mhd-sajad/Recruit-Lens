"""
benchmark_retrieval_and_truth_test.py

Executes:
1. Embeddings Benchmark: MiniLM-L6 vs BGE-small (quantized ONNX) on RSS, latency, metrics.
2. Truth Test on 34 Gold Pairs: BM25 vs Dense vs Hybrid.
3. Hit@1, Hit@3, Hit@5, Hit@10, MRR, per-category breakdown, and Bootstrap 95% CI.
4. Up to 3 cheap improvements (RRF k, section boosts, dense weighting).
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Literal

import numpy as np

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.embeddings import ONNXEmbedder  # noqa: E402
from app.core.models import ResumeChunk  # noqa: E402
from app.core.retrieval import CandidateIsolatedIndex  # noqa: E402


def get_current_rss_mb() -> float:
    """Read instantaneous VmRSS in MB from /proc/self/status on Linux."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    return float(parts[1]) / 1024.0
    except Exception:
        pass
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def bootstrap_ci(
    data: list[float], n_resamples: int = 2000, alpha: float = 0.05
) -> tuple[float, float]:
    """Compute bootstrap percentile confidence interval for the mean."""
    if not data:
        return 0.0, 0.0
    rng = np.random.default_rng(42)
    sample_means = []
    n = len(data)
    for _ in range(n_resamples):
        resample = rng.choice(data, size=n, replace=True)
        sample_means.append(float(np.mean(resample)))
    lower = float(np.percentile(sample_means, 100 * (alpha / 2)))
    upper = float(np.percentile(sample_means, 100 * (1 - alpha / 2)))
    return lower, upper


def load_gold_pairs() -> list[dict[str, Any]]:
    eval_file = Path(__file__).resolve().parent.parent / "docs" / "eval_pairs_locked.json"
    with open(eval_file, encoding="utf-8") as f:
        return json.load(f)


def load_candidate_chunks(
    gold_pairs: list[dict[str, Any]],
) -> dict[str, list[ResumeChunk]]:
    chunks_dir = Path(__file__).resolve().parent.parent / "data" / "chunks"
    candidate_chunks: dict[str, list[ResumeChunk]] = {}

    for pair in gold_pairs:
        cid = pair["relevant_chunk_id"]
        rid = cid.split("_")[0]
        if rid in candidate_chunks:
            continue

        chunk_file = chunks_dir / f"{rid}.json"
        if not chunk_file.exists():
            print(f"Warning: Chunk file not found: {chunk_file}")
            continue

        with open(chunk_file, encoding="utf-8") as f:
            raw_chunks = json.load(f)

        chunk_list = []
        for c in raw_chunks:
            chunk_list.append(
                ResumeChunk(
                    chunk_id=c["chunk_id"],
                    resume_id=c["resume_id"],
                    section=c.get("section", "general"),
                    text=c["text"],
                    metadata=c.get("metadata", {}),
                )
            )
        candidate_chunks[rid] = chunk_list

    return candidate_chunks


def evaluate_engine(
    embedder: ONNXEmbedder,
    gold_pairs: list[dict[str, Any]],
    candidate_chunks: dict[str, list[ResumeChunk]],
    mode: Literal["bm25", "dense", "hybrid"] = "hybrid",
    rrf_k: int = 60,
    dense_weight: float = 1.0,
    bm25_weight: float = 1.0,
    section_boosts: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Evaluate retrieval performance across gold pairs."""
    # Pre-build candidate indices
    indices: dict[str, CandidateIsolatedIndex] = {}
    for rid, chunks in candidate_chunks.items():
        indices[rid] = CandidateIsolatedIndex(rid, chunks, embedder=embedder)

    hit1_list: list[float] = []
    hit3_list: list[float] = []
    hit5_list: list[float] = []
    hit10_list: list[float] = []
    mrr_list: list[float] = []
    per_category: dict[str, dict[str, list[float]]] = {}

    for pair in gold_pairs:
        query = pair["query"]
        target_chunk_id = pair["relevant_chunk_id"]
        category = pair.get("domain", "General")
        rid = target_chunk_id.split("_")[0]

        if category not in per_category:
            per_category[category] = {"hit5": [], "mrr": []}

        if rid not in indices:
            hit1_list.append(0.0)
            hit3_list.append(0.0)
            hit5_list.append(0.0)
            hit10_list.append(0.0)
            mrr_list.append(0.0)
            per_category[category]["hit5"].append(0.0)
            per_category[category]["mrr"].append(0.0)
            continue

        index = indices[rid]
        results = index.search(
            query=query,
            top_k=10,
            mode=mode,
            rrf_k=rrf_k,
            dense_weight=dense_weight,
            bm25_weight=bm25_weight,
            section_boosts=section_boosts,
        )

        target_rank = None
        for rank_0, hit in enumerate(results):
            if hit.chunk_id == target_chunk_id:
                target_rank = rank_0 + 1
                break

        h1 = 1.0 if target_rank == 1 else 0.0
        h3 = 1.0 if (target_rank and target_rank <= 3) else 0.0
        h5 = 1.0 if (target_rank and target_rank <= 5) else 0.0
        h10 = 1.0 if (target_rank and target_rank <= 10) else 0.0
        mrr = 1.0 / target_rank if target_rank else 0.0

        hit1_list.append(h1)
        hit3_list.append(h3)
        hit5_list.append(h5)
        hit10_list.append(h10)
        mrr_list.append(mrr)
        per_category[category]["hit5"].append(h5)
        per_category[category]["mrr"].append(mrr)

    return {
        "hit1": float(np.mean(hit1_list)),
        "hit3": float(np.mean(hit3_list)),
        "hit5": float(np.mean(hit5_list)),
        "hit10": float(np.mean(hit10_list)),
        "mrr": float(np.mean(mrr_list)),
        "hit5_list": hit5_list,
        "mrr_list": mrr_list,
        "per_category": {
            cat: {
                "hit5": float(np.mean(v["hit5"])),
                "mrr": float(np.mean(v["mrr"])),
                "count": len(v["hit5"]),
            }
            for cat, v in per_category.items()
        },
    }


def run_benchmarks() -> None:
    print("=" * 70)
    print(" RECRUIT LENS: BATCH 1 EMBEDDINGS & RETRIEVAL TRUTH TEST")
    print("=" * 70)

    gold_pairs = load_gold_pairs()
    print(f"Loaded {len(gold_pairs)} locked evaluation pairs.")

    candidate_chunks = load_candidate_chunks(gold_pairs)
    total_chunks = sum(len(c) for c in candidate_chunks.values())
    print(f"Loaded {total_chunks} chunks across {len(candidate_chunks)} evaluation resumes.")

    all_chunk_texts = [c.text for chunks in candidate_chunks.values() for c in chunks][:100]

    # ---------------------------------------------------------
    # PART 1: Model Benchmark (MiniLM-L6 vs BGE-small)
    # ---------------------------------------------------------
    print("\n[PART 1] BENCHMARKING EMBEDDERS (MiniLM-L6 vs BGE-Small ONNX Quantized)")
    print("-" * 70)

    base_rss = get_current_rss_mb()
    print(f"Baseline Process RSS: {base_rss:.1f} MB")

    # Benchmark MiniLM-L6
    print("\nEvaluating MiniLM-L6 (quantized ONNX)...")
    t0 = time.time()
    minilm = ONNXEmbedder("minilm", quantized=True)
    minilm_load_time = time.time() - t0
    minilm_rss = get_current_rss_mb()

    # Latency measurement on 100 chunks
    t0 = time.time()
    _ = minilm.embed_texts(all_chunk_texts, batch_size=32)
    minilm_total_time = time.time() - t0
    minilm_latency_per_chunk_ms = (minilm_total_time / len(all_chunk_texts)) * 1000.0

    minilm_dense_res = evaluate_engine(minilm, gold_pairs, candidate_chunks, mode="dense")
    minilm_hybrid_res = evaluate_engine(minilm, gold_pairs, candidate_chunks, mode="hybrid")

    print(f"  MiniLM Load Time: {minilm_load_time:.2f}s")
    print(f"  MiniLM Post-load RSS: {minilm_rss:.1f} MB (Delta: +{minilm_rss - base_rss:.1f} MB)")
    print(f"  MiniLM Latency / Chunk: {minilm_latency_per_chunk_ms:.2f} ms")
    h5_m = minilm_dense_res["hit5"] * 100
    mrr_m = minilm_dense_res["mrr"]
    print(f"  MiniLM Dense:  Hit@5={h5_m:.1f}%, MRR={mrr_m:.4f}")
    h5_hy = minilm_hybrid_res["hit5"] * 100
    mrr_hy = minilm_hybrid_res["mrr"]
    print(f"  MiniLM Hybrid: Hit@5={h5_hy:.1f}%, MRR={mrr_hy:.4f}")

    # Benchmark BGE-small
    print("\nEvaluating BGE-small (quantized ONNX)...")
    t0 = time.time()
    bge = ONNXEmbedder("bge-small", quantized=True)
    bge_load_time = time.time() - t0
    bge_rss = get_current_rss_mb()

    t0 = time.time()
    _ = bge.embed_texts(all_chunk_texts, batch_size=32)
    bge_total_time = time.time() - t0
    bge_latency_per_chunk_ms = (bge_total_time / len(all_chunk_texts)) * 1000.0

    bge_dense_res = evaluate_engine(bge, gold_pairs, candidate_chunks, mode="dense")
    bge_hybrid_res = evaluate_engine(bge, gold_pairs, candidate_chunks, mode="hybrid")

    print(f"  BGE-small Load Time: {bge_load_time:.2f}s")
    print(f"  BGE-small Post-load RSS: {bge_rss:.1f} MB (Delta: +{bge_rss - base_rss:.1f} MB)")
    print(f"  BGE-small Latency / Chunk: {bge_latency_per_chunk_ms:.2f} ms")
    h5_b = bge_dense_res["hit5"] * 100
    mrr_b = bge_dense_res["mrr"]
    print(f"  BGE-small Dense:  Hit@5={h5_b:.1f}%, MRR={mrr_b:.4f}")
    h5_bhy = bge_hybrid_res["hit5"] * 100
    mrr_bhy = bge_hybrid_res["mrr"]
    print(f"  BGE-small Hybrid: Hit@5={h5_bhy:.1f}%, MRR={mrr_bhy:.4f}")

    # Winner Selection Rule: Best MRR and Hit@5 subject to RSS <= 350 MB
    print("\n--- MODEL SELECTION DECISION ---")
    print(
        f"MiniLM: RSS={minilm_rss:.1f} MB (<=350 MB: {minilm_rss <= 350}), "
        f"Hybrid Hit@5={minilm_hybrid_res['hit5'] * 100:.1f}%, MRR={minilm_hybrid_res['mrr']:.4f}"
    )
    print(
        f"BGE:    RSS={bge_rss:.1f} MB (<=350 MB: {bge_rss <= 350}), "
        f"Hybrid Hit@5={bge_hybrid_res['hit5'] * 100:.1f}%, MRR={bge_hybrid_res['mrr']:.4f}"
    )

    if bge_hybrid_res["mrr"] > minilm_hybrid_res["mrr"] and bge_rss <= 350:
        winning_embedder = bge
        winner_name = "BGE-small (quantized ONNX)"
    else:
        winning_embedder = minilm
        winner_name = "MiniLM-L6 (quantized ONNX)"

    print(f"-> Winner Selected: {winner_name}")

    # ---------------------------------------------------------
    # PART 2: Full Truth Test on 34 Gold Pairs
    # ---------------------------------------------------------
    print("\n[PART 2] TRUTH TEST ON 34 GOLD PAIRS (BM25 vs Dense vs Hybrid)")
    print("-" * 70)

    bm25_res = evaluate_engine(winning_embedder, gold_pairs, candidate_chunks, mode="bm25")
    dense_res = evaluate_engine(winning_embedder, gold_pairs, candidate_chunks, mode="dense")
    hybrid_res = evaluate_engine(winning_embedder, gold_pairs, candidate_chunks, mode="hybrid")

    # Bootstrap 95% Confidence Intervals
    bm25_h5_ci = bootstrap_ci(bm25_res["hit5_list"])
    bm25_mrr_ci = bootstrap_ci(bm25_res["mrr_list"])

    dense_h5_ci = bootstrap_ci(dense_res["hit5_list"])
    dense_mrr_ci = bootstrap_ci(dense_res["mrr_list"])

    hybrid_h5_ci = bootstrap_ci(hybrid_res["hit5_list"])
    hybrid_mrr_ci = bootstrap_ci(hybrid_res["mrr_list"])

    print("\n| Metric      | BM25 (Sparse)      | Dense (Embedder)   | Hybrid (RRF k=60)  |")
    print("|:------------|:-------------------|:-------------------|:-------------------|")
    row_h1 = (
        f"| Hit@1       | {bm25_res['hit1'] * 100:6.1f}%            | "
        f"{dense_res['hit1'] * 100:6.1f}%            | "
        f"{hybrid_res['hit1'] * 100:6.1f}%            |"
    )
    print(row_h1)
    row_h3 = (
        f"| Hit@3       | {bm25_res['hit3'] * 100:6.1f}%            | "
        f"{dense_res['hit3'] * 100:6.1f}%            | "
        f"{hybrid_res['hit3'] * 100:6.1f}%            |"
    )
    print(row_h3)
    row_h5 = (
        f"| Hit@5       | {bm25_res['hit5'] * 100:6.1f}%            | "
        f"{dense_res['hit5'] * 100:6.1f}%            | "
        f"{hybrid_res['hit5'] * 100:6.1f}%            |"
    )
    print(row_h5)
    row_h10 = (
        f"| Hit@10      | {bm25_res['hit10'] * 100:6.1f}%            | "
        f"{dense_res['hit10'] * 100:6.1f}%            | "
        f"{hybrid_res['hit10'] * 100:6.1f}%            |"
    )
    print(row_h10)
    row_mrr = (
        f"| MRR         | {bm25_res['mrr']:6.4f}             | "
        f"{dense_res['mrr']:6.4f}             | {hybrid_res['mrr']:6.4f}             |"
    )
    print(row_mrr)
    b_h5_str = f"[{bm25_h5_ci[0] * 100:.1f}%, {bm25_h5_ci[1] * 100:.1f}%]"
    d_h5_str = f"[{dense_h5_ci[0] * 100:.1f}%, {dense_h5_ci[1] * 100:.1f}%]"
    h_h5_str = f"[{hybrid_h5_ci[0] * 100:.1f}%, {hybrid_h5_ci[1] * 100:.1f}%]"
    print(f"| Hit@5 95%CI | {b_h5_str:<18} | {d_h5_str:<18} | {h_h5_str:<18} |")

    b_mrr_str = f"[{bm25_mrr_ci[0]:.4f}, {bm25_mrr_ci[1]:.4f}]"
    d_mrr_str = f"[{dense_mrr_ci[0]:.4f}, {dense_mrr_ci[1]:.4f}]"
    h_mrr_str = f"[{hybrid_mrr_ci[0]:.4f}, {hybrid_mrr_ci[1]:.4f}]"
    print(f"| MRR 95% CI  | {b_mrr_str:<18} | {d_mrr_str:<18} | {h_mrr_str:<18} |")

    print("\n* Note: N=34 is small. Wide confidence intervals reflect sample size variance.")

    # Category breakdown for Hybrid
    print("\n--- PER-CATEGORY BREAKDOWN (Hybrid Engine) ---")
    print("| Domain / Category     | Count | Hit@5 (%) | MRR    |")
    print("|:----------------------|:------|:----------|:-------|")
    for cat, stats in sorted(hybrid_res["per_category"].items()):
        print(
            f"| {cat:<22} | {stats['count']:<5} | "
            f"{stats['hit5'] * 100:6.1f}%   | {stats['mrr']:.4f} |"
        )

    # ---------------------------------------------------------
    # PART 3: Cheap Improvements Evaluation (at most 3)
    # ---------------------------------------------------------
    print("\n[PART 3] TESTING CHEAP IMPROVEMENTS (Keep only if BOTH Hit@5 and MRR improve)")
    print("-" * 70)

    baseline_h5 = hybrid_res["hit5"]
    baseline_mrr = hybrid_res["mrr"]

    # Improvement 1: RRF k parameter tuning (k=20 vs k=60)
    imp1_res = evaluate_engine(
        winning_embedder, gold_pairs, candidate_chunks, mode="hybrid", rrf_k=20
    )
    imp1_kept = (imp1_res["hit5"] > baseline_h5) and (imp1_res["mrr"] > baseline_mrr)
    print(
        f"1. RRF k=20: Hit@5={imp1_res['hit5'] * 100:.1f}% (vs {baseline_h5 * 100:.1f}%), "
        f"MRR={imp1_res['mrr']:.4f} (vs {baseline_mrr:.4f}) -> Kept: {imp1_kept}"
    )

    # Improvement 2: Section boosts (boost summary by 20%, experience by 10%, skills by 20%)
    sec_boosts = {"summary": 0.20, "experience": 0.10, "skills": 0.20}
    imp2_res = evaluate_engine(
        winning_embedder,
        gold_pairs,
        candidate_chunks,
        mode="hybrid",
        section_boosts=sec_boosts,
    )
    imp2_kept = (imp2_res["hit5"] > baseline_h5) and (imp2_res["mrr"] > baseline_mrr)
    print(
        f"2. Section boosts: Hit@5={imp2_res['hit5'] * 100:.1f}% (vs {baseline_h5 * 100:.1f}%), "
        f"MRR={imp2_res['mrr']:.4f} (vs {baseline_mrr:.4f}) -> Kept: {imp2_kept}"
    )

    # Improvement 3: Dense weight emphasis (dense_weight=1.5, bm25_weight=1.0)
    imp3_res = evaluate_engine(
        winning_embedder,
        gold_pairs,
        candidate_chunks,
        mode="hybrid",
        dense_weight=1.5,
        bm25_weight=1.0,
    )
    imp3_kept = (imp3_res["hit5"] > baseline_h5) and (imp3_res["mrr"] > baseline_mrr)
    print(
        f"3. Dense weight: Hit@5={imp3_res['hit5'] * 100:.1f}% (vs {baseline_h5 * 100:.1f}%), "
        f"MRR={imp3_res['mrr']:.4f} (vs {baseline_mrr:.4f}) -> Kept: {imp3_kept}"
    )

    print("\n--- HYBRID VS BM25 VERDICT ---")
    if hybrid_res["mrr"] >= bm25_res["mrr"]:
        print("Verdict: Hybrid matches or outperforms BM25. Hybrid serves as primary engine.")
    else:
        print("Verdict: BM25 outperforms Hybrid. BM25 will serve as primary signal.")

    print("=" * 70)


if __name__ == "__main__":
    run_benchmarks()
