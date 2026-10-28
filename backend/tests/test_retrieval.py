"""Tests for candidate-isolated retrieval, blob serialization, and zero cross-candidate leakage."""

from typing import cast

import numpy as np
import pytest
from app.core.embeddings import BaseEmbedder
from app.core.models import ResumeChunk
from app.core.retrieval import (
    CandidateChunkRecord,
    CandidateIsolatedIndex,
    blob_to_vector,
    vector_to_blob,
)


class MockEmbedder(BaseEmbedder):
    """Fast deterministic embedder for unit testing."""

    @property
    def dimension(self) -> int:
        return 4

    @property
    def model_name(self) -> str:
        return "mock-embedder"

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        vectors: list[np.ndarray] = []
        for text in texts:
            # Deterministic pseudo-vector based on character values
            h = sum(ord(c) for c in text)
            vec = np.array([h % 7, (h // 7) % 5, (h // 35) % 3, 1.0], dtype=np.float32)
            norm = np.linalg.norm(vec)
            vectors.append(vec / (norm if norm > 0 else 1.0))
        return np.vstack(vectors)

    def embed_query(self, query: str) -> np.ndarray:
        return cast(np.ndarray, self.embed_texts([query])[0])


def test_blob_serialization_roundtrip() -> None:
    """Verify raw byte serialization of float32 vectors has zero precision loss."""
    original = np.array([[0.123456, -0.654321, 0.987654, 0.0]], dtype=np.float32)
    blob = vector_to_blob(original)
    recovered = blob_to_vector(blob, dimension=4)
    assert np.allclose(original, recovered, atol=1e-7)
    assert recovered.dtype == np.float32


def test_candidate_isolation_violation_raises() -> None:
    """Verify injecting a chunk belonging to Candidate B into Candidate A's index is blocked."""
    cand_a_chunk = ResumeChunk(
        chunk_id="candA_001",
        resume_id="candA",
        section="experience",
        text="Software engineer at Alpha Corp",
    )
    cand_b_chunk = ResumeChunk(
        chunk_id="candB_001",
        resume_id="candB",
        section="experience",
        text="Marketing manager at Beta Inc",
    )

    with pytest.raises(ValueError, match="Candidate isolation violation"):
        CandidateIsolatedIndex(
            candidate_id="candA",
            chunks=[cand_a_chunk, cand_b_chunk],
            embedder=MockEmbedder(),
        )


def test_zero_cross_candidate_leakage() -> None:
    """
    Formally prove that searching Candidate A for Candidate B's unique terms
    returns strictly zero chunks from Candidate B.
    """
    chunks_cand_a = [
        ResumeChunk(
            chunk_id="candA_001",
            resume_id="candA",
            section="experience",
            text="Senior Python Backend Developer with PostgreSQL and Redis expertise.",
        ),
        ResumeChunk(
            chunk_id="candA_002",
            resume_id="candA",
            section="skills",
            text="Python, Docker, FastAPI, Git, Linux.",
        ),
    ]

    chunks_cand_b = [
        ResumeChunk(
            chunk_id="candB_001",
            resume_id="candB",
            section="experience",
            text="Clinical Cardiologist diagnosing rare pediatric cardiovascular conditions.",
        ),
        ResumeChunk(
            chunk_id="candB_002",
            resume_id="candB",
            section="education",
            text="Doctor of Medicine from Johns Hopkins School of Medicine.",
        ),
    ]

    embedder = MockEmbedder()
    index_a = CandidateIsolatedIndex("candA", chunks_cand_a, embedder=embedder)
    index_b = CandidateIsolatedIndex("candB", chunks_cand_b, embedder=embedder)

    # Search Index A with Candidate B's specialized query
    results_a = index_a.search("pediatric cardiology diagnosis", mode="hybrid")
    for r in results_a:
        assert r.resume_id == "candA"
        assert not r.chunk_id.startswith("candB_")
        assert "Cardiologist" not in r.text

    # Search Index B with Candidate A's specialized query
    results_b = index_b.search("FastAPI PostgreSQL Redis", mode="hybrid")
    for r in results_b:
        assert r.resume_id == "candB"
        assert not r.chunk_id.startswith("candA_")
        assert "Python" not in r.text


def test_retrieval_modes() -> None:
    """Verify BM25, Dense, and Hybrid modes return ordered results."""
    chunks = [
        CandidateChunkRecord(
            chunk_id="c1_001",
            resume_id="c1",
            section="experience",
            text="Architected distributed database engine in Rust.",
        ),
        CandidateChunkRecord(
            chunk_id="c1_002",
            resume_id="c1",
            section="skills",
            text="Rust, C++, WebAssembly, Concurrency.",
        ),
    ]
    index = CandidateIsolatedIndex("c1", chunks, embedder=MockEmbedder())

    # BM25 mode
    bm25_res = index.search("Rust database", mode="bm25", top_k=2)
    assert len(bm25_res) == 2
    assert bm25_res[0].rank == 1
    assert bm25_res[0].bm25_score is not None

    # Dense mode
    dense_res = index.search("database storage", mode="dense", top_k=2)
    assert len(dense_res) == 2
    assert dense_res[0].dense_score is not None

    # Hybrid mode with section boost
    hybrid_res = index.search(
        "Rust concurrency",
        mode="hybrid",
        top_k=2,
        section_boosts={"skills": 0.5},
    )
    assert len(hybrid_res) == 2
    assert hybrid_res[0].score > 0
