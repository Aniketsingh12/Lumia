"""
Knowledge Models - Pydantic schemas for the document knowledge base system.

=== What are Pydantic models? ===
Pydantic models are Python classes that validate data automatically. When the
frontend sends a JSON request, Pydantic checks that all required fields exist
and have the correct types before the backend processes anything.

=== What this file defines ===
This file contains all schemas related to the knowledge base -- the system that
lets bot owners upload documents so the AI can answer questions based on their
content. The models cover:
  - DocUpload:      Metadata for a new document being uploaded
  - DocResponse:    Full document record including processing status
  - ChunkResponse:  A single text chunk extracted from a processed document
  - URLIngest:      A URL to scrape and add as knowledge

=== How the knowledge pipeline works ===
1. User uploads a file (PDF, DOCX, TXT, CSV) or submits a URL
2. Backend creates a document record with status="processing"
3. A background worker extracts text and splits it into "chunks" (small pieces)
4. Each chunk is converted to a vector embedding for semantic search
5. When done, the document status changes to "ready"
6. During chat, the AI searches chunks to find relevant context for answers

=== Relationship to the database ===
Two database tables are involved:
  - "documents": One row per uploaded file (tracked by DocResponse)
  - "chunks": Many rows per document, one per text chunk (tracked by ChunkResponse)
This is a one-to-many relationship: one document has many chunks.
"""

from pydantic import BaseModel
from datetime import datetime


class DocUpload(BaseModel):
    """
    Schema for the metadata sent when uploading a new document.

    Used by: POST /bots/{bot_id}/docs endpoint
    Sent by: The "Upload Document" form in the Knowledge Base tab

    Note: The actual file binary is sent as a multipart form upload, not in
    this model. This model carries just the metadata about the file. The
    backend receives both the file and this metadata together.
    """

    # The original name of the uploaded file (e.g., "product-guide.pdf").
    # Stored for display purposes so the user can identify their documents
    # in the knowledge base list.
    filename: str

    # The type/format of the file. Determines which parser the backend uses
    # to extract text content:
    #   - "pdf":  Uses a PDF parser (e.g., PyPDF2 or pdfplumber)
    #   - "docx": Uses python-docx to read Word documents
    #   - "txt":  Read directly as plain text
    #   - "csv":  Parsed row-by-row, each row becomes context
    #   - "url":  Not a file upload -- instead, the backend scrapes a webpage
    file_type: str  # pdf | docx | txt | csv | url

    # For URL-type documents, this is the web address to scrape.
    # For file uploads, this may be set by the backend after storing the file
    # in cloud storage (e.g., Supabase Storage), pointing to the stored file.
    # None when the file hasn't been stored yet.
    file_url: str | None = None


class DocResponse(BaseModel):
    """
    Schema for document data returned by the API.

    Used by: All endpoints that return document info (list, get, upload response)
    Sent to: The frontend Knowledge Base tab, which shows a list of documents
             with their processing status

    This model tracks the full lifecycle of a document from upload through
    processing to being ready for AI queries.
    """

    # Unique identifier for this document (UUID string from the database).
    id: str

    # The bot this document belongs to. Each document is associated with exactly
    # one bot -- this is how the AI knows which documents to search for a given bot.
    bot_id: str

    # The original filename, displayed in the document list UI.
    filename: str

    # The storage URL where the uploaded file can be accessed.
    # May be None if the file is still being uploaded or if it was a URL ingest.
    file_url: str | None = None

    # The file format (same values as DocUpload.file_type).
    # Shown as a badge/icon in the document list (e.g., a PDF icon).
    file_type: str

    # The current processing status of this document. The frontend uses this
    # to show a progress indicator or error state:
    #   - "uploading":   File is being transferred to storage
    #   - "processing":  Text extraction and chunking is in progress
    #   - "ready":       All chunks created and indexed, document is searchable
    #   - "error":       Something went wrong (see error_message for details)
    status: str = "processing"  # uploading | processing | ready | error

    # How many text chunks were created from this document. Gives the user
    # a sense of how much content was extracted. A 10-page PDF might produce
    # ~20-30 chunks depending on chunk size settings.
    chunk_count: int = 0

    # The total number of tokens (roughly words/subwords) across all chunks.
    # Useful for tracking usage against plan limits (e.g., "free plan allows
    # 100K tokens of knowledge base content").
    total_tokens: int = 0

    # If status is "error", this contains a human-readable description of what
    # went wrong (e.g., "PDF is password-protected", "Failed to fetch URL").
    # None when there is no error.
    error_message: str | None = None

    # When the document was originally uploaded. Shown in the document list
    # and used for sorting documents by recency.
    uploaded_at: datetime | None = None


class ChunkResponse(BaseModel):
    """
    Schema for a single text chunk from a processed document.

    Used by: Endpoints that return chunk-level detail (e.g., for debugging)
    Purpose: Represents one piece of a document after it has been split

    Documents are split into chunks because:
    1. AI models have limited context windows -- we can't feed an entire PDF
    2. Smaller chunks allow more precise semantic search
    3. We can show the user exactly which part of which document answered their question

    Typical chunk size is ~500-1000 tokens (roughly a paragraph or two).
    """

    # Unique identifier for this chunk (UUID string from the database).
    id: str

    # The document this chunk was extracted from. Links back to the "documents"
    # table, establishing the one-to-many relationship.
    doc_id: str

    # The actual text content of this chunk. This is what gets searched during
    # AI queries and what gets injected into the AI prompt as context.
    content: str

    # The position of this chunk within the document (0-indexed).
    # Chunk 0 is the first piece, chunk 1 is the second, and so on.
    # Used to maintain document order when displaying source references.
    chunk_index: int

    # Flexible key-value metadata about this chunk. Can include things like:
    #   - "page_number": which page of a PDF this came from
    #   - "heading": the section heading this text was under
    #   - "source_url": for URL-ingested documents, the original page URL
    # Using a dict keeps this flexible as we add new document types.
    metadata: dict = {}


class URLIngest(BaseModel):
    """
    Schema for adding a webpage URL to the knowledge base.

    Used by: POST /bots/{bot_id}/docs/url endpoint (or similar)
    Sent by: The "Add URL" input in the Knowledge Base tab

    Instead of uploading a file, users can paste a URL and the backend will
    scrape the webpage content, extract the text, and process it just like
    a file upload.
    """

    # The full URL to scrape (e.g., "https://docs.example.com/faq").
    # The backend fetches this URL, extracts readable text content
    # (stripping HTML tags, navigation, etc.), and processes it into chunks.
    url: str

    # Optional human-friendly name for this URL source. If provided, this is
    # shown in the document list instead of the raw URL. For example, the user
    # might name it "FAQ Page" instead of showing the full URL.
    # If None, the backend may use the page title or the URL itself as the name.
    name: str | None = None
