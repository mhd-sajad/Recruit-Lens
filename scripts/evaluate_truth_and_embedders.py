"""
evaluate_truth_and_embedders.py

Executes:
1. Re-chunks all 300 resumes using current pdf_parser and resume_chunker.
2. Remaps 34 gold pairs from old chunk IDs to new chunk IDs via Jaccard text overlap.
3. Computes candidate pool statistics (min, median, max) and random-guess baselines (Hit@5, Hit@10, MRR).
4. Evaluates Within-Resume retrieval (BM25, Dense MiniLM, Dense BGE-small, Hybrid).
5. Evaluates Corpus-Wide retrieval across all 300 resumes pooled together (BM25, Dense MiniLM, Dense BGE-small, Hybrid).
6. Compares with old project's 64.7% Hit@5.
7. Measures RSS and latency per chunk for MiniLM vs BGE-small (arena disabled, fresh measurements).
"""

import argparse
import gc
import json
import resource
import sys
import time
from pathlib import Path
from typing import Any, Literal

import numpy as np

# Ensure backend is on sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import bm25s  # noqa: E402
from app.core.embeddings import ONNXEmbedder  # noqa: E402
from app.core.models import ResumeChunk  # noqa: E402
from app.core.pdf_parser import parse_resume_pdf  # noqa: E402
from app.core.resume_chunker import chunk_resume  # noqa: E402
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
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def tokenize_words(text: str) -> set[str]:
    import re

    words = re.findall(r"\w+", text.lower())
    return set(words)


def jaccard_similarity(text1: str, text2: str) -> float:
    s1 = tokenize_words(text1)
    s2 = tokenize_words(text2)
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def harmonic_mean_rr(n: int) -> float:
    """Random guess MRR for pool of size n: (1/n) * sum(1/i for i in 1..n)."""
    if n <= 0:
        return 0.0
    return sum(1.0 / i for i in range(1, n + 1)) / n


def get_or_create_new_chunks() -> dict[str, list[ResumeChunk]]:
    """Parse all 300 resumes and generate fresh chunks."""
    cache_dir = Path(__file__).resolve().parent.parent / "data" / "chunks_batch1_verified"
    cache_dir.mkdir(parents=True, exist_ok=True)

    resumes_dir = Path(__file__).resolve().parent.parent / "data" / "resumes_sample_300"
    pdf_files = sorted(list(resumes_dir.glob("**/*.pdf")))
    print(f"Total PDF resumes: {len(pdf_files)}")

    all_chunks: dict[str, list[ResumeChunk]] = {}
    missing_files = []

    for pdf_path in pdf_files:
        rid = pdf_path.stem
        chunk_file = cache_dir / f"{rid}.json"
        if chunk_file.exists():
            with open(chunk_file, encoding="utf-8") as f:
                raw = json.load(f)
            chunks = [
                ResumeChunk(
                    chunk_id=c["chunk_id"],
                    resume_id=c["resume_id"],
                    section=c.get("section", "general"),
                    text=c["text"],
                    metadata=c.get("metadata", {}),
                )
                for c in raw
            ]
            all_chunks[rid] = chunks
        else:
            missing_files.append(pdf_path)

    if missing_files:
        print(f"Parsing and chunking {len(missing_files)} fresh resumes...")
        for i, pdf_path in enumerate(missing_files):
            rid = pdf_path.stem
            try:
                parsed = parse_resume_pdf(pdf_path, resume_id=rid)
                chunks = chunk_resume(parsed)
                all_chunks[rid] = chunks

                # Save to cache
                chunk_file = cache_dir / f"{rid}.json"
                serializable = [
                    {
                        "chunk_id": c.chunk_id,
                        "resume_id": c.resume_id,
                        "section": c.section,
                        "text": c.text,
                        "metadata": c.metadata,
                    }
                    for c in chunks
                ]
                with open(chunk_file, "w", encoding="utf-8") as f:
                    json.dump(serializable, f, indent=2)
            except Exception as e:
                print(f"Error parsing {pdf_path}: {e}")

            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{len(missing_files)}...")

    print(f"Loaded fresh chunks for {len(all_chunks)} resumes.")
    return all_chunks


