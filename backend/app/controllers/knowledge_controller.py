"""
IntelliDesk AI — Knowledge Base Controller (Blueprint)
HTTP handlers for articles, search, categories, and voting.
Route prefix: /api/v1/knowledge
"""

from flask import Blueprint
from flask_jwt_extended import jwt_required

from app.repositories.knowledge_repository import (
    ArticleRepository, ArticleCategoryRepository, ArticleTagRepository,
)
from app.services.rag_service import RAGService
from app.services.audit_service import AuditService
from app.dtos.knowledge_dto import (
    ArticleSummarySchema, ArticleDetailSchema,
    CreateArticleSchema, UpdateArticleSchema, ArticleListQuerySchema,
    VoteArticleSchema, SearchQuerySchema, SearchResultSchema,
    ArticleCategorySchema, CreateCategorySchema, ArticleTagSchema,
)
from app.utils.decorators import (
    validate_body, validate_query, role_required,
    get_current_user_id, get_current_user_role,
)
from app.utils.response import (
    success_response, created_response, no_content_response,
    paginated_response, build_pagination_meta,
)
from app.utils.constants import UserRole
from app.utils.exceptions import NotFoundError, AuthorizationError, BusinessLogicError

knowledge_bp = Blueprint("knowledge", __name__, url_prefix="/api/v1/knowledge")


# ─── Article CRUD ─────────────────────────────────────────────────────────────

