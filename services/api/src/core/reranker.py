"""Reranking module for improving search result relevance."""

from typing import Any


def rerank_results(
    query: str,
    results: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Rerank search results using a simple keyword-overlap score.

    In production, this should be replaced with a cross-encoder model
    (e.g., sentence-transformers cross-encoder) or Cohere Rerank API.
    """
    scored = []
    query_terms = set(query.lower().split())

    for result in results:
        content = result.get("content", "").lower()
        # Simple term overlap scoring
        overlap = sum(1 for term in query_terms if term in content)
        combined_score = result.get("score", 0) * 0.7 + (overlap / max(len(query_terms), 1)) * 0.3
        scored.append({**result, "rerank_score": combined_score})

    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    return scored[:top_k]
