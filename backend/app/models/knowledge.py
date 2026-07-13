"""
IntelliDesk AI — Knowledge Base Models
Article management, categorization, tagging, and engagement tracking.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.base import TimestampMixin, SoftDeleteMixin
from app.utils.constants import ArticleStatus

# ─── Association Tables ───────────────────────────────────────────────────────

article_tags = db.Table(
    "article_tags",
    db.Column("article_id", db.Integer, db.ForeignKey("knowledge_articles.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("article_tag_list.id"), primary_key=True),
)

article_categories = db.Table(
    "article_categories",
    db.Column("article_id", db.Integer, db.ForeignKey("knowledge_articles.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("article_category_list.id"), primary_key=True),
)


class ArticleCategory(db.Model, TimestampMixin):
    """Knowledge article category (hierarchical)."""

    __tablename__ = "article_category_list"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(120), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=True)  # icon name / emoji
    parent_id = db.Column(db.Integer, db.ForeignKey("article_category_list.id"), nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Self-referential relationship for subcategories
    parent = db.relationship("ArticleCategory", remote_side=[id], backref="children")
    articles = db.relationship("KnowledgeArticle", secondary=article_categories, back_populates="categories")

    def __repr__(self) -> str:
        return f"<ArticleCategory {self.name}>"


class ArticleTag(db.Model):
    """Knowledge article tag — free-form keyword labels."""

    __tablename__ = "article_tag_list"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    slug = db.Column(db.String(60), nullable=False, unique=True, index=True)
    use_count = db.Column(db.Integer, default=0, nullable=False)

    articles = db.relationship("KnowledgeArticle", secondary=article_tags, back_populates="tags")

    def __repr__(self) -> str:
        return f"<ArticleTag {self.name}>"


class KnowledgeArticle(db.Model, TimestampMixin, SoftDeleteMixin):
    """
    Knowledge Article — the core entity of the knowledge base.
    Supports rich-text content, versioning metadata, and RAG indexing.
    """

    __tablename__ = "knowledge_articles"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(220), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    summary = db.Column(db.String(500), nullable=True)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=ArticleStatus.DRAFT.value, index=True)

    # Authorship
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Visibility — None = public to all authenticated users
    visible_to_roles = db.Column(db.JSON, default=None, nullable=True)

    # Engagement counters (denormalized for performance)
    view_count = db.Column(db.Integer, default=0, nullable=False)
    helpful_count = db.Column(db.Integer, default=0, nullable=False)
    not_helpful_count = db.Column(db.Integer, default=0, nullable=False)
    linked_ticket_count = db.Column(db.Integer, default=0, nullable=False)

    # RAG metadata — tracks embedding status in ChromaDB
    is_indexed = db.Column(db.Boolean, default=False, nullable=False, index=True)
    indexed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    embedding_model = db.Column(db.String(100), nullable=True)
    chroma_document_id = db.Column(db.String(100), nullable=True)

    # Versioning
    version = db.Column(db.Integer, default=1, nullable=False)
    last_edited_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relationships
    author = db.relationship("User", foreign_keys=[author_id], backref="authored_articles")
    reviewer = db.relationship("User", foreign_keys=[reviewer_id], backref="reviewed_articles")
    last_editor = db.relationship("User", foreign_keys=[last_edited_by], backref="edited_articles")
    categories = db.relationship("ArticleCategory", secondary=article_categories, back_populates="articles")
    tags = db.relationship("ArticleTag", secondary=article_tags, back_populates="articles")
    votes = db.relationship("ArticleVote", back_populates="article", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<KnowledgeArticle '{self.title}' [{self.status}]>"

    @property
    def is_published(self) -> bool:
        return self.status == ArticleStatus.PUBLISHED.value

    @property
    def helpfulness_score(self) -> float:
        """Percentage of helpful votes."""
        total = self.helpful_count + self.not_helpful_count
        if total == 0:
            return 0.0
        return round(self.helpful_count / total * 100, 1)

    def mark_indexed(self, embedding_model: str, chroma_id: str) -> None:
        """Mark this article as embedded and indexed in ChromaDB."""
        self.is_indexed = True
        self.indexed_at = datetime.now(timezone.utc)
        self.embedding_model = embedding_model
        self.chroma_document_id = chroma_id
        db.session.commit()

    def increment_view(self) -> None:
        self.view_count += 1
        db.session.commit()


class ArticleVote(db.Model):
    """
    Article vote — one vote per user per article.
    Enforced by unique constraint.
    """

    __tablename__ = "article_votes"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(
        db.Integer, db.ForeignKey("knowledge_articles.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_helpful = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("article_id", "user_id", name="uq_article_vote_user"),
    )

    article = db.relationship("KnowledgeArticle", back_populates="votes")
    user = db.relationship("User", foreign_keys=[user_id], backref="article_votes")

    def __repr__(self) -> str:
        vote_str = "helpful" if self.is_helpful else "not helpful"
        return f"<ArticleVote article={self.article_id} user={self.user_id} [{vote_str}]>"
