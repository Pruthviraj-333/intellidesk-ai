"""
IntelliDesk AI — RAG Service (Retrieval-Augmented Generation)
Manages embedding, indexing, and semantic search via ChromaDB + SentenceTransformers.
Provider-agnostic design — AI provider abstracted via Strategy pattern.
"""

import uuid
from typing import Optional

from flask import current_app

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Embedding model singleton — loaded once per process to avoid cold-start delay
_embedding_model = None

# ChromaDB client singleton — one persistent HTTP connection per process
_chroma_client = None


def get_embedding_model():
    """
    Lazy-load the SentenceTransformer embedding model.
    Singleton per process — model stays in memory after first load.
    """
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        model_name = current_app.config.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        logger.info(f"Loading embedding model: {model_name}")
        _embedding_model = SentenceTransformer(model_name)
        logger.info("Embedding model loaded successfully.")
    return _embedding_model


def get_chroma_client():
    """
    Get (or create) singleton ChromaDB HTTP client.

    Validates the existing connection with a lightweight heartbeat before
    returning it. If the heartbeat fails (e.g. ChromaDB restarted, socket
    dropped), the stale client is discarded and a fresh connection is made.
    This prevents the singleton from silently failing for the entire lifetime
    of a Flask or Celery worker process after a ChromaDB reconnect.
    """
    global _chroma_client

    # Validate existing connection — heartbeat is a ~1 ms no-op on the server
    if _chroma_client is not None:
        try:
            _chroma_client.heartbeat()
        except Exception:
            logger.warning("ChromaDB connection lost — resetting client for reconnect.")
            _chroma_client = None

    if _chroma_client is None:
        import chromadb

        host = current_app.config.get("CHROMA_HOST", "localhost")
        port = current_app.config.get("CHROMA_PORT", 8001)
        _chroma_client = chromadb.HttpClient(host=host, port=int(port))
        logger.info(f"ChromaDB client connected: {host}:{port}")

    return _chroma_client


