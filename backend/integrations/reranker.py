from __future__ import annotations

from config import BGE_MODEL_CACHE_DIR, BGE_RERANKER_MODEL_NAME


_model: object | None = None


def rerank(query: str, passages: list[str]) -> list[float]:
    if not passages:
        return []
    scores = _get_model().compute_score([[query, passage] for passage in passages], normalize=True)
    if not isinstance(scores, list):
        scores = [scores]
    return [float(score) for score in scores]


def _get_model():
    global _model
    if _model is None:
        from FlagEmbedding import FlagReranker

        BGE_MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _model = FlagReranker(BGE_RERANKER_MODEL_NAME, cache_dir=str(BGE_MODEL_CACHE_DIR), use_fp16=False)
    return _model
