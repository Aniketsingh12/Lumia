"""
Knowledge Base Router
======================

This router manages the knowledge base for each bot. The knowledge base is the
collection of documents and URLs that the bot uses to answer customer questions
via Retrieval-Augmented Generation (RAG).

RAG Overview:
    When a customer asks a question, the AI engine searches the bot's knowledge base
    for relevant text chunks, then uses those chunks as context when generating an answer.
    This allows the bot to give accurate, source-backed responses based on your documents.

Endpoints provided:
    GET    /{bot_id}/docs           - List all documents in a bot's knowledge base
    POST   /{bot_id}/docs/upload    - Upload a file (PDF, DOCX, TXT, CSV) to the knowledge base
    POST   /{bot_id}/docs/url       - Ingest a web URL into the knowledge base
    DELETE /{bot_id}/docs/{doc_id}  - Delete a specific document and its vector embeddings
    POST   /{bot_id}/docs/reindex   - Re-process and re-index all documents for a bot
    GET    /{bot_id}/docs/chunks    - Preview the text chunks stored in the vector database

All endpoints require authentication.

Document Processing Flow:
    1. User uploads a file or submits a URL via the API.
    2. A database record is created with status "processing".
    3. A background task (Celery) is triggered to:
       a. Parse the document (extract text from PDF, DOCX, etc.)
       b. Split the text into overlapping chunks
       c. Generate vector embeddings for each chunk
       d. Store the embeddings in ChromaDB (vector database)
       e. Update the database record with chunk count and status "ready"
    4. The bot can now use these chunks when answering questions.
"""

import uuid
import tempfile
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends

from app.database import get_supabase
from app.models.knowledge import DocResponse, URLIngest
from app.middleware.auth import get_current_user

# Create the router instance. Mounted with prefix like "/api/knowledge".
router = APIRouter()


def _verify_bot_ownership(db, bot_id: str, org_id: str):
    """Raise 404 if bot does not exist or belongs to a different org."""
    bot = db.table("bots").select("id").eq("id", bot_id).eq("org_id", org_id).execute()
    if not bot.data:
        raise HTTPException(status_code=404, detail="Bot not found")


@router.get("/{bot_id}/docs", response_model=list[DocResponse])
async def list_docs(bot_id: str, current_user: dict = Depends(get_current_user)):
    """
    List all documents in a bot's knowledge base.

    HTTP Method: GET
    URL: /{bot_id}/docs
    Auth Required: Yes

    Path Parameters:
        - bot_id (str): The UUID of the bot whose documents to list

    Request Flow:
        1. Verify the bot belongs to the current user's organization.
        2. Query the "knowledge_docs" table for all rows matching the given bot_id.
        3. Return the list (may be empty if no documents have been uploaded yet).

    Response: List of DocResponse objects, each containing:
        - id, bot_id, filename, file_type, status ("processing", "ready", "error")
        - chunk_count, total_tokens, uploaded_at
    """
    db = get_supabase()
    _verify_bot_ownership(db, bot_id, current_user["org_id"])
    result = db.table("knowledge_docs").select("*").eq("bot_id", bot_id).execute()
    return result.data or []