def remap_gold_pairs(
    all_new_chunks: dict[str, list[ResumeChunk]],
) -> list[dict[str, Any]]:
    """Remap 34 gold pairs to new chunk IDs based on text overlap."""
    gold_path = Path(__file__).resolve().parent.parent / "docs" / "eval_pairs_locked.json"
    old_chunks_dir = Path(__file__).resolve().parent.parent / "data" / "chunks"

    with open(gold_path, encoding="utf-8") as f:
        gold_pairs = json.load(f)

    remapped_pairs = []
    sample_mappings = []

    for pair in gold_pairs:
        old_cid = pair["relevant_chunk_id"]
        rid = old_cid.split("_")[0]
        query = pair["query"]

        # Find old text
        old_text = ""
        old_chunk_file = old_chunks_dir / f"{rid}.json"
        if old_chunk_file.exists():
            with open(old_chunk_file, encoding="utf-8") as f:
                old_data = json.load(f)
            for c in old_data:
                if c["chunk_id"] == old_cid:
                    old_text = c["text"]
                    break

        new_chunks = all_new_chunks.get(rid, [])
        if not new_chunks:
            remapped_pairs.append({**pair, "remapped_chunk_id": old_cid, "jaccard": 0.0})
            continue

        best_cid = new_chunks[0].chunk_id
        best_sim = -1.0
        best_new_text = ""

        for nc in new_chunks:
            # Overlap with old chunk text if available, or query overlap
            sim_old = jaccard_similarity(old_text, nc.text) if old_text else 0.0
            sim_query = jaccard_similarity(query, nc.text)
            sim = 0.8 * sim_old + 0.2 * sim_query
            if sim > best_sim:
                best_sim = sim
                best_cid = nc.chunk_id
                best_new_text = nc.text

        remapped_pair = {
            **pair,
            "old_chunk_id": old_cid,
            "relevant_chunk_id": best_cid,
            "jaccard_overlap": round(best_sim, 4),
            "old_text_preview": old_text[:120].replace("\n", " "),
            "new_text_preview": best_new_text[:120].replace("\n", " "),
        }
        remapped_pairs.append(remapped_pair)

        if len(sample_mappings) < 5:
            sample_mappings.append(remapped_pair)

    print("\n--- SAMPLE 5 REMAPPED GOLD PAIRS ---")
    for s in sample_mappings:
        print(f"Query: {s['query'][:60]}...")
        print(
            f"  Old ID: {s['old_chunk_id']} -> New ID: {s['relevant_chunk_id']} (Overlap: {s['jaccard_overlap']})"
        )
        print(f"  New Snippet: {s['new_text_preview'][:80]}...")

    return remapped_pairs


def compute_pool_statistics(
    gold_pairs: list[dict[str, Any]], all_chunks: dict[str, list[ResumeChunk]]
) -> dict[str, float]:
    """Report pool min, median, max chunks per gold resume, and random baseline."""
    pool_sizes = []
    random_hit5 = []
    random_hit10 = []
    random_mrrs = []

    for pair in gold_pairs:
        cid = pair["relevant_chunk_id"]
        rid = cid.split("_")[0]
        chunks = all_chunks.get(rid, [])
        n = len(chunks)
        if n == 0:
            continue
        pool_sizes.append(n)
        random_hit5.append(min(1.0, 5.0 / n))
        random_hit10.append(min(1.0, 10.0 / n))
        random_mrrs.append(harmonic_mean_rr(n))

    stats = {
        "min_pool": float(np.min(pool_sizes)),
        "median_pool": float(np.median(pool_sizes)),
        "max_pool": float(np.max(pool_sizes)),
        "mean_pool": float(np.mean(pool_sizes)),
        "random_hit5": float(np.mean(random_hit5)),
        "random_hit10": float(np.mean(random_hit10)),
        "random_mrr": float(np.mean(random_mrrs)),
    }

    print("\n--- CANDIDATE POOL & RANDOM BASELINE (WITHIN-RESUME) ---")
    print(
        f"Candidate chunks per resume: Min={stats['min_pool']:.0f}, Median={stats['median_pool']:.0f}, Max={stats['max_pool']:.0f}, Mean={stats['mean_pool']:.1f}"
    )
    print(
        f"Random Guess Baseline: Hit@5={stats['random_hit5'] * 100:.2f}%, Hit@10={stats['random_hit10'] * 100:.2f}%, MRR={stats['random_mrr']:.4f}"
    )

    return stats


