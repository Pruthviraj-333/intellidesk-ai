"""
IntelliDesk AI — Document Management Model
Uploaded knowledge documents for RAG pipeline processing.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin
from app.utils.constants import DocumentStatus


class Document(db.Model, TimestampMixin, SoftDeleteMixin):
    """
    Document model — uploaded files ingested into the RAG pipeline.
    PDF, DOCX, TXT, and MD files are chunked, embedded, and stored in ChromaDB.
    """

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # File metadata
    file_url = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # bytes
    file_type = db.Column(db.String(20), nullable=False)  # pdf | docx | txt | md
    cloudinary_public_id = db.Column(db.String(200), nullable=True)

    # Processing state
    status = db.Column(
        db.String(20),
        nullable=False,
        default=DocumentStatus.PENDING.value,
        index=True,
    )
    error_message = db.Column(db.Text, nullable=True)

    # RAG metadata
    chunk_count = db.Column(db.Integer, default=0, nullable=False)
    embedding_model = db.Column(db.String(100), nullable=True)
    chroma_collection = db.Column(db.String(100), nullable=True)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Ownership
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    is_public = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    uploader = db.relationship("User", foreign_keys=[uploaded_by], backref="uploaded_documents")
    chunks = db.relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document '{self.file_name}' [{self.status}]>"

    @property
    def is_processed(self) -> bool:
        return self.status == DocumentStatus.PROCESSED.value

    @property
    def can_be_processed(self) -> bool:
        return self.status in (DocumentStatus.PENDING.value, DocumentStatus.FAILED.value)

    def mark_processing(self) -> None:
        self.status = DocumentStatus.PROCESSING.value
        db.session.commit()

    def mark_processed(self, chunk_count: int, model: str, collection: str) -> None:
        self.status = DocumentStatus.PROCESSED.value
        self.chunk_count = chunk_count
        self.embedding_model = model
        self.chroma_collection = collection
        self.processed_at = datetime.now(timezone.utc)
        self.error_message = None
        db.session.commit()

    def mark_failed(self, error: str) -> None:
        self.status = DocumentStatus.FAILED.value
        self.error_message = error
        db.session.commit()


class DocumentChunk(db.Model):
    """
    DocumentChunk — stores individual text chunks after document parsing.
    Each chunk is separately embedded and stored in ChromaDB.
    Kept in SQL for auditing and re-processing capability.
    """

    __tablename__ = "document_chunks"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.Integer,
        db.ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = db.Column(db.Integer, nullable=False)  # 0-based position
    content = db.Column(db.Text, nullable=False)
    token_count = db.Column(db.Integer, nullable=True)
    chroma_id = db.Column(db.String(100), nullable=True, index=True)  # ChromaDB document ID
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    document = db.relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk doc={self.document_id} idx={self.chunk_index}>"
