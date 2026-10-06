"""Tests for the webhook registration route."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.middleware.auth import get_current_user
from core.database import get_db

CALLBACK_URL = "http://listener.test/hook"


@pytest.mark.unit
class TestRegisterWebhookRoute:
    """Test suite for POST /reviews/{review_id}/webhook."""

    @pytest.fixture
    def current_user(self):
        user = Mock()
        user.id = uuid4()
        return user

    @pytest.fixture
    def client(self, current_user):
        app.dependency_overrides[get_current_user] = lambda: current_user
        app.dependency_overrides[get_db] = lambda: AsyncMock()
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_missing_or_not_owned_review_returns_404(self, client, current_user):
        """Test the route returns 404 when the service finds no owned review."""
        review_id = uuid4()

        with patch(
            "api.routes.webhooks.register_callback_url", new=AsyncMock(return_value=None)
        ) as mock_register:
            response = client.post(
                f"/reviews/{review_id}/webhook", json={"callback_url": CALLBACK_URL}
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Review not found"
        assert mock_register.call_args.kwargs["user_id"] == current_user.id
        assert mock_register.call_args.kwargs["review_id"] == review_id

    def test_registration_returns_confirmation(self, client):
        """Test a successful registration confirms the stored callback URL."""
        review = Mock()
        review.id = uuid4()
        review.callback_url = CALLBACK_URL

        with patch("api.routes.webhooks.register_callback_url", new=AsyncMock(return_value=review)):
            response = client.post(
                f"/reviews/{review.id}/webhook", json={"callback_url": CALLBACK_URL}
            )

        assert response.status_code == 200
        assert response.json() == {
            "review_id": str(review.id),
            "callback_url": CALLBACK_URL,
            "status": "registered",
        }

    def test_invalid_callback_url_returns_422(self, client):
        """Test a non-http(s) callback URL is rejected before reaching the service."""
        with patch("api.routes.webhooks.register_callback_url", new=AsyncMock()) as mock_register:
            response = client.post(
                f"/reviews/{uuid4()}/webhook", json={"callback_url": "ftp://listener.test"}
            )

        assert response.status_code == 422
        mock_register.assert_not_called()
