import json
import time
import uuid
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.auth import get_current_user
from src.db.session import get_db
from src.models.qa_history import QAHistory
from src.models.user import User

logger = structlog.get_logger()

router = APIRouter(prefix="/qa", tags=["qa"])


ALLOWED_MODELS = {
    "qwen2.5:3b", "qwen2.5:7b", "qwen2.5:14b", "llama3.1:8b",
    "nomic-embed-text", "gemma2:9b",
    "claude-sonnet-4-20250514", "claude-haiku-4-5-20251001",
    "gpt-4o", "gpt-4o-mini",
    "gemini-2.0-flash", "gemini-2.5-pro-preview-05-06",
}


class QueryRequest(BaseModel):
    query: str = Field(..., max_length=4096)
    top_k: int = Field(10, ge=1, le=50)
    provider: Optional[str] = None
    model: Optional[str] = None


class SourceReference(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    score: float
    content_preview: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    provider: str
    model: str
    duration_ms: int


class QAHistoryResponse(BaseModel):
    id: uuid.UUID
    query: str
    answer: Optional[str]
    sources: list
    llm_provider: Optional[str]
    llm_model: Optional[str]
    duration_ms: Optional[int]
    created_at: Any

    model_config = {"from_attributes": True}


@router.post("/query", response_model=QueryResponse)
async def qa_query(
    request: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Execute RAG query (non-streaming). Full pipeline: embed -> search -> rerank -> generate."""
    if request.model and request.model not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model not allowed. Allowed models: {sorted(ALLOWED_MODELS)}",
        )
    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty",
        )

    start = time.monotonic()

    try:
        from src.core.rag_pipeline import execute_rag_query

        result = await execute_rag_query(
            query=request.query,
            tenant_id=str(user.tenant_id),
            user_id=str(user.id),
            user_role=user.role,
            top_k=request.top_k,
            provider_override=request.provider,
            model_override=request.model,
            db=db,
        )
    except Exception as e:
        logger.error("rag_pipeline_error", error=str(e), user_id=str(user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG pipeline error. Please try again later.",
        )

    duration_ms = int((time.monotonic() - start) * 1000)

    # Save to history
    history = QAHistory(
        tenant_id=user.tenant_id,
        user_id=user.id,
        query=request.query,
        answer=result["answer"],
        sources=result["sources"],
        llm_provider=result["provider"],
        llm_model=result["model"],
        token_usage=result.get("token_usage", {}),
        duration_ms=duration_ms,
    )
    db.add(history)
    await db.commit()

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceReference(**s) for s in result["sources"]],
        provider=result["provider"],
        model=result["model"],
        duration_ms=duration_ms,
    )


@router.post("/query/stream")
async def qa_query_stream(
    request: QueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Execute RAG query with SSE streaming response."""
    from src.core.rag_pipeline import stream_rag_query

    if request.model and request.model not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model not allowed. Allowed models: {sorted(ALLOWED_MODELS)}",
        )
    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty",
        )

    start = time.monotonic()

    async def event_generator():
        collected_answer = ""
        collected_sources: list = []
        try:
            async for event in stream_rag_query(
                query=request.query,
                tenant_id=str(user.tenant_id),
                user_id=str(user.id),
                user_role=user.role,
                top_k=request.top_k,
                provider_override=request.provider,
                model_override=request.model,
                db=db,
            ):
                parsed = json.loads(event)
                if parsed.get("type") == "token":
                    collected_answer += parsed.get("data", "")
                elif parsed.get("type") == "sources":
                    collected_sources = parsed.get("data", [])
                yield f"data: {event}\n\n"
        except Exception as e:
            logger.error("stream_rag_error", error=str(e), user_id=str(user.id))
            yield f"data: {json.dumps({'type': 'error', 'data': 'An error occurred. Please try again.'})}\n\n"
        yield "data: [DONE]\n\n"

        # Save to history
        try:
            if collected_answer:
                duration_ms = int((time.monotonic() - start) * 1000)
                history = QAHistory(
                    tenant_id=user.tenant_id,
                    user_id=user.id,
                    query=request.query,
                    answer=collected_answer,
                    sources=collected_sources,
                    llm_provider=request.provider or "",
                    llm_model=request.model or "",
                    token_usage={},
                    duration_ms=duration_ms,
                )
                db.add(history)
                await db.commit()
        except Exception as e:
            logger.warning("stream_history_save_failed", error=str(e))

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history", response_model=list[QAHistoryResponse])
async def get_history(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get user's QA history."""
    result = await db.execute(
        select(QAHistory)
        .where(QAHistory.user_id == user.id, QAHistory.tenant_id == user.tenant_id)
        .order_by(QAHistory.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
