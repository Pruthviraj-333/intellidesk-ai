"""
IntelliDesk AI — Knowledge Base DTOs (Marshmallow Schemas)
Request validation and response serialization for knowledge and document endpoints.
"""

from marshmallow import Schema, fields, validate

# ─── Category Schemas ─────────────────────────────────────────────────────────


class ArticleCategorySchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    slug = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True, allow_none=True)
    icon = fields.Str(dump_only=True, allow_none=True)
    parent_id = fields.Int(dump_only=True, allow_none=True)
    sort_order = fields.Int(dump_only=True)
    is_active = fields.Bool(dump_only=True)


class CreateCategorySchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    slug = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    description = fields.Str(load_default=None)
    icon = fields.Str(load_default=None)
    parent_id = fields.Int(load_default=None)
    sort_order = fields.Int(load_default=0)


# ─── Tag Schemas ──────────────────────────────────────────────────────────────


class ArticleTagSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    slug = fields.Str(dump_only=True)
    use_count = fields.Int(dump_only=True)


# ─── Article Schemas ──────────────────────────────────────────────────────────


class AuthorMiniSchema(Schema):
    id = fields.Int(dump_only=True)
    full_name = fields.Method("get_full_name")
    avatar_url = fields.Str(dump_only=True, allow_none=True)

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class ArticleSummarySchema(Schema):
    """Compact article for list views and suggestions."""

    id = fields.Int(dump_only=True)
    slug = fields.Str(dump_only=True)
    title = fields.Str(dump_only=True)
    summary = fields.Str(dump_only=True, allow_none=True)
    status = fields.Str(dump_only=True)
    author = fields.Nested(AuthorMiniSchema, dump_only=True)
    categories = fields.Nested(ArticleCategorySchema, many=True, dump_only=True)
    tags = fields.Nested(ArticleTagSchema, many=True, dump_only=True)
    view_count = fields.Int(dump_only=True)
    helpful_count = fields.Int(dump_only=True)
    helpfulness_score = fields.Float(dump_only=True)
    is_indexed = fields.Bool(dump_only=True)
    published_at = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ArticleDetailSchema(ArticleSummarySchema):
    """Full article including body and version info."""

    body = fields.Str(dump_only=True)
    version = fields.Int(dump_only=True)
    reviewer = fields.Nested(AuthorMiniSchema, dump_only=True, allow_none=True)
    visible_to_roles = fields.List(fields.Str(), dump_only=True, allow_none=True)
    not_helpful_count = fields.Int(dump_only=True)
    linked_ticket_count = fields.Int(dump_only=True)
    indexed_at = fields.DateTime(dump_only=True, allow_none=True)
    embedding_model = fields.Str(dump_only=True, allow_none=True)


class CreateArticleSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=5, max=200))
    body = fields.Str(required=True, validate=validate.Length(min=50))
    summary = fields.Str(load_default=None, validate=validate.Length(max=500))
    category_ids = fields.List(fields.Int(), load_default=[])
    tag_names = fields.List(fields.Str(validate=validate.Length(min=1, max=50)), load_default=[])
    visible_to_roles = fields.List(fields.Str(), load_default=None)


class UpdateArticleSchema(Schema):
    title = fields.Str(validate=validate.Length(min=5, max=200))
    body = fields.Str(validate=validate.Length(min=50))
    summary = fields.Str(allow_none=True, validate=validate.Length(max=500))
    status = fields.Str(validate=validate.OneOf(["draft", "published", "archived"]))
    category_ids = fields.List(fields.Int())
    tag_names = fields.List(fields.Str(validate=validate.Length(min=1, max=50)))
    visible_to_roles = fields.List(fields.Str(), allow_none=True)
    reviewer_id = fields.Int(allow_none=True)


class ArticleListQuerySchema(Schema):
    status = fields.Str(validate=validate.OneOf(["draft", "published", "archived"]))
    category_id = fields.Int()
    tag = fields.Str()
    author_id = fields.Int()
    search = fields.Str(validate=validate.Length(max=200))
    sort_by = fields.Str(
        load_default="published_at",
        validate=validate.OneOf(["published_at", "created_at", "view_count", "helpful_count"]),
    )
    order = fields.Str(load_default="desc", validate=validate.OneOf(["asc", "desc"]))
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))


class VoteArticleSchema(Schema):
    is_helpful = fields.Bool(required=True)


# ─── Semantic Search Schemas ──────────────────────────────────────────────────


class SearchQuerySchema(Schema):
    q = fields.Str(required=True, validate=validate.Length(min=3, max=500))
    n_results = fields.Int(load_default=5, validate=validate.Range(min=1, max=20))
    include_documents = fields.Bool(load_default=True)


class SearchResultSchema(Schema):
    content = fields.Str(dump_only=True)
    score = fields.Float(dump_only=True)
    collection = fields.Str(dump_only=True)
    metadata = fields.Dict(dump_only=True)


# ─── Document Schemas ─────────────────────────────────────────────────────────


class DocumentResponseSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True, allow_none=True)
    file_name = fields.Str(dump_only=True)
    file_url = fields.Str(dump_only=True)
    file_size = fields.Int(dump_only=True)
    file_type = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    chunk_count = fields.Int(dump_only=True)
    is_public = fields.Bool(dump_only=True)
    uploader = fields.Nested(AuthorMiniSchema, dump_only=True)
    processed_at = fields.DateTime(dump_only=True, allow_none=True)
    error_message = fields.Str(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class DocumentListQuerySchema(Schema):
    status = fields.Str(validate=validate.OneOf(["pending", "processing", "processed", "failed"]))
    file_type = fields.Str(validate=validate.OneOf(["pdf", "docx", "txt", "md"]))
    is_public = fields.Bool()
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
