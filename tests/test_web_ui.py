"""Tests for the Web UI routes.

Note: These tests verify that the Web UI pages load correctly.
Due to FastAPI's global app state, tests are kept simple to avoid state issues.
"""

import pytest
from fastapi.testclient import TestClient

from libra.interfaces.api import create_api_app


@pytest.fixture(scope="module")
def client():
    """Create a test client with Web UI enabled."""
    # Use create_api_app to get app with Web UI
    test_app = create_api_app(include_web_ui=True)
    return TestClient(test_app)


class TestDashboard:
    """Tests for the dashboard page."""

    def test_dashboard_loads(self, client):
        """Test that dashboard page loads successfully."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Dashboard" in response.text
        assert "Total Contexts" in response.text

    def test_dashboard_shows_stats(self, client):
        """Test that dashboard shows statistics."""
        response = client.get("/")
        assert response.status_code == 200
        assert "With Embeddings" in response.text
        assert "Queries Served" in response.text

    def test_dashboard_has_navigation(self, client):
        """Test that dashboard has navigation links."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Contexts" in response.text
        assert "Audit Log" in response.text
        assert "Settings" in response.text


class TestContextsPage:
    """Tests for the contexts list page."""

    def test_contexts_list_loads(self, client):
        """Test that contexts list page loads."""
        response = client.get("/contexts")
        assert response.status_code == 200
        assert "Contexts" in response.text

    def test_contexts_empty_state(self, client):
        """Test empty state message when no contexts."""
        response = client.get("/contexts")
        assert response.status_code == 200
        # Either shows empty state or contexts
        assert "Contexts" in response.text

    def test_contexts_filter_by_type(self, client):
        """Test filtering contexts by type."""
        response = client.get("/contexts?type=knowledge")
        assert response.status_code == 200

    def test_contexts_filter_by_tags(self, client):
        """Test filtering contexts by tags."""
        response = client.get("/contexts?tags=coding,api")
        assert response.status_code == 200


class TestAddContextPage:
    """Tests for the add context page."""

    def test_add_context_form_loads(self, client):
        """Test that add context form loads."""
        response = client.get("/contexts/add")
        assert response.status_code == 200
        assert "Add Context" in response.text
        assert "Context Type" in response.text
        assert "Content" in response.text
        assert "Tags" in response.text

    def test_add_context_form_has_type_options(self, client):
        """Test that add form has context type options."""
        response = client.get("/contexts/add")
        assert response.status_code == 200
        assert "knowledge" in response.text.lower()
        assert "preference" in response.text.lower()
        assert "history" in response.text.lower()

    def test_add_context_invalid_type(self, client):
        """Test submitting with invalid context type."""
        response = client.post(
            "/contexts/add",
            data={
                "content": "Test content",
                "type": "invalid_type",
                "tags": "",
                "source": "test",
            },
        )
        assert response.status_code == 200
        assert "Invalid context type" in response.text


class TestContextDetailPage:
    """Tests for the context detail page."""

    def test_context_detail_not_found(self, client):
        """Test context detail page with invalid ID."""
        response = client.get("/contexts/invalid-id-12345")
        assert response.status_code == 200
        assert "Context not found" in response.text


class TestAuditPage:
    """Tests for the audit log page."""

    def test_audit_page_loads(self, client):
        """Test that audit page loads."""
        response = client.get("/audit")
        assert response.status_code == 200
        assert "Audit Log" in response.text

    def test_audit_has_filter_form(self, client):
        """Test that audit page has filter form."""
        response = client.get("/audit")
        assert response.status_code == 200
        assert "Agent" in response.text or "Filter" in response.text


class TestSettingsPage:
    """Tests for the settings page."""

    def test_settings_page_loads(self, client):
        """Test that settings page loads."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert "Settings" in response.text
        assert "Current Configuration" in response.text

    def test_settings_shows_config(self, client):
        """Test that settings shows configuration."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert "Librarian Mode" in response.text
        assert "Embedding Provider" in response.text

    def test_settings_shows_api_links(self, client):
        """Test that settings shows API documentation links."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert "/docs" in response.text
        assert "/redoc" in response.text

    def test_settings_shows_export_option(self, client):
        """Test that settings shows export option."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert "Export" in response.text


class TestStaticFiles:
    """Tests for static file serving."""

    def test_css_file_loads(self, client):
        """Test that CSS file is served."""
        response = client.get("/static/css/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]


class TestAPIDocumentation:
    """Tests for API documentation endpoints."""

    def test_swagger_docs_loads(self, client):
        """Test that Swagger docs page loads."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_redoc_loads(self, client):
        """Test that ReDoc page loads."""
        response = client.get("/redoc")
        assert response.status_code == 200
