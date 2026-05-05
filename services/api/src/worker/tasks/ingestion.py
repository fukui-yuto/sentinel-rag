"""Document ingestion pipeline tasks."""

import io
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from celery import shared_task

from src.core.config import settings

logger = structlog.get_logger()


@shared_task(name="src.worker.tasks.ingestion.process_document", bind=True, max_retries=3)
def process_document(self, document_id: str) -> dict:
    """Process a document through the full ingestion pipeline.

    Steps:
    1. Fetch from MinIO
    2. Extract text (with OCR if needed)
    3. DLP scan
    4. Classify sensitivity
    5. Chunk text
    6. Generate embeddings
    7. Store in Qdrant
    8. Update PostgreSQL
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from src.core.config import settings
    from src.models.document import Document, DocumentChunk

    engine = create_engine(settings.database_url_sync)

    try:
        with Session(engine) as db:
            doc = db.get(Document, uuid.UUID(document_id))
            if not doc:
                logger.error("document_not_found", document_id=document_id)
                return {"status": "error", "reason": "not_found"}

            doc.status = "processing"
            db.commit()

            # 1. Fetch from MinIO
            from minio import Minio

            mc = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_root_user,
                secret_key=settings.minio_root_password,
                secure=settings.minio_use_ssl,
            )
            response = mc.get_object(doc.minio_bucket, doc.minio_key)
            file_content = response.read()
            response.close()
            response.release_conn()

            # 2. Extract text
            text = _extract_text(file_content, doc.filename, doc.mime_type)
            if not text.strip():
                doc.status = "failed"
                doc.error_message = "No text extracted"
                db.commit()
                return {"status": "failed", "reason": "no_text"}

            # 3. DLP scan
            from src.security.sensitivity_classifier import classify_document

            sensitivity, findings = classify_document(text, doc.filename)
            doc.sensitivity = sensitivity

            logger.info(
                "dlp_scan_complete",
                document_id=document_id,
                sensitivity=sensitivity,
                findings_count=len(findings),
            )

            # 4. Chunk text
            from src.core.chunker import chunk_text, estimate_tokens

            chunks = chunk_text(text)

            # 5. Generate embeddings
            from src.providers.router import get_embedding_provider

            embedding_provider = get_embedding_provider()

            # Batch embed (max 50 at a time)
            all_embeddings = []
            batch_size = 50
            import asyncio

            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(embedding_provider.embed(batch))
                loop.close()
                all_embeddings.extend(result.embeddings)

            # 6. Store in Qdrant
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, PointStruct, VectorParams

            qc = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key or None,
                https=False,
            )

            collection_name = f"tenant_{doc.tenant_id}"
            # Ensure collection exists
            try:
                qc.get_collection(collection_name)
            except Exception:
                dims = len(all_embeddings[0]) if all_embeddings else 768
                qc.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=dims, distance=Distance.COSINE),
                )

            points = []
            db_chunks = []
            for idx, (chunk_text_content, embedding) in enumerate(zip(chunks, all_embeddings)):
                point_id = str(uuid.uuid4())
                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "tenant_id": str(doc.tenant_id),
                        "document_id": str(doc.id),
                        "filename": doc.filename,
                        "chunk_index": idx,
                        "content": chunk_text_content,
                        "sensitivity": sensitivity,
                    },
                ))
                db_chunks.append(DocumentChunk(
                    document_id=doc.id,
                    tenant_id=doc.tenant_id,
                    chunk_index=idx,
                    content=chunk_text_content,
                    token_count=estimate_tokens(chunk_text_content),
                    qdrant_point_id=uuid.UUID(point_id),
                ))

            if points:
                qc.upsert(collection_name=collection_name, points=points)

            # 7. Update PostgreSQL
            for chunk in db_chunks:
                db.add(chunk)
            doc.chunk_count = len(chunks)
            doc.status = "indexed"
            doc.error_message = None
            db.commit()

            logger.info(
                "document_indexed",
                document_id=document_id,
                chunks=len(chunks),
                sensitivity=sensitivity,
            )
            return {"status": "indexed", "chunks": len(chunks)}

    except Exception as e:
        logger.exception("ingestion_failed", document_id=document_id)
        try:
            with Session(engine) as db:
                doc = db.get(Document, uuid.UUID(document_id))
                if doc:
                    doc.status = "failed"
                    doc.error_message = str(e)[:1000]
                    db.commit()
        except Exception:
            pass
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


def _extract_text(content: bytes, filename: str, mime_type: str | None) -> str:
    """Extract text from document content based on file type."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in ("txt", "md", "rst", "csv", "tsv", "json", "yaml", "yml", "xml"):
        return content.decode("utf-8", errors="replace")

    try:
        from unstructured.partition.auto import partition

        elements = partition(file=io.BytesIO(content), metadata_filename=filename)
        return "\n\n".join(str(el) for el in elements)
    except Exception as e:
        logger.warning("unstructured_fallback", error=str(e), filename=filename)
        return content.decode("utf-8", errors="replace")


@shared_task(name="src.worker.tasks.ingestion.cleanup_deleted_documents")
def cleanup_deleted_documents() -> dict:
    """Permanently delete documents that have been soft-deleted for 30+ days."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from src.models.document import Document

    engine = create_engine(settings.database_url_sync)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    count = 0

    with Session(engine) as db:
        docs = db.query(Document).filter(
            Document.deleted_at.isnot(None),
            Document.deleted_at < cutoff,
        ).all()

        for doc in docs:
            # TODO: Delete from Qdrant and MinIO too
            db.delete(doc)
            count += 1

        db.commit()

    logger.info("cleanup_complete", deleted_count=count)
    return {"deleted": count}
