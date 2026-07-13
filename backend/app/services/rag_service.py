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
    """Get ChromaDB HTTP client connected to the configured server."""
    import chromadb
    host = current_app.config.get("CHROMA_HOST", "localhost")
    port = current_app.config.get("CHROMA_PORT", 8001)
    return chromadb.HttpClient(host=host, port=int(port))


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

            # Delete old entries if re-indexing
            try:
                existing_ids = [
                    doc["id"] for doc in
                    collection.get(where={"article_id": str(article.id)})["ids"]
                ]
                if existing_ids:
                    collection.delete(ids=existing_ids)
            except Exception:
                pass  # No existing entries

            collection.upsert(
                ids=chroma_ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=[{
                    "article_id": str(article.id),
                    "title": article.title,
                    "slug": article.slug,
                    "chunk_index": str(i),
                    "source": "article",
                } for i in range(len(chunks))],
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
            return True
        except Exception as e:
            logger.error(f"Failed to remove article {article_id} from index: {e}")
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

            embeddings = model.encode(chunks, normalize_embeddings=True).tolist()
            chroma_ids = [f"doc_{document.id}_chunk_{i}" for i in range(len(chunks))]

            collection.upsert(
                ids=chroma_ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=[{
                    "document_id": str(document.id),
                    "file_name": document.file_name,
                    "chunk_index": str(i),
                    "source": "document",
                } for i in range(len(chunks))],
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
                    query_kwargs = {
                        "query_embeddings": [query_embedding],
                        "n_results": n_results,
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
                        all_results.append({
                            "content": doc,
                            "metadata": meta,
                            "score": round(1 - dist, 4),  # Cosine similarity (0-1, higher=better)
                            "collection": coll_name,
                        })

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
                f"[Source {i+1}: {source_label} (score: {result['score']})]\n{result['content']}"
            )

        return "\n\n---\n\n".join(context_parts)
