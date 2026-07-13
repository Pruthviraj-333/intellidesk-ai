"""
IntelliDesk AI — Auth API Integration Tests
Tests for all /api/v1/auth/* endpoints.
"""

import pytest


class TestRegister:
    """Tests for POST /api/v1/auth/register"""

    def test_register_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "NewUser@123!",
            "confirm_password": "NewUser@123!",
            "first_name": "New",
            "last_name": "User",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "success"
        assert "user" in data["data"]
        assert data["data"]["user"]["email"] == "newuser@test.com"
        assert data["data"]["user"]["status"] == "pending_verification"

    def test_register_duplicate_email(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "employee@test.com",  # Already seeded
            "password": "Test@12345!",
            "confirm_password": "Test@12345!",
            "first_name": "Dup",
            "last_name": "User",
        })
        assert resp.status_code == 409
        assert resp.get_json()["error"]["code"] == "CONFLICT"

    def test_register_password_mismatch(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "mismatch@test.com",
            "password": "Test@12345!",
            "confirm_password": "Different@123!",
            "first_name": "Test",
            "last_name": "User",
        })
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_register_weak_password(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "weak@test.com",
            "password": "password",
            "confirm_password": "password",
            "first_name": "Test",
            "last_name": "User",
        })
        assert resp.status_code == 400

    def test_register_missing_required_fields(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "incomplete@test.com",
        })
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_register_invalid_email(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "Test@12345!",
            "confirm_password": "Test@12345!",
            "first_name": "Test",
            "last_name": "User",
        })
        assert resp.status_code == 400


class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    def test_login_success(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "employee@test.com",
            "password": "Test@12345!",
        })
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["user"]["email"] == "employee@test.com"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "employee@test.com",
            "password": "WrongPassword@123",
        })
        assert resp.status_code == 401
        assert resp.get_json()["error"]["code"] == "UNAUTHORIZED"

    def test_login_nonexistent_email(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "Test@12345!",
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/api/v1/auth/login", json={"email": "employee@test.com"})
        assert resp.status_code == 400

    def test_login_returns_user_role(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "Test@12345!",
        })
        assert resp.status_code == 200
        user = resp.get_json()["data"]["user"]
        assert user["role"] == "admin"


class TestTokenRefresh:
    """Tests for POST /api/v1/auth/refresh"""

    def test_refresh_success(self, client):
        # Login first
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "agent@test.com",
            "password": "Test@12345!",
        })
        refresh_token = login_resp.get_json()["data"]["refresh_token"]

        # Use refresh token
        resp = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_access_token_fails(self, client, auth_headers_employee):
        # Sending access token to refresh endpoint should fail
        resp = client.post(
            "/api/v1/auth/refresh",
            headers=auth_headers_employee,
        )
        assert resp.status_code == 401  # Access token used on refresh endpoint


class TestGetMe:
    """Tests for GET /api/v1/auth/me"""

    def test_get_me_authenticated(self, client, auth_headers_employee):
        resp = client.get("/api/v1/auth/me", headers=auth_headers_employee)
        assert resp.status_code == 200
        user = resp.get_json()["data"]
        assert user["email"] == "employee@test.com"
        assert user["role"] == "employee"

    def test_get_me_unauthenticated(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestPasswordReset:
    """Tests for forgot and reset password flows."""

    def test_forgot_password_existing_email(self, client):
        resp = client.post("/api/v1/auth/forgot-password", json={
            "email": "employee@test.com"
        })
        # Always 200 regardless of email existence
        assert resp.status_code == 200

    def test_forgot_password_nonexistent_email(self, client):
        resp = client.post("/api/v1/auth/forgot-password", json={
            "email": "nobody@test.com"
        })
        assert resp.status_code == 200  # No enumeration

    def test_reset_password_invalid_token(self, client):
        resp = client.post("/api/v1/auth/reset-password", json={
            "token": "invalid-token-xyz",
            "password": "NewPass@123!",
            "confirm_password": "NewPass@123!",
        })
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_public(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_detailed_requires_auth(self, client):
        resp = client.get("/api/v1/health/detailed")
        assert resp.status_code == 401

    def test_health_detailed_admin(self, client, auth_headers_admin):
        resp = client.get("/api/v1/health/detailed", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "services" in data
        assert "database" in data["services"]