class RAGService:
    """
    Core RAG service — handles all vector database operations.
    Supports indexing articles, documents, and performing semantic search.
    """

    ARTICLE_COLLECTION = "knowledge_articles"
    DOCUMENT_COLLECTION = "knowledge_documents"

    # ─── Text Chunking ─────────────────────────────────────────────────────────

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> list[str]:
        """
        Split text into overlapping chunks for embedding.

        Args:
            text: Raw text to chunk.
            chunk_size: Target words per chunk.
            overlap: Word overlap between adjacent chunks (context preservation).

        Returns:
            List of text chunk strings.
        """
        words = text.split()
        if not words:
            return []

        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            if end == len(words):
                break
            start = end - overlap

        return [c for c in chunks if len(c.strip()) > 50]  # Skip trivially short chunks

    # ─── Article Indexing ──────────────────────────────────────────────────────

    @staticmethod
    def index_article(article) -> bool:
        """
        Embed and index a knowledge article in ChromaDB.

        Args:
            article: KnowledgeArticle model instance.

        Returns:
            True on success, False on failure.
        """
        try:
            client = get_chroma_client()
            model = get_embedding_model()
            model_name = current_app.config.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

            collection = client.get_or_create_collection(
                name=RAGService.ARTICLE_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )

            # Combine title, summary, and body for rich indexing
            full_text = f"{article.title}\n\n{article.summary or ''}\n\n{article.body}"
            chunks = RAGService.chunk_text(full_text)

            if not chunks:
                logger.warning(f"Article {article.id} produced no indexable chunks.")
                return False

            embeddings = model.encode(chunks, normalize_embeddings=True).tolist()
            chroma_ids = [f"article_{article.id}_chunk_{i}" for i in range(len(chunks))]

            # Delete old entries if re-indexing.
            # Uses a where-clause delete directly — avoids the TypeError caused by iterating
            # over the flat list[str] returned by collection.get(...)["ids"].
            # collection.delete(where=...) is a no-op when no matching records exist.
            try:
                collection.delete(where={"article_id": str(article.id)})
            except Exception:
                pass  # Collection empty on first index — safe to ignore

            collection.upsert(
                ids=chroma_ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=[
                    {
                        "article_id": str(article.id),
                        "title": article.title,
                        "slug": article.slug,
                        "chunk_index": str(i),
                        "source": "article",
                    }
                    for i in range(len(chunks))
                ],
            )

            # Mark article as indexed in DB
            article.mark_indexed(model_name, chroma_ids[0])
            logger.info(f"Article {article.id} indexed: {len(chunks)} chunks.")
            return True

        except Exception as e:
            logger.error(f"Failed to index article {article.id}: {e}")
            return False

    @staticmethod
    def remove_article_from_index(article_id: int) -> bool:
        """Remove all chunks for an article from ChromaDB."""
        try:
            client = get_chroma_client()
            collection = client.get_or_create_collection(RAGService.ARTICLE_COLLECTION)
            collection.delete(where={"article_id": str(article_id)})
            logger.info(f"Article {article_id} vectors purged from ChromaDB.")
            return True
        except Exception as e:
            logger.error(f"Failed to remove article {article_id} from index: {e}")
            return False

    @staticmethod
    def remove_document_from_index(document_id: int) -> bool:
        """Remove all chunk vectors for a document from ChromaDB.

        Called asynchronously via Celery when a document is deleted or
        re-queued for reprocessing, so stale vectors never surface in RAG retrieval.
        Safe to call multiple times — delete on a non-existent where-clause is a no-op.
        """
        try:
            client = get_chroma_client()
            collection = client.get_or_create_collection(RAGService.DOCUMENT_COLLECTION)
            collection.delete(where={"document_id": str(document_id)})
            logger.info(f"Document {document_id} vectors purged from ChromaDB.")
            return True
        except Exception as e:
            logger.error(f"Failed to purge document {document_id} vectors: {e}")
            return False


    # ─── Document Indexing ─────────────────────────────────────────────────────

    @staticmethod
    def index_document(document, chunks: list[str]) -> list[str]:
        """
        Embed and store document chunks in ChromaDB.

        Args:
            document: Document model instance.
            chunks: Pre-extracted text chunks from document parser.

        Returns:
            List of ChromaDB IDs for each chunk.
        """
        try:
            client = get_chroma_client()
            model = get_embedding_model()

            collection = client.get_or_create_collection(
                name=RAGService.DOCUMENT_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )

            # Purge any existing chunks for this document before re-indexing.
            # Guards against orphan vectors when index_document() is called directly
            # (e.g. admin scripts, tests) rather than via the Celery purge task.
            try:
                collection.delete(where={"document_id": str(document.id)})
            except Exception:
                pass  # No-op if collection is empty — safe to ignore

            embeddings = model.encode(chunks, normalize_embeddings=True).tolist()
            chroma_ids = [f"doc_{document.id}_chunk_{i}" for i in range(len(chunks))]

            collection.upsert(
                ids=chroma_ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=[
                    {
                        "document_id": str(document.id),
                        "file_name": document.file_name,
                        "chunk_index": str(i),
                        "source": "document",
                    }
                    for i in range(len(chunks))
                ],
            )

            logger.info(f"Document {document.id} indexed: {len(chunks)} chunks.")
            return chroma_ids

        except Exception as e:
            logger.error(f"Failed to index document {document.id}: {e}")
            return []

    # ─── Semantic Search ───────────────────────────────────────────────────────

    @staticmethod
    def semantic_search(
        query: str,
        n_results: int = 5,
        collections: Optional[list[str]] = None,
        filters: Optional[dict] = None,
    ) -> list[dict]:
        """
        Perform semantic similarity search across knowledge collections.

        Args:
            query: Natural language search query.
            n_results: Number of results to return per collection.
            collections: Which collections to search. Defaults to both.
            filters: Optional ChromaDB where-clause metadata filters.

        Returns:
            List of result dicts with content, metadata, and distance score.
        """
        try:
            client = get_chroma_client()
            model = get_embedding_model()
            query_embedding = model.encode([query], normalize_embeddings=True).tolist()[0]

            if collections is None:
                collections = [RAGService.ARTICLE_COLLECTION, RAGService.DOCUMENT_COLLECTION]

            all_results = []

            for coll_name in collections:
                try:
                    collection = client.get_collection(coll_name)

                    # Cap n_results to actual collection size.
                    # ChromaDB raises InvalidArgumentError if n_results > count(),
                    # which would silently swallow all results for that collection.
                    count = collection.count()
                    if count == 0:
                        continue
                    capped_n = min(n_results, count)

                    query_kwargs = {
                        "query_embeddings": [query_embedding],
                        "n_results": capped_n,
                        "include": ["documents", "metadatas", "distances"],
                    }
                    if filters:
                        query_kwargs["where"] = filters

                    results = collection.query(**query_kwargs)

                    for doc, meta, dist in zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0],
                    ):
                        all_results.append(
                            {
                                "content": doc,
                                "metadata": meta,
                                "score": round(
                                    1 - dist, 4
                                ),  # Cosine similarity (0-1, higher=better)
                                "collection": coll_name,
                            }
                        )

                except Exception:
                    # Collection may not exist yet (no documents indexed)
                    continue

            # Sort all results by score descending
            all_results.sort(key=lambda x: x["score"], reverse=True)
            return all_results[:n_results]

        except Exception as e:
            logger.error(f"Semantic search failed for query '{query}': {e}")
            return []

    # ─── RAG Context Building ──────────────────────────────────────────────────

    @staticmethod
    def build_context_for_query(query: str, n_results: int = 5) -> str:
        """
        Build a context string from top semantic search results.
        Used to augment LLM prompts in the AI assistant.

        Returns:
            Formatted context string for injection into LLM prompt.
        """
        results = RAGService.semantic_search(query=query, n_results=n_results)
        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results):
            meta = result["metadata"]
            source_label = meta.get("title") or meta.get("file_name") or "Knowledge Base"
            context_parts.append(
                f"[Source {i + 1}: {source_label} (score: {result['score']})]\n{result['content']}"
            )

        return "\n\n---\n\n".join(context_parts)
