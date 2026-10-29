"""Measure runtime memory footprint and CPU latency for ONNX embedders in clean isolated subprocesses.

Measures:
1. baseline RSS (MB)
2. after_imports RSS (MB)
3. after_load RSS (MB)
4. during_inference RSS (MB)
Stating the glibc arena configuration.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
sys.path.insert(0, str(repo_root))

from scripts.provenance_helper import get_provenance


MEASURE_CODE = """
import os
import sys
import time

def get_rss_mb() -> float:
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return round(float(line.split()[1]) / 1024.0, 2)
    except Exception:
        pass
    import resource
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 2)

baseline_rss = get_rss_mb()

# 1. After imports
sys.path.insert(0, sys.argv[2])
from app.core.embeddings import ONNXEmbedder
after_imports_rss = get_rss_mb()

# 2. After load
model_name = sys.argv[1]
t0 = time.perf_counter()
embedder = ONNXEmbedder(model_name)
init_time_s = round(time.perf_counter() - t0, 3)
after_load_rss = get_rss_mb()

# 3. During inference (batch of 24 sample chunks)
sample_chunks = ["Experienced software engineer with proficiency in Python, FastAPI, and Docker." for _ in range(24)]
t_infer_start = time.perf_counter()
embeddings = embedder.embed_texts(sample_chunks)
infer_time_ms = ((time.perf_counter() - t_infer_start) / 24.0) * 1000.0
during_inference_rss = get_rss_mb()

result = {
    "model_type": model_name,
    "arena_setting": os.environ.get("MALLOC_ARENA_MAX", "default (system glibc)"),
    "rss_baseline_mb": baseline_rss,
    "rss_after_imports_mb": after_imports_rss,
    "rss_after_load_mb": after_load_rss,
    "rss_during_inference_mb": during_inference_rss,
    "init_time_s": init_time_s,
    "latency_per_chunk_ms": round(infer_time_ms, 2),
}
import json
print(json.dumps(result))
"""


def measure_isolated_model(model_name: str) -> dict:
    env = os.environ.copy()
    env["MALLOC_ARENA_MAX"] = "2"
    cmd = [
        sys.executable,
        "-c",
        MEASURE_CODE,
        model_name,
        str(backend_dir),
    ]
    raw = subprocess.check_output(cmd, env=env, text=True)
    return json.loads(raw.strip().splitlines()[-1])


def main() -> None:
    print("Measuring MiniLM in clean isolated subprocess...")
    minilm_res = measure_isolated_model("minilm")
    print(
        f"  MiniLM: Baseline={minilm_res['rss_baseline_mb']}MB, Imports={minilm_res['rss_after_imports_mb']}MB, Loaded={minilm_res['rss_after_load_mb']}MB, Inference={minilm_res['rss_during_inference_mb']}MB, Latency={minilm_res['latency_per_chunk_ms']}ms/chunk"
    )

    print("Measuring BGE-Small in clean isolated subprocess...")
    bge_res = measure_isolated_model("bge-small")
    print(
        f"  BGE:    Baseline={bge_res['rss_baseline_mb']}MB, Imports={bge_res['rss_after_imports_mb']}MB, Loaded={bge_res['rss_after_load_mb']}MB, Inference={bge_res['rss_during_inference_mb']}MB, Latency={bge_res['latency_per_chunk_ms']}ms/chunk"
    )

    prov = get_provenance("scripts/measure_embedder_footprint_clean.py")
    report = {
        "metadata": {
            **prov,
            "test_description": "Clean isolated subprocess RSS and CPU latency per chunk across lifecycle stages",
            "arena_setting": "MALLOC_ARENA_MAX=2",
        },
        "models": {
            "minilm": minilm_res,
            "bge-small": bge_res,
        },
        "chosen_production_model": "minilm",
    }

    out_file = repo_root / "docs" / "eval_embedder_footprint_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Saved embedder footprint report to {out_file}")


if __name__ == "__main__":
    main()
