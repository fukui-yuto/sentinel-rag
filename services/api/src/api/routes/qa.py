import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.auth import get_current_user
from src.db.session import get_db
from src.models.qa_history import QAHistory
from src.models.user import User

router = APIRouter(prefix="/qa", tags=["qa"])


class QueryRequest(BaseModel):
    query: str
    top_k: int = 10
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG pipeline error: {e}",
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

    async def event_generator():
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
            yield f"data: {event}\n\n"
        yield "data: [DONE]\n\n"

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
