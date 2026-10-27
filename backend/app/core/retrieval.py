"""Candidate-isolated hybrid retrieval engine combining BM25 and dense vector search via RRF."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import bm25s
import numpy as np

from app.core.embeddings import BaseEmbedder
from app.core.models import ResumeChunk


def vector_to_blob(vector: np.ndarray) -> bytes:
    """Serialize a float32 numpy vector or matrix to raw binary blob."""
    return np.ascontiguousarray(vector, dtype=np.float32).tobytes()


def blob_to_vector(blob: bytes, dimension: int = 384) -> np.ndarray:
    """Deserialize a raw binary blob back into a float32 numpy array."""
    if not blob:
        return np.empty((0, dimension), dtype=np.float32)
    flat = np.frombuffer(blob, dtype=np.float32)
    return flat.reshape(-1, dimension)


@dataclass
class CandidateChunkRecord:
    """Stored candidate chunk with associated serialized embedding blob."""

    chunk_id: str
    resume_id: str
    section: str
    text: str
    embedding_blob: bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Ranked retrieval hit with evidence metadata."""

    chunk_id: str
    resume_id: str
    section: str
    text: str
    score: float
    dense_score: float | None = None
    bm25_score: float | None = None
    rank: int = 1


class CandidateIsolatedIndex:
    """
    Isolated retrieval index for a single candidate.

    Enforces zero cross-candidate leakage by strictly binding chunks,
    BM25 inverted index, and embedding vectors to one candidate ID.
    """

    def __init__(
        self,
        candidate_id: str,
        chunks: Sequence[ResumeChunk | CandidateChunkRecord],
        embedder: BaseEmbedder | None = None,
    ) -> None:
        self.candidate_id = candidate_id
        self._embedder = embedder

        # Standardize records
        self._records: list[CandidateChunkRecord] = []
        texts_to_embed: list[str] = []
        texts_indices: list[int] = []

        for idx, item in enumerate(chunks):
            if isinstance(item, ResumeChunk):
                rec = CandidateChunkRecord(
                    chunk_id=item.chunk_id,
                    resume_id=item.resume_id,
                    section=item.section,
                    text=item.text,
                    metadata=item.metadata,
                )
            else:
                rec = item

            # Verify no foreign candidate chunk sneaks into this index
            if rec.resume_id != self.candidate_id:
                raise ValueError(
                    f"Candidate isolation violation: chunk {rec.chunk_id} belongs to "
                    f"resume '{rec.resume_id}', but index is for '{self.candidate_id}'"
                )

            self._records.append(rec)
            if rec.embedding_blob is None:
                texts_to_embed.append(rec.text)
                texts_indices.append(idx)

        # 1. Compute embeddings if missing and embedder provided
        if texts_to_embed and self._embedder is not None:
            vectors = self._embedder.embed_texts(texts_to_embed)
            for idx, vec in zip(texts_indices, vectors, strict=False):
                self._records[idx].embedding_blob = vector_to_blob(vec)

        # 2. Build in-memory dense matrix
        self._dense_matrix: np.ndarray | None = None
        valid_blobs = [r.embedding_blob for r in self._records if r.embedding_blob]
        if len(valid_blobs) == len(self._records) and len(self._records) > 0:
            dim = self._embedder.dimension if self._embedder else 384
            vectors_list = [blob_to_vector(b, dim) for b in valid_blobs]
            self._dense_matrix = np.vstack(vectors_list)

        # 3. Build in-memory BM25 index with integer index references
        corpus_texts = [r.text for r in self._records]
        if corpus_texts:
            tokens = bm25s.tokenize(corpus_texts, show_progress=False)
            self._bm25_retriever = bm25s.BM25(corpus=list(range(len(corpus_texts))))
            self._bm25_retriever.index(tokens, show_progress=False)
        else:
            self._bm25_retriever = None

    @property
    def chunk_count(self) -> int:
        return len(self._records)

    def search(
        self,
        query: str,
        top_k: int = 5,
        mode: Literal["bm25", "dense", "hybrid"] = "hybrid",
        rrf_k: int = 60,
        dense_weight: float = 1.0,
        bm25_weight: float = 1.0,
        section_boosts: dict[str, float] | None = None,
    ) -> list[RetrievalResult]:
        """
        Search candidate's chunks using BM25, Dense semantic search, or RRF Hybrid.
        """
        if not self._records or not query.strip():
            return []

        num_chunks = len(self._records)
        effective_k = min(top_k, num_chunks)

        bm25_scores = np.zeros(num_chunks, dtype=np.float32)
        dense_scores = np.zeros(num_chunks, dtype=np.float32)
        bm25_ranks_map: dict[int, int] = {}

        # 1. Compute BM25 scores
        if mode in ("bm25", "hybrid") and self._bm25_retriever is not None:
            query_tokens = bm25s.tokenize([query], show_progress=False)
            retrieved_indices, retrieved_scores = self._bm25_retriever.retrieve(
                query_tokens, k=num_chunks, show_progress=False
            )
            for rank_0, (idx, score) in enumerate(
                zip(retrieved_indices[0], retrieved_scores[0], strict=False)
            ):
                idx_int = int(idx)
                bm25_scores[idx_int] = float(score)
                bm25_ranks_map[idx_int] = rank_0 + 1

        # 2. Compute Dense Cosine Similarities
        if mode in ("dense", "hybrid") and self._dense_matrix is not None:
            if self._embedder is None:
                raise ValueError("Cannot perform dense search without an embedder.")
            query_vec = self._embedder.embed_query(query)
            # Matrix dot product (both matrix and query are L2-normalized)
            dense_scores = np.dot(self._dense_matrix, query_vec).astype(np.float32)

        # 3. Score aggregation and ranking
        final_scores = np.zeros(num_chunks, dtype=np.float32)

        if mode == "bm25":
            final_scores = bm25_scores.copy()
        elif mode == "dense":
            final_scores = dense_scores.copy()
        elif mode == "hybrid":
            # Reciprocal Rank Fusion
            bm25_ranks = np.argsort(-bm25_scores)
            dense_ranks = np.argsort(-dense_scores)

            rrf_scores = np.zeros(num_chunks, dtype=np.float32)
            for rank_0, idx in enumerate(bm25_ranks):
                rank_1 = rank_0 + 1
                rrf_scores[idx] += bm25_weight / (rrf_k + rank_1)

            for rank_0, idx in enumerate(dense_ranks):
                rank_1 = rank_0 + 1
                rrf_scores[idx] += dense_weight / (rrf_k + rank_1)

            final_scores = rrf_scores

        # Apply section boosts if requested
        if section_boosts:
            for idx, rec in enumerate(self._records):
                boost = section_boosts.get(rec.section.lower(), 0.0)
                if boost != 0.0:
                    final_scores[idx] *= 1.0 + boost

        # Sort indices by final score descending
        ranked_indices = np.argsort(-final_scores)[:effective_k]

        results: list[RetrievalResult] = []
        for rank_0, idx in enumerate(ranked_indices):
            rec = self._records[idx]
            results.append(
                RetrievalResult(
                    chunk_id=rec.chunk_id,
                    resume_id=rec.resume_id,
                    section=rec.section,
                    text=rec.text,
                    score=float(final_scores[idx]),
                    dense_score=float(dense_scores[idx]) if mode in ("dense", "hybrid") else None,
                    bm25_score=float(bm25_scores[idx]) if mode in ("bm25", "hybrid") else None,
                    rank=rank_0 + 1,
                )
            )

        return results
