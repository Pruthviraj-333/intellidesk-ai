"""
IntelliDesk AI — Document Repository
Data access for Document and DocumentChunk entities.
"""

from typing import Optional

from app.extensions import db
from app.models.document import Document, DocumentChunk
from app.utils.constants import DocumentStatus


class DocumentRepository:
    """Repository for Document and DocumentChunk entities."""

    @staticmethod
    def get_by_id(doc_id: int) -> Optional[Document]:
        return Document.query.filter_by(id=doc_id, deleted_at=None).first()

    @staticmethod
    def create(
        title: str,
        file_url: str,
        file_name: str,
        file_size: int,
        file_type: str,
        uploaded_by: int,
        description: Optional[str] = None,
        cloudinary_public_id: Optional[str] = None,
        is_public: bool = False,
    ) -> Document:
        doc = Document(
            title=title.strip(),
            description=description,
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            uploaded_by=uploaded_by,
            cloudinary_public_id=cloudinary_public_id,
            is_public=is_public,
            status=DocumentStatus.PENDING.value,
        )
        db.session.add(doc)
        db.session.commit()
        return doc

    @staticmethod
    def update(doc: Document, data: dict) -> Document:
        allowed = {"title", "description", "is_public"}
        for key, value in data.items():
            if key in allowed:
                setattr(doc, key, value)
        db.session.commit()
        return doc

    @staticmethod
    def save_chunks(document_id: int, chunks: list[str]) -> list[DocumentChunk]:
        """
        Persist document text chunks to the DB before sending to ChromaDB.
        Returns created chunk objects.
        """
        chunk_objects = []
        for idx, content in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=idx,
                content=content,
                token_count=len(content.split()),  # Rough token estimate
            )
            db.session.add(chunk)
            chunk_objects.append(chunk)
        db.session.commit()
        return chunk_objects

    @staticmethod
    def update_chunk_chroma_ids(chunks: list[DocumentChunk], chroma_ids: list[str]) -> None:
        """Link each chunk to its ChromaDB document ID after indexing."""
        for chunk, chroma_id in zip(chunks, chroma_ids):
            chunk.chroma_id = chroma_id
        db.session.commit()

    @staticmethod
    def list_with_filters(
        status: Optional[str] = None,
        uploaded_by: Optional[int] = None,
        file_type: Optional[str] = None,
        is_public: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20,
    ):
        query = Document.query.filter_by(deleted_at=None).order_by(Document.created_at.desc())
        if status:
            query = query.filter(Document.status == status)
        if uploaded_by:
            query = query.filter(Document.uploaded_by == uploaded_by)
        if file_type:
            query = query.filter(Document.file_type == file_type)
        if is_public is not None:
            query = query.filter(Document.is_public == is_public)
        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_pending_documents(limit: int = 10) -> list[Document]:
        """Get documents awaiting processing (for Celery pickup)."""
        return (
            Document.query.filter_by(status=DocumentStatus.PENDING.value, deleted_at=None)
            .order_by(Document.created_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def soft_delete(doc: Document) -> None:
        doc.soft_delete()