@router.post("/{bot_id}/docs/upload", response_model=DocResponse)
async def upload_doc(
    bot_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a document file to a bot's knowledge base.

    HTTP Method: POST
    URL: /{bot_id}/docs/upload
    Auth Required: Yes
    Content-Type: multipart/form-data

    Path Parameters:
        - bot_id (str): The UUID of the bot to add the document to

    Request Body:
        - file (UploadFile): The document file to upload. Supported formats:
          PDF (.pdf), Word (.docx), Plain Text (.txt), CSV (.csv)

    Request Flow:
        1. Validate the uploaded file's MIME type against the allowed types list.
           If the MIME type is not recognized, fall back to checking the file extension.
           If neither matches, return HTTP 400 "Unsupported file type".
        2. Generate a unique document ID (UUID).
        3. Read the file content into memory and save it to a temporary directory.
           The temp file is needed so the background worker can access it later.
        4. Create a "knowledge_docs" database record with status "processing".
           This lets the frontend show the document as "processing" immediately.
        5. Trigger the background Celery task (process_document) which will:
           - Parse the file and extract text
           - Split text into chunks
           - Generate embeddings and store them in ChromaDB
           - Update the database record status to "ready"
        6. Return the document record immediately (processing continues in background).

    Response: DocResponse with the document metadata (status will be "processing").

    Error Responses:
        - 400: Unsupported file type
    """
    db = get_supabase()
    _verify_bot_ownership(db, bot_id, current_user["org_id"])

    # Validate file type by MIME type first, then fall back to file extension
    allowed_types = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
        "text/csv": "csv",
    }
    file_type = allowed_types.get(file.content_type)
    if not file_type:
        # Try by extension as a fallback (some clients may not set MIME type correctly)
        ext = os.path.splitext(file.filename or "")[1].lower().lstrip(".")
        if ext in ("pdf", "docx", "txt", "csv"):
            file_type = ext
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

    # Save file to a temporary directory so the background worker can access it
    doc_id = str(uuid.uuid4())
    content = await file.read()

    tmp_dir = tempfile.mkdtemp()
    file_path = os.path.join(tmp_dir, file.filename or f"doc.{file_type}")
    with open(file_path, "wb") as f:
        f.write(content)

    # Create the document record in the database with "processing" status
    doc_data = {
        "id": doc_id,
        "bot_id": bot_id,
        "filename": file.filename,
        "file_type": file_type,
        "status": "processing",
        "chunk_count": 0,
        "total_tokens": 0,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    result = db.table("knowledge_docs").insert(doc_data).execute()

    # Trigger the Celery background task to parse, chunk, embed, and index the document.
    # The .delay() method sends the task to the Celery worker queue asynchronously.
    from app.tasks.document_tasks import process_document

    process_document.delay(bot_id, doc_id, file_path, file_type)

    return result.data[0]


@router.post("/{bot_id}/docs/url", response_model=DocResponse)
async def ingest_url(
    bot_id: str,
    url_data: URLIngest,
    current_user: dict = Depends(get_current_user),
):
    """
    Ingest a web URL into a bot's knowledge base.

    HTTP Method: POST
    URL: /{bot_id}/docs/url
    Auth Required: Yes

    Path Parameters:
        - bot_id (str): The UUID of the bot to add the URL content to

    Request Body (URLIngest):
        - url (str): The web URL to scrape and ingest
        - name (str, optional): A friendly name for this document; defaults to the URL itself

    Request Flow:
        1. Generate a unique document ID.
        2. Create a "knowledge_docs" record with file_type "url" and status "processing".
        3. Trigger the background Celery task which will:
           - Fetch and scrape the web page content
           - Split the text into chunks
           - Generate embeddings and store them in ChromaDB
           - Update the database record to "ready"
        4. Return the document record immediately.

    Response: DocResponse with the document metadata (status will be "processing").
    """
    doc_id = str(uuid.uuid4())
    db = get_supabase()
    _verify_bot_ownership(db, bot_id, current_user["org_id"])

    doc_data = {
        "id": doc_id,
        "bot_id": bot_id,
        "filename": url_data.name or url_data.url,
        "file_url": url_data.url,
        "file_type": "url",
        "status": "processing",
        "chunk_count": 0,
        "total_tokens": 0,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    result = db.table("knowledge_docs").insert(doc_data).execute()

    # Trigger background processing for the URL (same task as file upload, different type)
    from app.tasks.document_tasks import process_document

    process_document.delay(bot_id, doc_id, url_data.url, "url")

    return result.data[0]


@router.delete("/{bot_id}/docs/{doc_id}")
async def delete_doc(bot_id: str, doc_id: str, current_user: dict = Depends(get_current_user)):
    """
    Delete a document from the knowledge base.

    HTTP Method: DELETE
    URL: /{bot_id}/docs/{doc_id}
    Auth Required: Yes

    Path Parameters:
        - bot_id (str): The UUID of the bot
        - doc_id (str): The UUID of the document to delete

    Request Flow:
        1. Verify the bot belongs to the current user's organization.
        2. Delete the document's vector embeddings from ChromaDB using the RAG pipeline.
        3. Delete the document record from the "knowledge_docs" database table.
        4. Return a confirmation message.

    Response: {"message": "Document deleted"}
    """
    db = get_supabase()
    _verify_bot_ownership(db, bot_id, current_user["org_id"])

    # Delete vector embeddings from ChromaDB (the vector database used for RAG)
    from app.services.rag_pipeline import RAGPipeline

    rag = RAGPipeline()
    await rag.delete_document(bot_id, doc_id)

    # Delete the metadata record from the relational database
    db.table("knowledge_docs").delete().eq("id", doc_id).execute()
    return {"message": "Document deleted"}


@router.post("/{bot_id}/docs/reindex")
async def reindex_docs(bot_id: str, current_user: dict = Depends(get_current_user)):
    """
    Re-index all documents for a bot.

    HTTP Method: POST
    URL: /{bot_id}/docs/reindex
    Auth Required: Yes

    Path Parameters:
        - bot_id (str): The UUID of the bot to reindex

    Request Flow:
        1. Trigger a Celery background task that will re-process all documents
           associated with this bot: re-parse, re-chunk, re-embed, and rebuild
           the ChromaDB collection.
        2. Return immediately with a confirmation that reindexing has started.

    Use Cases:
        - After changing chunking parameters or embedding models
        - If the vector database becomes corrupted or out of sync
        - To rebuild embeddings after an upgrade

    Response: {"message": "Reindexing started"}
    """
    db = get_supabase()
    _verify_bot_ownership(db, bot_id, current_user["org_id"])

    from app.tasks.document_tasks import reindex_bot

    reindex_bot.delay(bot_id)
    return {"message": "Reindexing started"}


@router.get("/{bot_id}/docs/chunks")
async def get_chunks(bot_id: str, current_user: dict = Depends(get_current_user)):
    """
    Preview the text chunks stored in the vector database for a bot.

    HTTP Method: GET
    URL: /{bot_id}/docs/chunks
    Auth Required: Yes

    Path Parameters:
        - bot_id (str): The UUID of the bot

    Request Flow:
        1. Access the bot's ChromaDB collection via the RAG pipeline.
        2. Get the total count of chunks in the collection.
        3. Peek at the first 50 chunks (ChromaDB's peek returns a sample).
        4. Return the total count and a preview of each chunk (truncated to 200 chars).

    This endpoint is useful for debugging and verifying that documents have been
    correctly processed and indexed. It helps answer questions like:
        - "Were my documents chunked correctly?"
        - "How many chunks does this bot have?"
        - "What does the indexed content look like?"

    Response:
        - total_chunks (int): Total number of text chunks in the vector database
        - sample_chunks (list): Up to 50 sample chunks, each with:
          - id (str): The chunk's unique identifier
          - content (str): First 200 characters of the chunk text
    """
    db = get_supabase()
    _verify_bot_ownership(db, bot_id, current_user["org_id"])

    from app.services.rag_pipeline import RAGPipeline

    rag = RAGPipeline()
    collection = rag._get_collection(bot_id)
    count = collection.count()
    results = collection.peek(limit=50)

    return {
        "total_chunks": count,
        "sample_chunks": [
            {"id": results["ids"][i], "content": results["documents"][i][:200]}
            for i in range(len(results["ids"]))
        ] if results["ids"] else [],
    }
