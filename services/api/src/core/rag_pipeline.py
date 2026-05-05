"""Core RAG pipeline: embed query -> vector search -> rerank -> generate answer."""

import json
from collections.abc import AsyncGenerator
from typing import Any, Optional

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.prompt_templates import build_qa_prompt
from src.models.document import Document
from src.providers.router import get_embedding_provider, get_llm_provider

logger = structlog.get_logger()


async def execute_rag_query(
    query: str,
    tenant_id: str,
    user_id: str,
    user_role: str,
    top_k: int = 10,
    provider_override: Optional[str] = None,
    model_override: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> dict[str, Any]:
    """Execute the full RAG pipeline and return structured results."""
    # 1. Embed the query
    embedding_provider = get_embedding_provider()
    embed_result = await embedding_provider.embed([query])
    query_vector = embed_result.embeddings[0]

    # 2. Search Qdrant with tenant filter
    qdrant = AsyncQdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key or None,
        https=False,
    )
    collection_name = f"tenant_{tenant_id}"

    try:
        result = await qdrant.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            query_filter=Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                ]
            ),
        )
        search_results = result.points
    except Exception:
        search_results = []
    finally:
        await qdrant.close()

    if not search_results:
        return {
            "answer": "関連するドキュメントが見つかりませんでした。",
            "sources": [],
            "provider": provider_override or settings.default_llm_provider,
            "model": model_override or "",
            "token_usage": {},
        }

    # 3. Determine max sensitivity from retrieved chunks
    max_sensitivity = "public"
    sensitivity_order = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
    sources = []

    for hit in search_results:
        payload = hit.payload or {}
        chunk_sensitivity = payload.get("sensitivity", "internal")
        if sensitivity_order.get(chunk_sensitivity, 0) > sensitivity_order.get(max_sensitivity, 0):
            max_sensitivity = chunk_sensitivity

        sources.append({
            "document_id": payload.get("document_id", ""),
            "filename": payload.get("filename", ""),
            "chunk_index": payload.get("chunk_index", 0),
            "score": hit.score,
            "content_preview": payload.get("content", "")[:200],
        })

    # 4. Build context and generate answer
    context_chunks = [
        hit.payload.get("content", "") for hit in search_results if hit.payload
    ]
    prompt = build_qa_prompt(query, context_chunks)

    llm = get_llm_provider(
        provider_name=provider_override,
        sensitivity=max_sensitivity,
    )
    response = await llm.generate(
        prompt=prompt,
        model=model_override,
    )

    return {
        "answer": response.content,
        "sources": sources,
        "provider": response.provider,
        "model": response.model,
        "token_usage": {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
        },
    }


async def stream_rag_query(
    query: str,
    tenant_id: str,
    user_id: str,
    user_role: str,
    top_k: int = 10,
    provider_override: Optional[str] = None,
    model_override: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> AsyncGenerator[str, None]:
    """Execute RAG pipeline with streaming LLM response."""
    # 1. Embed the query
    embedding_provider = get_embedding_provider()
    embed_result = await embedding_provider.embed([query])
    query_vector = embed_result.embeddings[0]

    # 2. Search Qdrant
    qdrant = AsyncQdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key or None,
        https=False,
    )
    collection_name = f"tenant_{tenant_id}"

    try:
        result = await qdrant.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            query_filter=Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                ]
            ),
        )
        search_results = result.points
    except Exception:
        search_results = []
    finally:
        await qdrant.close()

    # Send sources first
    sources = []
    max_sensitivity = "public"
    sensitivity_order = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}

    for hit in search_results:
        payload = hit.payload or {}
        chunk_sensitivity = payload.get("sensitivity", "internal")
        if sensitivity_order.get(chunk_sensitivity, 0) > sensitivity_order.get(max_sensitivity, 0):
            max_sensitivity = chunk_sensitivity
        sources.append({
            "document_id": payload.get("document_id", ""),
            "filename": payload.get("filename", ""),
            "chunk_index": payload.get("chunk_index", 0),
            "score": hit.score,
        })

    yield json.dumps({"type": "sources", "data": sources}, ensure_ascii=False)

    if not search_results:
        yield json.dumps({"type": "token", "data": "関連するドキュメントが見つかりませんでした。"})
        return

    # 3. Stream LLM response
    context_chunks = [
        hit.payload.get("content", "") for hit in search_results if hit.payload
    ]
    prompt = build_qa_prompt(query, context_chunks)

    llm = get_llm_provider(provider_name=provider_override, sensitivity=max_sensitivity)
    async for token in llm.stream(prompt=prompt, model=model_override):
        yield json.dumps({"type": "token", "data": token}, ensure_ascii=False)
