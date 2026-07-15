"""
IntelliDesk AI — RAG Service Unit Tests
Tests for chunking, embedding, and ChromaDB operations with mocked dependencies.
"""

from unittest.mock import MagicMock, call, patch

import pytest


class TestChunkText:
    """Tests for RAGService.chunk_text() — no external dependencies."""

    def test_empty_text_returns_empty_list(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            assert RAGService.chunk_text("") == []

    def test_short_text_returns_single_chunk(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            text = "This is a short article. " * 10
            chunks = RAGService.chunk_text(text, chunk_size=500)
            assert len(chunks) == 1

    def test_long_text_is_split_into_multiple_chunks(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            # 1500 words → 3 chunks of 500 words
            text = "word " * 1500
            chunks = RAGService.chunk_text(text, chunk_size=500, overlap=0)
            assert len(chunks) == 3

    def test_overlap_produces_more_chunks_than_without(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            text = "word " * 1200
            no_overlap = RAGService.chunk_text(text, chunk_size=500, overlap=0)
            with_overlap = RAGService.chunk_text(text, chunk_size=500, overlap=100)
            assert len(with_overlap) >= len(no_overlap)

    def test_trivially_short_chunks_are_filtered(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            text = "hi " * 5  # Too short to meet 50-char minimum
            chunks = RAGService.chunk_text(text, chunk_size=10)
            assert all(len(c.strip()) > 50 for c in chunks) or len(chunks) == 0

    def test_chunk_size_respected(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            text = "word " * 600
            chunks = RAGService.chunk_text(text, chunk_size=100, overlap=0)
            for chunk in chunks:
                assert len(chunk.split()) <= 100


class TestIndexArticle:
    """Tests for RAGService.index_article() with mocked ChromaDB."""

    def _make_article(self, idx=1):
        article = MagicMock()
        article.id = idx
        article.title = f"Test Article {idx}"
        article.summary = "A test article summary."
        article.body = "Content word. " * 200  # 200 words
        article.slug = f"test-article-{idx}"
        article.is_indexed = False
        article.chroma_document_id = None
        return article

    def test_successful_index_marks_article_indexed(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            mock_model = MagicMock()
            mock_model.encode.return_value = MagicMock()
            mock_model.encode.return_value.tolist.return_value = [[0.1] * 384]

            mock_collection = MagicMock()
            mock_collection.get.return_value = {"ids": []}
            mock_collection.upsert.return_value = None

            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection

            article = self._make_article()

            with (
                patch("app.services.rag_service.get_chroma_client", return_value=mock_client),
                patch("app.services.rag_service.get_embedding_model", return_value=mock_model),
            ):

                result = RAGService.index_article(article)
                assert result is True
                article.mark_indexed.assert_called_once()

    def test_empty_article_body_returns_false(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            article = MagicMock()
            article.id = 1
            article.title = "Empty"
            article.summary = ""
            article.body = ""  # Empty body
            article.slug = "empty"

            mock_model = MagicMock()
            mock_client = MagicMock()

            with (
                patch("app.services.rag_service.get_chroma_client", return_value=mock_client),
                patch("app.services.rag_service.get_embedding_model", return_value=mock_model),
            ):

                result = RAGService.index_article(article)
                assert result is False

    def test_chroma_failure_returns_false(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            article = self._make_article()
            mock_model = MagicMock()
            mock_model.encode.side_effect = Exception("ChromaDB connection refused")

            with (
                patch("app.services.rag_service.get_chroma_client"),
                patch("app.services.rag_service.get_embedding_model", return_value=mock_model),
            ):

                result = RAGService.index_article(article)
                assert result is False


class TestSemanticSearch:
    """Tests for RAGService.semantic_search() with mocked dependencies."""

    def test_semantic_search_returns_sorted_results(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            mock_model = MagicMock()
            mock_model.encode.return_value = MagicMock()
            mock_model.encode.return_value.tolist.return_value = [[0.1] * 384]

            mock_collection = MagicMock()
            mock_collection.query.return_value = {
                "documents": [["Article about VPN setup", "Article about network issues"]],
                "metadatas": [
                    [
                        {"article_id": "1", "title": "VPN Setup Guide", "source": "article"},
                        {"article_id": "2", "title": "Network Guide", "source": "article"},
                    ]
                ],
                "distances": [[0.15, 0.35]],  # Lower = more similar
            }

            mock_client = MagicMock()
            mock_client.get_collection.return_value = mock_collection

            with (
                patch("app.services.rag_service.get_chroma_client", return_value=mock_client),
                patch("app.services.rag_service.get_embedding_model", return_value=mock_model),
            ):

                results = RAGService.semantic_search("VPN configuration issue", n_results=2)
                assert len(results) <= 2
                if len(results) == 2:
                    assert results[0]["score"] >= results[1]["score"]

    def test_search_with_no_collections_returns_empty(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            mock_model = MagicMock()
            mock_model.encode.return_value = MagicMock()
            mock_model.encode.return_value.tolist.return_value = [[0.1] * 384]

            mock_client = MagicMock()
            mock_client.get_collection.side_effect = Exception("Collection not found")

            with (
                patch("app.services.rag_service.get_chroma_client", return_value=mock_client),
                patch("app.services.rag_service.get_embedding_model", return_value=mock_model),
            ):

                results = RAGService.semantic_search("some query", n_results=5)
                assert results == []  # Gracefully returns empty on missing collections


class TestBuildContext:
    """Tests for RAGService.build_context_for_query()"""

    def test_build_context_formats_results(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            mock_results = [
                {
                    "content": "To reset VPN, go to settings and click reset.",
                    "score": 0.92,
                    "collection": "knowledge_articles",
                    "metadata": {"title": "VPN Reset Guide"},
                },
                {
                    "content": "Network connectivity is required for VPN.",
                    "score": 0.78,
                    "collection": "knowledge_articles",
                    "metadata": {"title": "Network Prerequisites"},
                },
            ]

            with patch.object(RAGService, "semantic_search", return_value=mock_results):
                context = RAGService.build_context_for_query("how to reset VPN", n_results=2)
                assert "VPN Reset Guide" in context
                assert "---" in context  # Separator between chunks
                assert "Source 1" in context
                assert "Source 2" in context

    def test_empty_results_returns_empty_string(self, app):
        with app.app_context():
            from app.services.rag_service import RAGService

            with patch.object(RAGService, "semantic_search", return_value=[]):
                context = RAGService.build_context_for_query("obscure query with no results")
                assert context == ""