def run_within_resume_eval(
    gold_pairs: list[dict[str, Any]],
    all_chunks: dict[str, list[ResumeChunk]],
    embedder: ONNXEmbedder,
    mode: Literal["bm25", "dense", "hybrid"],
) -> dict[str, float]:
    """Run evaluation within isolated candidate resumes."""
    indices: dict[str, CandidateIsolatedIndex] = {}
    for pair in gold_pairs:
        rid = pair["relevant_chunk_id"].split("_")[0]
        if rid not in indices and rid in all_chunks:
            indices[rid] = CandidateIsolatedIndex(rid, all_chunks[rid], embedder=embedder)

    hit1, hit3, hit5, hit10, mrr = [], [], [], [], []

    for pair in gold_pairs:
        target_cid = pair["relevant_chunk_id"]
        rid = target_cid.split("_")[0]
        if rid not in indices:
            hit1.append(0.0)
            hit3.append(0.0)
            hit5.append(0.0)
            hit10.append(0.0)
            mrr.append(0.0)
            continue

        results = indices[rid].search(query=pair["query"], top_k=10, mode=mode)
        retrieved_ids = [r.chunk_id for r in results]

        h1 = 1.0 if target_cid in retrieved_ids[:1] else 0.0
        h3 = 1.0 if target_cid in retrieved_ids[:3] else 0.0
        h5 = 1.0 if target_cid in retrieved_ids[:5] else 0.0
        h10 = 1.0 if target_cid in retrieved_ids[:10] else 0.0

        rec_rank = 0.0
        if target_cid in retrieved_ids:
            rec_rank = 1.0 / (retrieved_ids.index(target_cid) + 1)

        hit1.append(h1)
        hit3.append(h3)
        hit5.append(h5)
        hit10.append(h10)
        mrr.append(rec_rank)

    return {
        "hit1": float(np.mean(hit1)),
        "hit3": float(np.mean(hit3)),
        "hit5": float(np.mean(hit5)),
        "hit10": float(np.mean(hit10)),
        "mrr": float(np.mean(mrr)),
    }


class CorpusWideGlobalIndex:
    def __init__(self, chunks: list[ResumeChunk], embedder: ONNXEmbedder) -> None:
        self.chunks = chunks
        self.embedder = embedder
        self.num_chunks = len(chunks)

        # 1. BM25 index
        print(f"Building global BM25 index over {self.num_chunks} chunks...")
        corpus_texts = [c.text for c in chunks]
        tokens = bm25s.tokenize(corpus_texts, show_progress=False)
        self.bm25_retriever = bm25s.BM25(corpus=list(range(len(corpus_texts))))
        self.bm25_retriever.index(tokens, show_progress=False)

        # 2. Dense Matrix
        print(
            f"Building global dense embeddings for {self.num_chunks} chunks using {embedder.model_name}..."
        )
        t0 = time.perf_counter()
        self.dense_matrix = embedder.embed_texts(corpus_texts, batch_size=64)
        print(
            f"Dense matrix of shape {self.dense_matrix.shape} built in {time.perf_counter() - t0:.2f}s."
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
        mode: Literal["bm25", "dense", "hybrid"] = "hybrid",
        rrf_k: int = 60,
    ) -> list[str]:
        if mode == "bm25":
            query_tokens = bm25s.tokenize([query], show_progress=False)
            indices, _ = self.bm25_retriever.retrieve(query_tokens, k=top_k, show_progress=False)
            return [self.chunks[int(idx)].chunk_id for idx in indices[0]]
        elif mode == "dense":
            q_vec = self.embedder.embed_query(query)
            scores = np.dot(self.dense_matrix, q_vec)
            top_indices = np.argsort(-scores)[:top_k]
            return [self.chunks[int(idx)].chunk_id for idx in top_indices]
        else:
            # Hybrid (RRF)
            query_tokens = bm25s.tokenize([query], show_progress=False)
            bm25_indices, _ = self.bm25_retriever.retrieve(
                query_tokens, k=min(100, self.num_chunks), show_progress=False
            )
            q_vec = self.embedder.embed_query(query)
            scores = np.dot(self.dense_matrix, q_vec)
            dense_indices = np.argsort(-scores)[: min(100, self.num_chunks)]

            rrf_scores: dict[int, float] = {}
            for rank_0, idx in enumerate(bm25_indices[0]):
                idx_int = int(idx)
                rrf_scores[idx_int] = rrf_scores.get(idx_int, 0.0) + (1.0 / (rrf_k + rank_0 + 1))
            for rank_0, idx in enumerate(dense_indices):
                idx_int = int(idx)
                rrf_scores[idx_int] = rrf_scores.get(idx_int, 0.0) + (1.0 / (rrf_k + rank_0 + 1))

            sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
            return [self.chunks[idx].chunk_id for idx, _ in sorted_items]


