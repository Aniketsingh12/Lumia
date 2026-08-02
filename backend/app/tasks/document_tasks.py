import asyncio
from app.tasks.celery_app import celery_app
from app.database import get_supabase


@celery_app.task(bind=True, max_retries=3)
def process_document(self, bot_id: str, doc_id: str, file_path: str, file_type: str):
    """Background task: read file → chunk → embed → store in ChromaDB."""
    try:
        from app.services.rag_pipeline import RAGPipeline

        rag = RAGPipeline()
        db = get_supabase()

        # Update status to processing
        db.table("knowledge_docs").update({"status": "processing"}).eq("id", doc_id).execute()

        # Run the async ingest
        loop = asyncio.new_event_loop()
        chunk_count = loop.run_until_complete(
            rag.ingest_document(bot_id, file_path, file_type, doc_id)
        )
        loop.close()

        # Update doc record
        db.table("knowledge_docs").update({
            "status": "ready",
            "chunk_count": chunk_count,
        }).eq("id", doc_id).execute()

        # Update bot doc count
        docs = db.table("knowledge_docs").select("id", count="exact").eq("bot_id", bot_id).eq("status", "ready").execute()
        db.table("bots").update({"doc_count": docs.count or 0}).eq("id", bot_id).execute()

        return {"status": "success", "chunks": chunk_count}

    except Exception as exc:
        db = get_supabase()
        db.table("knowledge_docs").update({
            "status": "error",
            "error_message": str(exc),
        }).eq("id", doc_id).execute()

        raise self.retry(exc=exc, countdown=30)


@celery_app.task
def reindex_bot(bot_id: str):
    """Delete all vectors and re-process all documents for a bot."""
    from app.services.rag_pipeline import RAGPipeline

    rag = RAGPipeline()
    db = get_supabase()

    # Clear existing vectors
    loop = asyncio.new_event_loop()
    loop.run_until_complete(rag.reindex_all(bot_id))
    loop.close()

    # Get all docs for this bot
    docs = db.table("knowledge_docs").select("*").eq("bot_id", bot_id).execute()

    for doc in docs.data or []:
        process_document.delay(
            bot_id,
            doc["id"],
            doc.get("file_url", ""),
            doc.get("file_type", "txt"),
        )

    return {"status": "reindexing", "doc_count": len(docs.data or [])}