@knowledge_bp.route("/articles", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(CreateArticleSchema)
def create_article(data: dict):
    """POST /api/v1/knowledge/articles — Create draft article (Agent+)."""
    user_id = get_current_user_id()
    article = ArticleRepository.create(
        title=data["title"],
        body=data["body"],
        author_id=user_id,
        summary=data.get("summary"),
        category_ids=data.get("category_ids", []),
        tag_names=data.get("tag_names", []),
        visible_to_roles=data.get("visible_to_roles"),
    )
    AuditService.log(
        action="article_created",
        resource_type="knowledge_article",
        resource_id=article.id,
        new_values={"title": article.title},
    )
    return created_response(ArticleDetailSchema().dump(article))


@knowledge_bp.route("/articles", methods=["GET"])
@jwt_required()
@validate_query(ArticleListQuerySchema)
def list_articles(params: dict):
    """GET /api/v1/knowledge/articles — List articles (role-scoped)."""
    role = get_current_user_role()
    # Employees only see published articles
    if role == UserRole.EMPLOYEE.value and "status" not in params:
        params["status"] = "published"
    params["user_role"] = role

    pagination = ArticleRepository.list_with_filters(**{
        k: v for k, v in params.items()
        if k in ("status", "category_id", "tag", "author_id", "search",
                  "sort_by", "order", "page", "per_page", "user_role")
    })
    return paginated_response(
        data=ArticleSummarySchema(many=True).dump(pagination.items),
        pagination=build_pagination_meta(pagination),
    )


@knowledge_bp.route("/articles/<slug>", methods=["GET"])
@jwt_required()
def get_article(slug: str):
    """GET /api/v1/knowledge/articles/:slug — Get article by slug."""
    article = ArticleRepository.get_by_slug(slug)
    if not article:
        raise NotFoundError("KnowledgeArticle")

    # Employees can only view published articles
    role = get_current_user_role()
    if role == UserRole.EMPLOYEE.value and not article.is_published:
        raise NotFoundError("KnowledgeArticle")

    article.increment_view()
    return success_response(ArticleDetailSchema().dump(article))


@knowledge_bp.route("/articles/<int:article_id>", methods=["PUT"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(UpdateArticleSchema)
def update_article(data: dict, article_id: int):
    """PUT /api/v1/knowledge/articles/:id — Update article (Agent+, own articles only for agents)."""
    user_id = get_current_user_id()
    role = get_current_user_role()

    article = ArticleRepository.get_by_id(article_id)
    if not article:
        raise NotFoundError("KnowledgeArticle", article_id)

    # Agents can only edit their own articles
    if role == UserRole.AGENT.value and article.author_id != user_id:
        raise AuthorizationError("Agents can only edit their own articles.")

    article.last_edited_by = user_id
    article = ArticleRepository.update(article, data)

    # Re-index if published and body changed
    if article.is_published and ("body" in data or "title" in data):
        RAGService.index_article(article)

    AuditService.log(
        action="article_updated",
        resource_type="knowledge_article",
        resource_id=article.id,
        new_values=data,
    )
    return success_response(ArticleDetailSchema().dump(article))


@knowledge_bp.route("/articles/<int:article_id>", methods=["DELETE"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
def delete_article(article_id: int):
    """DELETE /api/v1/knowledge/articles/:id — Soft delete (Admin+)."""
    article = ArticleRepository.get_by_id(article_id)
    if not article:
        raise NotFoundError("KnowledgeArticle", article_id)

    # Remove from ChromaDB
    if article.is_indexed:
        RAGService.remove_article_from_index(article.id)

    AuditService.log(
        action="article_deleted",
        resource_type="knowledge_article",
        resource_id=article.id,
        old_values={"title": article.title},
    )
    ArticleRepository.soft_delete(article)
    return no_content_response()


@knowledge_bp.route("/articles/<int:article_id>/publish", methods=["PUT"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def publish_article(article_id: int):
    """PUT /api/v1/knowledge/articles/:id/publish — Publish and index article (Manager+)."""
    article = ArticleRepository.get_by_id(article_id)
    if not article:
        raise NotFoundError("KnowledgeArticle", article_id)
    if article.is_published:
        raise BusinessLogicError("Article is already published.")

    article = ArticleRepository.update(article, {"status": "published"})

    # Index in ChromaDB
    success = RAGService.index_article(article)
    return success_response({
        "message": "Article published successfully.",
        "indexed": success,
        "article": ArticleDetailSchema().dump(article),
    })


# ─── Voting ───────────────────────────────────────────────────────────────────

@knowledge_bp.route("/articles/<int:article_id>/vote", methods=["POST"])
@jwt_required()
@validate_body(VoteArticleSchema)
def vote_article(data: dict, article_id: int):
    """POST /api/v1/knowledge/articles/:id/vote — Vote helpful/not-helpful."""
    user_id = get_current_user_id()
    article = ArticleRepository.get_by_id(article_id)
    if not article:
        raise NotFoundError("KnowledgeArticle", article_id)
    if not article.is_published:
        raise BusinessLogicError("Only published articles can be voted on.")

    result = ArticleRepository.record_vote(
        article_id=article_id,
        user_id=user_id,
        is_helpful=data["is_helpful"],
    )
    return success_response({
        "message": "Vote recorded.",
        "votes": result,
        "helpfulness_score": article.helpfulness_score,
    })


# ─── Semantic Search ──────────────────────────────────────────────────────────

@knowledge_bp.route("/search", methods=["GET"])
@jwt_required()
@validate_query(SearchQuerySchema)
def semantic_search(params: dict):
    """
    GET /api/v1/knowledge/search?q=...
    Semantic search across articles and documents using ChromaDB.
    """
    query = params["q"]
    n_results = params.get("n_results", 5)
    collections = None
    if not params.get("include_documents", True):
        collections = [RAGService.ARTICLE_COLLECTION]

    results = RAGService.semantic_search(
        query=query,
        n_results=n_results,
        collections=collections,
    )
    return success_response({
        "query": query,
        "results": results,
        "result_count": len(results),
    })


# ─── Categories ───────────────────────────────────────────────────────────────

@knowledge_bp.route("/categories", methods=["GET"])
@jwt_required()
def list_categories():
    """GET /api/v1/knowledge/categories — List all active categories."""
    categories = ArticleCategoryRepository.get_all_active()
    return success_response(ArticleCategorySchema(many=True).dump(categories))


@knowledge_bp.route("/categories", methods=["POST"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(CreateCategorySchema)
def create_category(data: dict):
    """POST /api/v1/knowledge/categories — Create category (Admin+)."""
    cat = ArticleCategoryRepository.create(**data)
    return created_response(ArticleCategorySchema().dump(cat))


# ─── Tags ─────────────────────────────────────────────────────────────────────

@knowledge_bp.route("/tags", methods=["GET"])
@jwt_required()
def get_popular_tags():
    """GET /api/v1/knowledge/tags — Get popular tags for autocomplete."""
    tags = ArticleTagRepository.get_popular_tags(limit=30)
    return success_response(ArticleTagSchema(many=True).dump(tags))
