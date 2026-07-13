"""
IntelliDesk AI — Knowledge Base Repository
Data access layer for KnowledgeArticle, ArticleCategory, and ArticleTag.
"""

from typing import Optional

from sqlalchemy import or_

from app.extensions import db
from app.models.knowledge import KnowledgeArticle, ArticleCategory, ArticleTag, ArticleVote
from app.utils.constants import ArticleStatus
from app.utils.helpers import generate_article_slug


class ArticleRepository:
    """Repository for KnowledgeArticle entity."""

    @staticmethod
    def get_by_id(article_id: int) -> Optional[KnowledgeArticle]:
        return KnowledgeArticle.query.filter_by(id=article_id, deleted_at=None).first()

    @staticmethod
    def get_by_slug(slug: str) -> Optional[KnowledgeArticle]:
        return KnowledgeArticle.query.filter_by(slug=slug, deleted_at=None).first()

    @staticmethod
    def create(
        title: str,
        body: str,
        author_id: int,
        summary: Optional[str] = None,
        category_ids: Optional[list[int]] = None,
        tag_names: Optional[list[str]] = None,
        visible_to_roles: Optional[list[str]] = None,
    ) -> KnowledgeArticle:
        slug = generate_article_slug(title)
        article = KnowledgeArticle(
            slug=slug,
            title=title.strip(),
            body=body.strip(),
            summary=summary.strip() if summary else None,
            author_id=author_id,
            visible_to_roles=visible_to_roles,
        )
        db.session.add(article)
        db.session.flush()  # Get ID

        # Attach categories
        if category_ids:
            cats = ArticleCategory.query.filter(ArticleCategory.id.in_(category_ids)).all()
            article.categories.extend(cats)

        # Create/get tags and attach
        if tag_names:
            tags = ArticleTagRepository.get_or_create_tags(tag_names)
            article.tags.extend(tags)

        db.session.commit()
        return article

    @staticmethod
    def update(article: KnowledgeArticle, data: dict) -> KnowledgeArticle:
        from datetime import datetime, timezone

        allowed = {"title", "body", "summary", "status", "visible_to_roles", "reviewer_id"}
        for key, value in data.items():
            if key in allowed:
                setattr(article, key, value)

        if data.get("status") == ArticleStatus.PUBLISHED.value and not article.published_at:
            article.published_at = datetime.now(timezone.utc)

        if "category_ids" in data:
            cats = ArticleCategory.query.filter(ArticleCategory.id.in_(data["category_ids"])).all()
            article.categories = cats

        if "tag_names" in data:
            tags = ArticleTagRepository.get_or_create_tags(data["tag_names"])
            article.tags = tags

        article.version += 1
        db.session.commit()
        return article

    @staticmethod
    def list_with_filters(
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        tag: Optional[str] = None,
        author_id: Optional[int] = None,
        search: Optional[str] = None,
        user_role: Optional[str] = None,
        sort_by: str = "published_at",
        order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ):
        query = KnowledgeArticle.query.filter_by(deleted_at=None)

        if status:
            query = query.filter(KnowledgeArticle.status == status)
        if author_id:
            query = query.filter(KnowledgeArticle.author_id == author_id)
        if category_id:
            query = query.join(KnowledgeArticle.categories).filter(
                ArticleCategory.id == category_id
            )
        if tag:
            query = query.join(KnowledgeArticle.tags).filter(
                ArticleTag.slug == tag
            )
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    KnowledgeArticle.title.ilike(term),
                    KnowledgeArticle.body.ilike(term),
                    KnowledgeArticle.summary.ilike(term),
                )
            )

        # Role-based visibility filter for non-admins
        if user_role in ("employee",):
            query = query.filter(KnowledgeArticle.status == ArticleStatus.PUBLISHED.value)

        sort_col = getattr(KnowledgeArticle, sort_by, KnowledgeArticle.published_at)
        query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())
        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def soft_delete(article: KnowledgeArticle) -> None:
        # Unindex from ChromaDB before soft delete
        if article.chroma_document_id:
            article.is_indexed = False
        article.soft_delete()

    @staticmethod
    def record_vote(article_id: int, user_id: int, is_helpful: bool) -> dict:
        """
        Record or update a user's vote on an article.
        Handles the unique constraint — updates vote if already exists.
        Returns vote counts.
        """
        existing = ArticleVote.query.filter_by(
            article_id=article_id, user_id=user_id
        ).first()

        article = KnowledgeArticle.query.get(article_id)
        if not article:
            return {}

        if existing:
            old_helpful = existing.is_helpful
            if old_helpful == is_helpful:
                # Same vote — no change needed
                return {"helpful": article.helpful_count, "not_helpful": article.not_helpful_count}

            # Flip vote
            existing.is_helpful = is_helpful
            if old_helpful:
                article.helpful_count = max(0, article.helpful_count - 1)
                article.not_helpful_count += 1
            else:
                article.not_helpful_count = max(0, article.not_helpful_count - 1)
                article.helpful_count += 1
        else:
            vote = ArticleVote(article_id=article_id, user_id=user_id, is_helpful=is_helpful)
            db.session.add(vote)
            if is_helpful:
                article.helpful_count += 1
            else:
                article.not_helpful_count += 1

        db.session.commit()
        return {"helpful": article.helpful_count, "not_helpful": article.not_helpful_count}


class ArticleCategoryRepository:
    """Repository for ArticleCategory."""

    @staticmethod
    def get_by_id(cat_id: int) -> Optional[ArticleCategory]:
        return ArticleCategory.query.get(cat_id)

    @staticmethod
    def get_all_active() -> list[ArticleCategory]:
        return ArticleCategory.query.filter_by(
            is_active=True, parent_id=None
        ).order_by(ArticleCategory.sort_order).all()

    @staticmethod
    def create(
        name: str,
        slug: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        parent_id: Optional[int] = None,
        sort_order: int = 0,
    ) -> ArticleCategory:
        cat = ArticleCategory(
            name=name, slug=slug, description=description,
            icon=icon, parent_id=parent_id, sort_order=sort_order,
        )
        db.session.add(cat)
        db.session.commit()
        return cat


class ArticleTagRepository:
    """Repository for ArticleTag."""

    @staticmethod
    def get_or_create_tags(tag_names: list[str]) -> list[ArticleTag]:
        """Get existing tags or create new ones. Returns list of tag objects."""
        from slugify import slugify
        tags = []
        for name in tag_names:
            name = name.strip().lower()
            slug = slugify(name)
            tag = ArticleTag.query.filter_by(slug=slug).first()
            if not tag:
                tag = ArticleTag(name=name, slug=slug)
                db.session.add(tag)
                db.session.flush()
            tags.append(tag)
        return tags

    @staticmethod
    def get_popular_tags(limit: int = 20) -> list[ArticleTag]:
        return ArticleTag.query.order_by(ArticleTag.use_count.desc()).limit(limit).all()
