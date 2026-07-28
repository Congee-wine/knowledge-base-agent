from __future__ import annotations

from typing import Protocol

from config import BGE_MODEL_CACHE_DIR, BGE_MODEL_NAME


class EmbeddingModel(Protocol):
    def encode(self, sentences: list[str], **kwargs: object) -> dict[str, object]: ...


_model: EmbeddingModel | None = None


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    result = _get_model().encode(texts, batch_size=len(texts), max_length=8192)
    vectors = result.get("dense_vecs")
    if hasattr(vectors, "tolist"):
        vectors = vectors.tolist()
    if not isinstance(vectors, list):
        raise RuntimeError("bge-m3 returned no dense vectors")
    return [[float(value) for value in vector] for vector in vectors]


def _get_model() -> EmbeddingModel:
    global _model
    if _model is None:
        from FlagEmbedding import BGEM3FlagModel

        BGE_MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _model = BGEM3FlagModel(BGE_MODEL_NAME, cache_dir=str(BGE_MODEL_CACHE_DIR), use_fp16=False)
    return _model
