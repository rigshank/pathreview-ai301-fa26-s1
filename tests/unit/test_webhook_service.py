"""Tests for webhook_service.py"""

import json
from unittest.mock import patch

import httpx
import pytest

from core.services import webhook_service
from core.services.webhook_service import deliver_webhook

CALLBACK_URL = "http://listener.test/hook"
PAYLOAD = {"id": "review-1", "status": "complete"}


def _patch_client(handler):
    """Route deliver_webhook's AsyncClient through an in-memory transport."""
    real_client = httpx.AsyncClient

    def make_client(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    return patch.object(webhook_service.httpx, "AsyncClient", side_effect=make_client)


@pytest.mark.unit
class TestDeliverWebhook:
    """Test suite for deliver_webhook."""

    @pytest.mark.asyncio
    async def test_successful_post_returns_true(self):
        """Test a 2xx response returns True and POSTs the payload as JSON."""
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200)

        with _patch_client(handler) as mock_client:
            result = await deliver_webhook(CALLBACK_URL, PAYLOAD)

        assert result is True
        assert len(requests) == 1
        assert requests[0].method == "POST"
        assert str(requests[0].url) == CALLBACK_URL
        assert json.loads(requests[0].content) == PAYLOAD
        assert mock_client.call_args.kwargs["timeout"] == webhook_service.WEBHOOK_TIMEOUT_SECONDS

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [301, 400, 500])
    async def test_non_2xx_returns_false(self, status_code):
        """Test a non-2xx response returns False without raising."""
        with _patch_client(lambda request: httpx.Response(status_code)):
            result = await deliver_webhook(CALLBACK_URL, PAYLOAD)

        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error",
        [httpx.ConnectError("refused"), httpx.ReadTimeout("timed out")],
    )
    async def test_network_failure_returns_false(self, error):
        """Test connection errors and timeouts return False without raising."""

        def handler(request):
            raise error

        with _patch_client(handler):
            result = await deliver_webhook(CALLBACK_URL, PAYLOAD)

        assert result is False