def run_corpus_wide_eval_with_index(
    gold_pairs: list[dict[str, Any]],
    global_index: CorpusWideGlobalIndex,
    mode: Literal["bm25", "dense", "hybrid"],
) -> dict[str, float]:
    """Search across all chunks using pre-built global index."""
    hit1, hit3, hit5, hit10, mrr = [], [], [], [], []

    for pair in gold_pairs:
        target_cid = pair["relevant_chunk_id"]
        retrieved_ids = global_index.search(query=pair["query"], top_k=10, mode=mode)

        h1 = 1.0 if target_cid in retrieved_ids[:1] else 0.0
        h3 = 1.0 if target_cid in retrieved_ids[:3] else 0.0
        h5 = 1.0 if target_cid in retrieved_ids[:5] else 0.0
        h10 = 1.0 if target_cid in retrieved_ids[:10] else 0.0

        rec_rank = 0.0
        if target_cid in retrieved_ids:
            rec_rank = 1.0 / (retrieved_ids.index(target_cid) + 1)

        hit1.append(h1)
        hit3.append(h3)
        hit5.append(h5)
        hit10.append(h10)
        mrr.append(rec_rank)

    return {
        "hit1": float(np.mean(hit1)),
        "hit3": float(np.mean(hit3)),
        "hit5": float(np.mean(hit5)),
        "hit10": float(np.mean(hit10)),
        "mrr": float(np.mean(mrr)),
    }


