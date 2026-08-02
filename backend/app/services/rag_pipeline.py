"""
RAG (Retrieval-Augmented Generation) Pipeline Service
======================================================

This module implements the knowledge base for BotForge bots. RAG is a technique
where, instead of relying solely on the LLM's built-in knowledge, we:

1. **Ingest** documents (PDFs, text files, etc.) by splitting them into small
   chunks, converting each chunk into a numerical vector (embedding), and storing
   those vectors in a vector database (ChromaDB).

2. **Query** the knowledge base by converting the user's question into a vector,
   then finding the most similar document chunks using cosine similarity. These
   relevant chunks are then passed to the LLM as context so it can answer
   accurately based on the bot owner's actual documents.

Why it exists:
- Each bot in BotForge has its own knowledge base. A restaurant bot knows about
  its menu; a tech support bot knows about its product docs. RAG makes this
  possible without fine-tuning the LLM.

How it fits in the architecture:
- **ai_engine.py** calls `rag.query()` during message processing to find relevant
  context before generating an answer.
- **Document upload endpoints** call `rag.ingest_document()` when a bot owner
  uploads a new document.
- **Document management endpoints** call `rag.delete_document()` and
  `rag.reindex_all()` for cleanup.

Key technologies:
- **ChromaDB**: An open-source vector database that stores embeddings and
  supports fast similarity search.
- **sentence-transformers**: A library for generating text embeddings locally.
  We use the "all-MiniLM-L6-v2" model (384-dimensional vectors, good balance
  of speed and quality).
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.utils.text_splitter import split_text
from app.utils.file_parser import parse_file

# ---------------------------------------------------------------------------
# Lazy-loaded singletons
# ---------------------------------------------------------------------------
# We use module-level singletons so that the ChromaDB client and the embedding
# model are created only once and reused across all requests. Loading the
# embedding model into memory takes a few seconds, so we don't want to do it
# on every request.

_chroma_client = None
_embedding_model: SentenceTransformer | None = None


def get_chroma_client():
    """
    Get or create the ChromaDB client singleton.

    Two modes, selected by `chroma_mode` in settings:
      - "embedded" (default): a PersistentClient that runs in-process and stores
        vectors on disk at `chroma_persist_dir`. No separate server required —
        this is what makes local dev work out of the box.
      - "http": an HttpClient that connects to a standalone ChromaDB server at
        `chroma_host:chroma_port`. Use this in production / multi-node setups
        where you run `chroma run` as its own service.

    Returns:
        A ChromaDB client (PersistentClient or HttpClient) cached for reuse.
    """
    global _chroma_client
    if _chroma_client is None:
        settings = get_settings()
        if settings.chroma_mode == "http":
            _chroma_client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        else:
            _chroma_client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
    return _chroma_client


def get_embedding_model() -> SentenceTransformer:
    """
    Get or create the sentence-transformers embedding model singleton.

    The model "all-MiniLM-L6-v2" is loaded into memory once and reused.
    It converts text into 384-dimensional vectors that capture semantic meaning.
    This runs entirely locally -- no external API calls needed.

    Returns:
        A SentenceTransformer model ready to encode text.
    """
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(get_settings().embedding_model)
    return _embedding_model


class RAGPipeline:
    """
    RAG pipeline: embed, search, and retrieve from ChromaDB.

    Each bot gets its own ChromaDB collection (named "bot_{bot_id}"), so
    documents from different bots are completely isolated. This class provides
    methods to:
    - Ingest documents (split, embed, store)
    - Query the knowledge base (embed question, find similar chunks)
    - Delete documents and reindex

    Attributes:
        chroma: The ChromaDB client for storing/retrieving vectors.
        model: The sentence-transformers model for generating embeddings.
    """

    def __init__(self):
        """Initialize the pipeline with shared ChromaDB client and embedding model."""
        self.chroma = get_chroma_client()
        self.model = get_embedding_model()

    def _get_collection(self, bot_id: str):
        """
        Get or create the ChromaDB collection for a specific bot.

        Each bot has its own isolated collection named "bot_{bot_id}". The
        collection uses cosine similarity as the distance metric, which works
        well for comparing text embeddings (higher similarity = more relevant).

        Args:
            bot_id: The unique identifier of the bot.

        Returns:
            A ChromaDB Collection object for this bot's knowledge base.
        """
        return self.chroma.get_or_create_collection(
            name=f"bot_{bot_id}",
            metadata={"hnsw:space": "cosine"},  # Use cosine distance for similarity
        )

    # -------------------------------------------------------------------------
    # Document ingestion
    # -------------------------------------------------------------------------

    async def ingest_document(
        self, bot_id: str, file_path: str, file_type: str, doc_id: str
    ) -> int:
        """
        Read a file, split it into chunks, embed each chunk, and store in ChromaDB.

        This is called when a bot owner uploads a document to their knowledge base.
        The document goes through this pipeline:

        Step 1: Parse the file into raw text (handled by file_parser utility).
                Supports PDF, TXT, DOCX, CSV, and other formats.
        Step 2: Split the text into smaller chunks (handled by text_splitter utility).
                Chunks are typically ~500 tokens each with some overlap so that
                context isn't lost at chunk boundaries.
        Step 3: For each chunk, generate a vector embedding using the local model.
        Step 4: Store all chunks + embeddings + metadata in ChromaDB.

        Args:
            bot_id: The bot this document belongs to.
            file_path: Path to the uploaded file on disk.
            file_type: The MIME type or extension (e.g., "pdf", "text/plain").
            doc_id: A unique identifier for this document (used for later deletion).

        Returns:
            The number of chunks created and stored. Returns 0 if the file was
            empty or could not be parsed.
        """
        # Step 1: Parse file to text
        text = parse_file(file_path, file_type)
        if not text.strip():
            return 0

        # Step 2: Split text into manageable chunks
        chunks = split_text(text)
        collection = self._get_collection(bot_id)

        # Step 3 & 4: Embed each chunk and prepare batch for ChromaDB
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            # Each chunk gets a unique ID combining the document ID and chunk index
            chunk_id = f"{doc_id}_chunk_{i}"
            # Generate the vector embedding for this chunk (runs locally)
            embedding = self.model.encode(chunk).tolist()

            ids.append(chunk_id)
            documents.append(chunk)
            embeddings.append(embedding)
            metadatas.append({
                "doc_id": doc_id,       # Which document this chunk came from
                "chunk_index": i,       # Position within the document
                "bot_id": bot_id,       # Which bot owns this document
            })

        # Batch insert all chunks into ChromaDB at once (more efficient than one-by-one)
        if ids:
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

        return len(chunks)

    # -------------------------------------------------------------------------
    # Knowledge base querying
    # -------------------------------------------------------------------------

    async def query(self, bot_id: str, question: str, top_k: int = 5) -> list[dict]:
        """
        Embed a question and search the bot's knowledge base for relevant chunks.

        This is the "retrieval" part of RAG. When a customer asks a question,
        we convert it to a vector and find the most similar document chunks
        in ChromaDB. Those chunks are then passed to the LLM as context.

        Data flow:
        1. Get the bot's ChromaDB collection.
        2. If the collection is empty, return no results (the bot has no documents).
        3. Encode the question into a vector using the same embedding model.
        4. Query ChromaDB for the top_k most similar chunks (by cosine distance).
        5. Format the results into a list of dicts with content, metadata, and
           distance (similarity score).

        Args:
            bot_id: The bot whose knowledge base to search.
            question: The customer's question or message text.
            top_k: Maximum number of chunks to return (default 5).

        Returns:
            A list of dicts, each containing:
            - "content": The text of the chunk.
            - "metadata": Info about the chunk (doc_id, chunk_index, bot_id).
            - "distance": How far this chunk is from the query vector (lower = more similar).
        """
        collection = self._get_collection(bot_id)

        # If the bot has no documents yet, return empty results
        if collection.count() == 0:
            return []

        # Encode the question using the same model that was used to embed the documents
        query_embedding = self.model.encode(question).tolist()

        # Search ChromaDB for the most similar chunks
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),  # Don't request more than exist
            include=["documents", "metadatas", "distances"],
        )

        # Format results into a clean list of dicts
        chunks = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                chunks.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                })

        return chunks

    # -------------------------------------------------------------------------
    # Document management
    # -------------------------------------------------------------------------

    async def delete_document(self, bot_id: str, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a specific document from ChromaDB.

        When a bot owner deletes a document from their knowledge base, we need
        to remove all the chunks that were created from it. ChromaDB supports
        filtering by metadata, so we delete all entries where doc_id matches.

        Args:
            bot_id: The bot whose collection to modify.
            doc_id: The document ID whose chunks should be removed.

        Returns:
            True if the operation completed (ChromaDB doesn't report individual
            deletion counts).
        """
        collection = self._get_collection(bot_id)
        collection.delete(where={"doc_id": doc_id})
        return True

    async def reindex_all(self, bot_id: str) -> int:
        """
        Delete the entire collection for a bot, effectively wiping the knowledge base.

        This is used when a full reindex is needed. After calling this, the caller
        should re-ingest all documents for the bot. The method returns 0 to indicate
        that zero chunks remain.

        Args:
            bot_id: The bot whose collection to delete.

        Returns:
            0, indicating the collection is now empty. The caller is responsible
            for re-ingesting all documents.
        """
        try:
            self.chroma.delete_collection(f"bot_{bot_id}")
        except Exception:
            pass  # Collection might not exist, which is fine
        return 0
