"""Sliding window chunking for Job Descriptions."""

from app.core.models import JDChunk

DEFAULT_JD_CHUNK_SIZE = 100
DEFAULT_JD_OVERLAP = 20


def chunk_jd_text(
    jd_text: str,
    jd_id: str = "custom_jd",
    chunk_size: int = DEFAULT_JD_CHUNK_SIZE,
    overlap: int = DEFAULT_JD_OVERLAP,
) -> list[JDChunk]:
    """
    Apply a sliding window to split Job Description text into query chunks.

    Returns a list of JDChunk instances.
    """
    words = jd_text.split()
    if not words:
        return []

    if len(words) <= chunk_size:
        return [
            JDChunk(
                chunk_id=f"{jd_id}_001",
                jd_id=jd_id,
                text=" ".join(words),
                metadata={"chunk_index": 1, "word_count": len(words)},
            )
        ]

    chunks: list[JDChunk] = []
    start = 0
    chunk_counter = 1
    step = max(1, chunk_size - overlap)

    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk_words = words[start:end]
        if chunk_words:
            chunk_text = " ".join(chunk_words)
            chunks.append(
                JDChunk(
                    chunk_id=f"{jd_id}_{chunk_counter:03d}",
                    jd_id=jd_id,
                    text=chunk_text,
                    metadata={"chunk_index": chunk_counter, "word_count": len(chunk_words)},
                )
            )
            chunk_counter += 1

        if end >= len(words):
            break
        start += step

    return chunks
