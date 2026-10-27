"""Dense embedding module using ONNX Runtime with quantized CPU inference."""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal, cast

import numpy as np
import onnxruntime as ort
from huggingface_hub import snapshot_download
from tokenizers import Tokenizer


class BaseEmbedder(ABC):
    """Abstract interface for dense text embedding models."""

    @abstractmethod
    def embed_texts(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed a list of text strings into an L2-normalized float32 numpy array of shape (N, D).
        """
        pass

    @abstractmethod
    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a single query string into an L2-normalized float32 numpy array of shape (D,).
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifying name of the embedding model."""
        pass


def _mean_pooling(token_embeddings: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
    """
    Weighted mean pooling over non-padding tokens.

    token_embeddings: shape (batch_size, seq_len, hidden_dim)
    attention_mask: shape (batch_size, seq_len)
    """
    input_mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
    sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
    sum_mask = np.clip(np.sum(input_mask_expanded, axis=1), a_min=1e-9, a_max=None)
    return cast(np.ndarray, sum_embeddings / sum_mask)


def _l2_normalize(embeddings: np.ndarray) -> np.ndarray:
    """L2 normalization along axis 1."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return cast(np.ndarray, embeddings / np.clip(norms, a_min=1e-9, a_max=None))


class ONNXEmbedder(BaseEmbedder):
    """
    CPU-optimized ONNX Runtime embedder supporting quantized Transformer models.

    Avoids PyTorch dependencies completely to keep process RSS under 250 MB.
    """

    MODEL_CONFIGS: dict[str, dict[str, str | int]] = {
        "minilm": {
            "repo_id": "Xenova/all-MiniLM-L6-v2",
            "dimension": 384,
            "max_length": 256,
            "query_prefix": "",
        },
        "bge-small": {
            "repo_id": "Xenova/bge-small-en-v1.5",
            "dimension": 384,
            "max_length": 256,
            "query_prefix": "Represent this sentence for searching relevant passages: ",
        },
    }

    def __init__(
        self,
        model_type: Literal["minilm", "bge-small"] = "minilm",
        cache_dir: Path | None = None,
        quantized: bool = True,
        intra_op_threads: int = 2,
    ) -> None:
        if model_type not in self.MODEL_CONFIGS:
            choices = list(self.MODEL_CONFIGS.keys())
            raise ValueError(f"Unsupported model_type '{model_type}'. Choose from: {choices}")

        self._model_type = model_type
        config = self.MODEL_CONFIGS[model_type]
        self._repo_id = str(config["repo_id"])
        self._dimension = int(config["dimension"])
        self._max_length = int(config["max_length"])
        self._query_prefix = str(config["query_prefix"])
        self._quantized = quantized

        if cache_dir is None:
            # Resolve default cache directory relative to repo root
            cache_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "hf_cache"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ["HF_HOME"] = str(self.cache_dir)

        # 1. Download or locate model artifacts in cache
        model_filename = "onnx/model_quantized.onnx" if quantized else "onnx/model.onnx"
        model_dir = snapshot_download(
            repo_id=self._repo_id,
            cache_dir=str(self.cache_dir),
            allow_patterns=[model_filename, "tokenizer.json", "tokenizer_config.json"],
        )

        onnx_file = Path(model_dir) / model_filename
        tokenizer_file = Path(model_dir) / "tokenizer.json"

        # 2. Initialize ONNX InferenceSession (CPU Execution Provider)
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = intra_op_threads
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = ort.InferenceSession(
            str(onnx_file), sess_options, providers=["CPUExecutionProvider"]
        )

        # 3. Initialize Tokenizer
        self._tokenizer = Tokenizer.from_file(str(tokenizer_file))
        self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        self._tokenizer.enable_truncation(max_length=self._max_length)

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return f"{self._model_type}{'-quantized' if self._quantized else ''}"

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Generate normalized float32 embeddings for a batch of candidate texts."""
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)

        all_embeddings: list[np.ndarray] = []

        for start_idx in range(0, len(texts), batch_size):
            batch = texts[start_idx : start_idx + batch_size]
            encodings = self._tokenizer.encode_batch(batch)

            input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
            attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)

            # Determine input names expected by the ONNX model
            input_feed: dict[str, np.ndarray] = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            }

            # If model expects token_type_ids, provide zero array
            model_inputs = [inp.name for inp in self._session.get_inputs()]
            if "token_type_ids" in model_inputs:
                input_feed["token_type_ids"] = np.zeros_like(input_ids, dtype=np.int64)

            outputs = self._session.run(None, input_feed)
            last_hidden_state = outputs[0]  # shape: (batch_size, seq_len, hidden_dim)

            pooled = _mean_pooling(last_hidden_state, attention_mask)
            normalized = _l2_normalize(pooled)
            all_embeddings.append(normalized.astype(np.float32))

        return np.vstack(all_embeddings)

    def embed_query(self, query: str) -> np.ndarray:
        """Generate normalized float32 embedding for a search query string."""
        formatted_query = f"{self._query_prefix}{query}" if self._query_prefix else query
        result = self.embed_texts([formatted_query], batch_size=1)
        return cast(np.ndarray, result[0])
