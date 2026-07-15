"""
IntelliDesk AI — Knowledge Base API Integration Tests
Tests for /api/v1/knowledge/* and /api/v1/documents/* endpoints.
"""

import pytest


class TestCreateArticle:
    """Tests for POST /api/v1/knowledge/articles"""

    def test_agent_can_create_draft_article(self, client, auth_headers_agent):
        resp = client.post(
            "/api/v1/knowledge/articles",
            json={
                "title": "How to reset your VPN configuration",
                "body": "This article explains the step-by-step process for resetting your VPN. "
                * 10,
                "summary": "Quick guide to VPN configuration reset for remote workers.",
                "tag_names": ["vpn", "network", "troubleshooting"],
            },
            headers=auth_headers_agent,
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["status"] == "draft"
        assert data["slug"] is not None
        assert len(data["tags"]) == 3
        assert data["is_indexed"] == False

    def test_employee_cannot_create_article(self, client, auth_headers_employee):
        resp = client.post(
            "/api/v1/knowledge/articles",
            json={
                "title": "Employee trying to write an article",
                "body": "This should not be allowed because employees are read-only." * 5,
            },
            headers=auth_headers_employee,
        )
        assert resp.status_code == 403

    def test_article_title_too_short(self, client, auth_headers_agent):
        resp = client.post(
            "/api/v1/knowledge/articles",
            json={
                "title": "Hi",
                "body": "Short title article body content." * 5,
            },
            headers=auth_headers_agent,
        )
        assert resp.status_code == 400

    def test_article_body_too_short(self, client, auth_headers_agent):
        resp = client.post(
            "/api/v1/knowledge/articles",
            json={
                "title": "Article with short body",
                "body": "Too short.",
            },
            headers=auth_headers_agent,
        )
        assert resp.status_code == 400


class TestListArticles:
    """Tests for GET /api/v1/knowledge/articles"""

    def test_agent_lists_all_statuses(self, client, auth_headers_agent):
        resp = client.get("/api/v1/knowledge/articles", headers=auth_headers_agent)
        assert resp.status_code == 200
        assert isinstance(resp.get_json()["data"], list)

    def test_employee_only_sees_published(self, client, auth_headers_employee):
        resp = client.get("/api/v1/knowledge/articles", headers=auth_headers_employee)
        assert resp.status_code == 200
        for article in resp.get_json()["data"]:
            assert article["status"] == "published"

    def test_search_articles(self, client, auth_headers_agent):
        resp = client.get("/api/v1/knowledge/articles?search=VPN", headers=auth_headers_agent)
        assert resp.status_code == 200

    def test_filter_by_tag(self, client, auth_headers_agent):
        resp = client.get("/api/v1/knowledge/articles?tag=vpn", headers=auth_headers_agent)
        assert resp.status_code == 200

    def test_unauthenticated_cannot_list(self, client):
        resp = client.get("/api/v1/knowledge/articles")
        assert resp.status_code == 401


class TestGetArticle:
    """Tests for GET /api/v1/knowledge/articles/:slug"""

    def _create_article(self, client, headers):
        resp = client.post(
            "/api/v1/knowledge/articles",
            json={
                "title": "Article for slug retrieval test",
                "body": "Full body content of this article for testing retrieval." * 5,
            },
            headers=headers,
        )
        return resp.get_json()["data"]["slug"]

    def test_get_article_by_slug(self, client, auth_headers_agent):
        slug = self._create_article(client, auth_headers_agent)
        resp = client.get(f"/api/v1/knowledge/articles/{slug}", headers=auth_headers_agent)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "body" in data
        assert "categories" in data
        assert "tags" in data

    def test_view_increments_count(self, client, auth_headers_agent):
        slug = self._create_article(client, auth_headers_agent)
        # View it twice
        client.get(f"/api/v1/knowledge/articles/{slug}", headers=auth_headers_agent)
        resp = client.get(f"/api/v1/knowledge/articles/{slug}", headers=auth_headers_agent)
        assert resp.get_json()["data"]["view_count"] >= 1

    def test_get_nonexistent_article(self, client, auth_headers_agent):
        resp = client.get(
            "/api/v1/knowledge/articles/nonexistent-slug-xyz", headers=auth_headers_agent
        )
        assert resp.status_code == 404

    def test_employee_cannot_get_draft(self, client, auth_headers_agent, auth_headers_employee):
        slug = self._create_article(client, auth_headers_agent)
        resp = client.get(f"/api/v1/knowledge/articles/{slug}", headers=auth_headers_employee)
        assert resp.status_code == 404  # Draft hidden from employees


class TestUpdateArticle:
    """Tests for PUT /api/v1/knowledge/articles/:id"""

    def _create_and_get_id(self, client, headers):
        resp = client.post(
            "/api/v1/knowledge/articles",
            json={
                "title": "Article for update testing purposes",
                "body": "Original body content for update testing, needs to be long enough." * 3,
            },
            headers=headers,
        )
        return resp.get_json()["data"]["id"]

    def test_agent_can_update_own_article(self, client, auth_headers_agent):
        article_id = self._create_and_get_id(client, auth_headers_agent)
        resp = client.put(
            f"/api/v1/knowledge/articles/{article_id}",
            json={
                "summary": "Updated summary added to the article.",
            },
            headers=auth_headers_agent,
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["summary"] == "Updated summary added to the article."

    def test_version_increments_on_update(self, client, auth_headers_agent):
        article_id = self._create_and_get_id(client, auth_headers_agent)
        resp = client.put(
            f"/api/v1/knowledge/articles/{article_id}",
            json={
                "summary": "Second update to check version increments.",
            },
            headers=auth_headers_agent,
        )
        assert resp.get_json()["data"]["version"] == 2


class TestPublishArticle:
    """Tests for PUT /api/v1/knowledge/articles/:id/publish"""

    def _create_article_id(self, client, headers):
        resp = client.post(
            "/api/v1/knowledge/articles",
            json={
                "title": "Article ready for publishing workflow",
                "body": "This article has been reviewed and is ready to be published." * 4,
            },
            headers=headers,
        )
        return resp.get_json()["data"]["id"]

    def test_manager_can_publish_article(self, client, auth_headers_manager, auth_headers_agent):
        article_id = self._create_article_id(client, auth_headers_agent)
        resp = client.put(
            f"/api/v1/knowledge/articles/{article_id}/publish",
            headers=auth_headers_manager,
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["article"]["status"] == "published"
        assert "indexed" in data

    def test_agent_cannot_publish_article(self, client, auth_headers_agent):
        article_id = self._create_article_id(client, auth_headers_agent)
        resp = client.put(
            f"/api/v1/knowledge/articles/{article_id}/publish",
            headers=auth_headers_agent,
        )
        assert resp.status_code == 403


class TestArticleVoting:
    """Tests for POST /api/v1/knowledge/articles/:id/vote"""

    def _get_published_article_id(self, client, agent_headers, manager_headers):
        create_resp = client.post(
            "/api/v1/knowledge/articles",
            json={
                "title": "Voting test: password manager guide",
                "body": "This is a comprehensive guide to using a password manager safely." * 5,
            },
            headers=agent_headers,
        )
        article_id = create_resp.get_json()["data"]["id"]
        client.put(f"/api/v1/knowledge/articles/{article_id}/publish", headers=manager_headers)
        return article_id

    def test_vote_helpful(
        self, client, auth_headers_employee, auth_headers_agent, auth_headers_manager
    ):
        article_id = self._get_published_article_id(
            client, auth_headers_agent, auth_headers_manager
        )
        resp = client.post(
            f"/api/v1/knowledge/articles/{article_id}/vote",
            json={"is_helpful": True},
            headers=auth_headers_employee,
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["votes"]["helpful"] >= 1

    def test_vote_cannot_be_cast_on_draft(self, client, auth_headers_agent, auth_headers_employee):
        create_resp = client.post(
            "/api/v1/knowledge/articles",
            json={
                "title": "Draft article for vote rejection test",
                "body": "This draft article should not accept votes from any user." * 4,
            },
            headers=auth_headers_agent,
        )
        article_id = create_resp.get_json()["data"]["id"]
        resp = client.post(
            f"/api/v1/knowledge/articles/{article_id}/vote",
            json={"is_helpful": True},
            headers=auth_headers_employee,
        )
        assert resp.status_code == 422


class TestSemanticSearch:
    """Tests for GET /api/v1/knowledge/search"""

    def test_search_returns_results_structure(self, client, auth_headers_agent):
        resp = client.get(
            "/api/v1/knowledge/search?q=password+reset+guide",
            headers=auth_headers_agent,
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "query" in data
        assert "results" in data
        assert "result_count" in data
        assert isinstance(data["results"], list)

    def test_search_query_too_short(self, client, auth_headers_agent):
        resp = client.get("/api/v1/knowledge/search?q=ab", headers=auth_headers_agent)
        assert resp.status_code == 400

    def test_search_requires_auth(self, client):
        resp = client.get("/api/v1/knowledge/search?q=password")
        assert resp.status_code == 401


class TestCategories:
    """Tests for knowledge category endpoints."""

    def test_list_categories(self, client, auth_headers_employee):
        resp = client.get("/api/v1/knowledge/categories", headers=auth_headers_employee)
        assert resp.status_code == 200
        assert isinstance(resp.get_json()["data"], list)

    def test_admin_creates_category(self, client, auth_headers_admin):
        resp = client.post(
            "/api/v1/knowledge/categories",
            json={
                "name": "Security Best Practices",
                "slug": "security-best-practices",
                "description": "Articles about IT security best practices.",
                "icon": "🔒",
            },
            headers=auth_headers_admin,
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["name"] == "Security Best Practices"

    def test_employee_cannot_create_category(self, client, auth_headers_employee):
        resp = client.post(
            "/api/v1/knowledge/categories",
            json={
                "name": "My Category",
                "slug": "my-category",
            },
            headers=auth_headers_employee,
        )
        assert resp.status_code == 403