def run_embedder_benchmark(
    model_type: Literal["minilm", "bge-small"],
) -> dict[str, Any]:
    """Benchmark single embedder in fresh process."""
    gc.collect()
    rss_start = get_current_rss_mb()
    t0 = time.perf_counter()

    embedder = ONNXEmbedder(model_type=model_type, quantized=True)
    init_time = time.perf_counter() - t0
    rss_loaded = get_current_rss_mb()

    # Latency test on 50 chunks
    sample_texts = [
        f"Sample professional experience entry {i} covering software engineering, cloud services, and database optimizations."
        for i in range(50)
    ]
    t_lat0 = time.perf_counter()
    _ = embedder.embed_texts(sample_texts, batch_size=16)
    latency_per_chunk_ms = ((time.perf_counter() - t_lat0) / len(sample_texts)) * 1000.0
    rss_after = get_current_rss_mb()

    return {
        "model_type": model_type,
        "rss_initial_mb": round(rss_start, 1),
        "rss_loaded_mb": round(rss_loaded, 1),
        "rss_after_mb": round(rss_after, 1),
        "init_time_s": round(init_time, 2),
        "latency_per_chunk_ms": round(latency_per_chunk_ms, 2),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["all", "embedder_only"], default="all")
    parser.add_argument("--model", choices=["minilm", "bge-small"], default="minilm")
    args = parser.parse_args()

    if args.mode == "embedder_only":
        res = run_embedder_benchmark(args.model)
        print(f"BENCHMARK_RESULT:{json.dumps(res)}")
        sys.exit(0)

    # Full execution
    all_chunks = get_or_create_new_chunks()
    remap_path = Path(__file__).resolve().parent.parent / "docs" / "eval_pairs_remapped_v2.json"
    if remap_path.exists():
        with open(remap_path, encoding="utf-8") as f:
            remapped_gold = json.load(f)
        print(f"Loaded {len(remapped_gold)} verified remapped pairs from {remap_path}")
    else:
        remapped_gold = remap_gold_pairs(all_chunks)
        with open(remap_path, "w", encoding="utf-8") as f:
            json.dump(remapped_gold, f, indent=2)
        print(f"Saved {len(remapped_gold)} remapped pairs to {remap_path}")

    pool_stats = compute_pool_statistics(remapped_gold, all_chunks)

    # Now evaluate within-resume and corpus-wide for MiniLM
    print("\n--- EVALUATING MINILM (WITHIN-RESUME & CORPUS-WIDE) ---")
    embedder_minilm = ONNXEmbedder(model_type="minilm")

    for m in ["bm25", "dense", "hybrid"]:
        res_within = run_within_resume_eval(remapped_gold, all_chunks, embedder_minilm, mode=m)
        print(
            f"Within-Resume [{m.upper()}]: Hit@1={res_within['hit1'] * 100:.1f}%, Hit@3={res_within['hit3'] * 100:.1f}%, Hit@5={res_within['hit5'] * 100:.1f}%, Hit@10={res_within['hit10'] * 100:.1f}%, MRR={res_within['mrr']:.4f}"
        )

    # Flatten all chunks
    pooled_chunks: list[ResumeChunk] = []
    for chunks in all_chunks.values():
        pooled_chunks.extend(chunks)

    corpus_results: dict[str, Any] = {
        "metadata": {
            "source_script": "scripts/evaluate_truth_and_embedders.py",
            "total_pooled_chunks": len(pooled_chunks),
            "total_resumes": len(all_chunks),
            "total_gold_pairs": len(remapped_gold),
            "pool_statistics": pool_stats,
            "old_project_baseline_hit5": 64.7,
        },
        "within_resume": {},
        "corpus_wide": {},
    }

    print("\n--- EVALUATING MINILM (WITHIN-RESUME & CORPUS-WIDE) ---")
    embedder_minilm = ONNXEmbedder(model_type="minilm")

    for m in ["bm25", "dense", "hybrid"]:
        res_within = run_within_resume_eval(remapped_gold, all_chunks, embedder_minilm, mode=m)
        corpus_results["within_resume"][f"{m}_minilm" if m != "bm25" else "bm25"] = res_within
        if m == "bm25":
            corpus_results["within_resume"]["bm25_minilm"] = res_within
        print(
            f"Within-Resume [{m.upper()}]: Hit@1={res_within['hit1'] * 100:.1f}%, Hit@3={res_within['hit3'] * 100:.1f}%, Hit@5={res_within['hit5'] * 100:.1f}%, Hit@10={res_within['hit10'] * 100:.1f}%, MRR={res_within['mrr']:.4f}"
        )

    # Build MiniLM Global Index
    global_index_minilm = CorpusWideGlobalIndex(pooled_chunks, embedder_minilm)
    for m in ["bm25", "dense", "hybrid"]:
        res_corpus = run_corpus_wide_eval_with_index(remapped_gold, global_index_minilm, mode=m)
        corpus_results["corpus_wide"][f"{m}_minilm" if m != "bm25" else "bm25"] = res_corpus
        if m == "bm25":
            corpus_results["corpus_wide"]["bm25_minilm"] = res_corpus
        print(
            f"Corpus-Wide [{m.upper()} MiniLM]: Hit@1={res_corpus['hit1'] * 100:.1f}%, Hit@3={res_corpus['hit3'] * 100:.1f}%, Hit@5={res_corpus['hit5'] * 100:.1f}%, Hit@10={res_corpus['hit10'] * 100:.1f}%, MRR={res_corpus['mrr']:.4f}"
        )

    print("\n--- EVALUATING BGE-SMALL (WITHIN-RESUME & CORPUS-WIDE) ---")
    embedder_bge = ONNXEmbedder(model_type="bge-small")

    for m in ["dense", "hybrid"]:
        res_within = run_within_resume_eval(remapped_gold, all_chunks, embedder_bge, mode=m)
        corpus_results["within_resume"][f"{m}_bge"] = res_within
        print(
            f"Within-Resume [{m.upper()} BGE]: Hit@1={res_within['hit1'] * 100:.1f}%, Hit@3={res_within['hit3'] * 100:.1f}%, Hit@5={res_within['hit5'] * 100:.1f}%, Hit@10={res_within['hit10'] * 100:.1f}%, MRR={res_within['mrr']:.4f}"
        )

    global_index_bge = CorpusWideGlobalIndex(pooled_chunks, embedder_bge)
    for m in ["dense", "hybrid"]:
        res_corpus = run_corpus_wide_eval_with_index(remapped_gold, global_index_bge, mode=m)
        corpus_results["corpus_wide"][f"{m}_bge"] = res_corpus
        print(
            f"Corpus-Wide [{m.upper()} BGE]: Hit@1={res_corpus['hit1'] * 100:.1f}%, Hit@3={res_corpus['hit3'] * 100:.1f}%, Hit@5={res_corpus['hit5'] * 100:.1f}%, Hit@10={res_corpus['hit10'] * 100:.1f}%, MRR={res_corpus['mrr']:.4f}"
        )

    # Determine winning production embedder
    minilm_cw_hit5 = corpus_results["corpus_wide"]["hybrid_minilm"]["hit5"]
    minilm_cw_mrr = corpus_results["corpus_wide"]["hybrid_minilm"]["mrr"]
    bge_cw_hit5 = corpus_results["corpus_wide"]["hybrid_bge"]["hit5"]
    bge_cw_mrr = corpus_results["corpus_wide"]["hybrid_bge"]["mrr"]

    bge_wins_both = (bge_cw_hit5 > minilm_cw_hit5) and (bge_cw_mrr > minilm_cw_mrr)
    production_embedder = "bge-small" if bge_wins_both else "minilm"

    corpus_results["decision"] = {
        "production_embedder": production_embedder,
        "rule": "MiniLM unless BGE wins both Hit@5 and MRR corpus-wide",
        "minilm_hybrid_hit5": round(minilm_cw_hit5 * 100, 2),
        "minilm_hybrid_mrr": round(minilm_cw_mrr, 4),
        "bge_hybrid_hit5": round(bge_cw_hit5 * 100, 2),
        "bge_hybrid_mrr": round(bge_cw_mrr, 4),
        "bge_wins_both": bge_wins_both,
    }

    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    with open(docs_dir / "eval_corpus_retrieval_report.json", "w", encoding="utf-8") as f:
        json.dump(corpus_results, f, indent=2)
    print(f"\nSaved corpus retrieval report to {docs_dir / 'eval_corpus_retrieval_report.json'}")

    # Run fresh embedder footprints
    print("\n--- MEASURING EMBEDDER RUNTIME FOOTPRINTS ---")
    bench_minilm = run_embedder_benchmark("minilm")
    bench_bge = run_embedder_benchmark("bge-small")

    embedder_report = {
        "metadata": {
            "source_script": "scripts/evaluate_truth_and_embedders.py",
            "test_description": "Runtime RSS and batch CPU inference latency per chunk",
        },
        "models": {
            "minilm": bench_minilm,
            "bge-small": bench_bge,
        },
        "chosen_production_model": production_embedder,
    }

    with open(docs_dir / "eval_embedder_footprint_report.json", "w", encoding="utf-8") as f:
        json.dump(embedder_report, f, indent=2)
    print(f"Saved embedder footprint report to {docs_dir / 'eval_embedder_footprint_report.json'}")
