"""Unit tests for quantized ONNX embedder module."""

import numpy as np
import pytest
from app.core.embeddings import ONNXEmbedder, _l2_normalize, _mean_pooling


def test_mean_pooling_and_l2_normalize() -> None:
    """Verify mean pooling with attention mask and L2 normalization."""
    token_embeddings = np.array([[[1.0, 2.0], [3.0, 4.0], [0.0, 0.0]]], dtype=np.float32)
    attention_mask = np.array([[1, 1, 0]], dtype=np.int64)

    pooled = _mean_pooling(token_embeddings, attention_mask)
    assert pooled.shape == (1, 2)
    # Expected mean of [1,2] and [3,4] is [2.0, 3.0]
    assert np.allclose(pooled, [[2.0, 3.0]], atol=1e-5)

    normed = _l2_normalize(pooled)
    assert np.allclose(np.linalg.norm(normed, axis=1), [1.0], atol=1e-5)


def test_onnx_embedder_unsupported_model() -> None:
    """Verify ValueError on unsupported model name."""
    with pytest.raises(ValueError, match="Unsupported model_type"):
        ONNXEmbedder(model_type="invalid-model")  # type: ignore[arg-type]


def test_onnx_embedder_empty_input() -> None:
    """Verify embedding an empty list returns empty array of correct shape."""
    embedder = ONNXEmbedder("minilm")
    vecs = embedder.embed_texts([])
    assert vecs.shape == (0, 384)


def test_onnx_embedder_minilm_and_bge_small() -> None:
    """Verify MiniLM and BGE-small embedding generation and properties."""
    minilm = ONNXEmbedder("minilm")
    assert minilm.dimension == 384
    assert minilm.model_name == "minilm-quantized"

    texts = ["Staff Python Developer", "React Frontend Engineer"]
    vecs = minilm.embed_texts(texts, batch_size=2)
    assert vecs.shape == (2, 384)
    assert vecs.dtype == np.float32
    assert np.allclose(np.linalg.norm(vecs, axis=1), [1.0, 1.0], atol=1e-5)

    q_vec = minilm.embed_query("Python")
    assert q_vec.shape == (384,)
    assert np.isclose(np.linalg.norm(q_vec), 1.0, atol=1e-5)

    bge = ONNXEmbedder("bge-small")
    assert bge.dimension == 384
    assert bge.model_name == "bge-small-quantized"
    bge_q = bge.embed_query("Search query")
    assert bge_q.shape == (384,)
    assert np.isclose(np.linalg.norm(bge_q), 1.0, atol=1e-5)
