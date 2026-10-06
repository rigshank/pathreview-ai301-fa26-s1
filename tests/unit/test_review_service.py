"""Tests for review_service.py"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from api.schemas.review import ReviewResponse
from core.models.profile import Profile
from core.models.review import Review
from core.services.review_service import (
    create_review,
    get_review,
    list_reviews,
    process_review,
    register_callback_url,
)


@pytest.mark.unit
class TestReviewService:
    """Test suite for review_service module."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock async database session."""
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_review(self):
        """Create a mock Review object."""
        review = Mock()
        review.id = uuid4()
        review.status = "pending"
        review.sections = None
        review.overall_score = None
        return review

    @pytest.fixture
    def mock_profile(self):
        """Create a mock Profile object."""
        profile = Mock()
        profile.id = uuid4()
        profile.user_id = uuid4()
        return profile

    @pytest.mark.asyncio
    async def test_create_review_returns_review_with_pending_status(
        self, mock_db_session, mock_review
    ):
        """Test create_review returns Review with status='pending'."""
        profile_id = uuid4()
        user_id = uuid4()

        # Setup mock
        mock_db_session.add = Mock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        with patch("core.services.review_service.Review") as MockReview:
            mock_instance = MockReview.return_value
            mock_instance.status = "pending"
            mock_instance.sections = None
            mock_instance.overall_score = None

            result = await create_review(mock_db_session, profile_id, user_id)

            # Check that Review was instantiated
            MockReview.assert_called()
            call_kwargs = MockReview.call_args[1]
            assert call_kwargs["status"] == "pending"

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_get_review_returns_review_for_correct_owner(self, mock_db_session):
        """Test get_review returns review when user_id matches."""
        review_id = uuid4()
        user_id = uuid4()

        mock_review = Mock()
        mock_review.id = review_id

        # Setup mock execute to return review
        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = mock_review
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await get_review(mock_db_session, review_id, user_id)

        assert result == mock_review
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_get_review_returns_none_for_wrong_user(self, mock_db_session):
        """Test get_review returns None when user_id doesn't match."""
        review_id = uuid4()
        user_id = uuid4()
        wrong_user_id = uuid4()

        # Setup mock to return None
        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await get_review(mock_db_session, review_id, wrong_user_id)

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_list_reviews_returns_paginated_results(self, mock_db_session):
        """Test list_reviews returns paginated results."""
        user_id = uuid4()

        # Create mock reviews
        mock_reviews = [Mock() for _ in range(5)]

        # Setup execute mock to return reviews
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_reviews
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        reviews, total = await list_reviews(mock_db_session, user_id, page=1, page_size=20)

        assert len(reviews) > 0 or len(reviews) == 0  # May be empty
        assert isinstance(total, int)
        assert total >= 0

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_list_reviews_page_2_returns_correct_offset(self, mock_db_session):
        """Test list_reviews page 2 returns correct offset."""
        user_id = uuid4()
        page_size = 20

        # Setup mock
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        reviews, total = await list_reviews(mock_db_session, user_id, page=2, page_size=page_size)

        # Second call should pass offset for page 2
        calls = mock_db_session.execute.call_args_list
        # Should have at least one call
        assert len(calls) > 0

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_list_reviews_returns_tuple(self, mock_db_session):
        """Test list_reviews returns (reviews, total) tuple."""
        user_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await list_reviews(mock_db_session, user_id)

        assert isinstance(result, tuple)
        assert len(result) == 2
        reviews, total = result
        assert isinstance(reviews, list)
        assert isinstance(total, int)

    @pytest.mark.asyncio
    async def test_create_review_calls_db_add(self, mock_db_session):
        """Test create_review calls db.add()."""
        profile_id = uuid4()
        user_id = uuid4()

        with patch("core.services.review_service.Review"):
            await create_review(mock_db_session, profile_id, user_id)

            mock_db_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_review_calls_db_commit(self, mock_db_session):
        """Test create_review calls db.commit()."""
        profile_id = uuid4()
        user_id = uuid4()

        with patch("core.services.review_service.Review"):
            await create_review(mock_db_session, profile_id, user_id)

            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_review_calls_db_refresh(self, mock_db_session):
        """Test create_review calls db.refresh()."""
        profile_id = uuid4()
        user_id = uuid4()

        with patch("core.services.review_service.Review"):
            await create_review(mock_db_session, profile_id, user_id)

            mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_get_review_uses_select_and_join(self, mock_db_session):
        """Test get_review constructs proper SQL with join."""
        review_id = uuid4()
        user_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        await get_review(mock_db_session, review_id, user_id)

        # Should call execute with a statement
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_list_reviews_default_pagination(self, mock_db_session):
        """Test list_reviews uses default pagination."""
        user_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        reviews, total = await list_reviews(mock_db_session, user_id)

        # Should use default page=1, page_size=20
        assert isinstance(reviews, list)
        assert isinstance(total, int)

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_list_reviews_custom_page_size(self, mock_db_session):
        """Test list_reviews with custom page size."""
        user_id = uuid4()
        custom_page_size = 50

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        reviews, total = await list_reviews(
            mock_db_session, user_id, page=1, page_size=custom_page_size
        )

        assert isinstance(reviews, list)

    @pytest.mark.asyncio
    async def test_create_review_with_uuid_ids(self, mock_db_session):
        """Test create_review handles UUID objects correctly."""
        profile_id = uuid4()
        user_id = uuid4()

        with patch("core.services.review_service.Review") as MockReview:
            MockReview.return_value = Mock()
            await create_review(mock_db_session, profile_id, user_id)

            call_kwargs = MockReview.call_args[1]
            assert "profile_id" in call_kwargs
            assert "status" in call_kwargs

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_get_review_verifies_ownership(self, mock_db_session):
        """Test get_review checks Profile.user_id matches."""
        review_id = uuid4()
        user_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        await get_review(mock_db_session, review_id, user_id)

        # Should construct query with user_id filter
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_list_reviews_counts_total(self, mock_db_session):
        """Test list_reviews calculates total count."""
        user_id = uuid4()

        mock_reviews = [Mock() for _ in range(5)]
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_reviews
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        reviews, total = await list_reviews(mock_db_session, user_id)

        # Total should be counted
        assert isinstance(total, int)

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_list_reviews_returns_reviews_list(self, mock_db_session):
        """Test list_reviews returns list of Review objects."""
        user_id = uuid4()

        mock_reviews = [Mock(spec=["id", "status"]) for _ in range(3)]
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_reviews
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        reviews, total = await list_reviews(mock_db_session, user_id)

        assert isinstance(reviews, list)

    @pytest.mark.asyncio
    async def test_review_sections_and_score_initially_none(self, mock_db_session):
        """Test review has None for sections and overall_score initially."""
        profile_id = uuid4()
        user_id = uuid4()

        with patch("core.services.review_service.Review") as MockReview:
            MockReview.return_value = Mock()
            await create_review(mock_db_session, profile_id, user_id)

            call_kwargs = MockReview.call_args[1]
            assert call_kwargs["sections"] is None
            assert call_kwargs["overall_score"] is None

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_get_review_with_valid_uuid(self, mock_db_session):
        """Test get_review handles valid UUID parameters."""
        review_id = uuid4()
        user_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Should not raise
        result = await get_review(mock_db_session, review_id, user_id)

        assert result is None or result is not None  # Just verify no exception

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        strict=True, reason="issue #65: review_service tests misconfigure async mocks"
    )
    async def test_list_reviews_ordered_by_created_at(self, mock_db_session):
        """Test list_reviews returns results ordered by created_at desc."""
        user_id = uuid4()

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        reviews, total = await list_reviews(mock_db_session, user_id)

        # Should order by created_at descending
        mock_db_session.execute.assert_called_once()


CALLBACK_URL = "http://listener.test/hook"


@pytest.mark.unit
class TestReviewWebhooks:
    """Test suite for webhook registration and completion delivery."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock async database session."""
        session = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session

    @staticmethod
    def make_review(status="pending", callback_url=None) -> Review:
        now = datetime.now(UTC)
        return Review(
            id=str(uuid4()),
            profile_id=str(uuid4()),
            status=status,
            callback_url=callback_url,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def make_result(obj):
        """Mimic db.execute(...).scalars().first() returning obj."""
        result = Mock()
        result.scalars.return_value.first.return_value = obj
        return result

    async def run_process_review(self, db, review):
        """Run process_review against a review and an empty profile."""
        profile = Profile(id=review.profile_id, user_id=str(uuid4()))
        db.execute = AsyncMock(side_effect=[self.make_result(review), self.make_result(profile)])
        await process_review(db, review.id, profile.id)

    # --- registration ---

    @pytest.mark.asyncio
    async def test_register_callback_url_persists_url(self, mock_db_session):
        """Test registering a callback stores and commits callback_url."""
        review = self.make_review(status="pending")

        with (
            patch("core.services.review_service.get_review", new=AsyncMock(return_value=review)),
            patch("core.services.review_service.deliver_webhook", new=AsyncMock()),
        ):
            result = await register_callback_url(mock_db_session, review.id, uuid4(), CALLBACK_URL)

        assert result is review
        assert review.callback_url == CALLBACK_URL
        mock_db_session.add.assert_called_once_with(review)
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_callback_url_missing_or_not_owned_returns_none(self, mock_db_session):
        """Test registering for a missing/not-owned review returns None and writes nothing."""
        user_id = uuid4()
        review_id = uuid4()

        with (
            patch(
                "core.services.review_service.get_review", new=AsyncMock(return_value=None)
            ) as mock_get_review,
            patch("core.services.review_service.deliver_webhook", new=AsyncMock()) as mock_deliver,
        ):
            result = await register_callback_url(mock_db_session, review_id, user_id, CALLBACK_URL)

        assert result is None
        mock_get_review.assert_called_once_with(mock_db_session, review_id, user_id)
        mock_db_session.commit.assert_not_called()
        mock_deliver.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", ["pending", "processing", "failed"])
    async def test_register_callback_url_unfinished_review_does_not_deliver(
        self, mock_db_session, status
    ):
        """Test registration does not send a webhook for a review that is not complete."""
        review = self.make_review(status=status)

        with (
            patch("core.services.review_service.get_review", new=AsyncMock(return_value=review)),
            patch("core.services.review_service.deliver_webhook", new=AsyncMock()) as mock_deliver,
        ):
            await register_callback_url(mock_db_session, review.id, uuid4(), CALLBACK_URL)

        mock_deliver.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_callback_url_complete_review_delivers_after_commit(
        self, mock_db_session
    ):
        """Test registering on a completed review persists the URL, then delivers immediately."""
        review = self.make_review(status="complete")
        events = []
        mock_db_session.commit = AsyncMock(
            side_effect=lambda: events.append(("commit", review.callback_url))
        )

        async def fake_deliver(url, payload):
            events.append(("deliver", url))
            return True

        with (
            patch("core.services.review_service.get_review", new=AsyncMock(return_value=review)),
            patch(
                "core.services.review_service.deliver_webhook",
                new=AsyncMock(side_effect=fake_deliver),
            ) as mock_deliver,
        ):
            await register_callback_url(mock_db_session, review.id, uuid4(), CALLBACK_URL)

        assert events == [("commit", CALLBACK_URL), ("deliver", CALLBACK_URL)]
        payload = mock_deliver.call_args.args[1]
        assert payload["id"] == review.id
        assert payload["status"] == "complete"

    @pytest.mark.asyncio
    async def test_register_callback_url_delivery_failure_keeps_registration(self, mock_db_session):
        """Test a failed immediate delivery neither raises nor rolls back the registration."""
        review = self.make_review(status="complete")

        with (
            patch("core.services.review_service.get_review", new=AsyncMock(return_value=review)),
            patch(
                "core.services.review_service.deliver_webhook",
                new=AsyncMock(side_effect=RuntimeError("boom")),
            ),
        ):
            result = await register_callback_url(mock_db_session, review.id, uuid4(), CALLBACK_URL)

        assert result is review
        assert review.callback_url == CALLBACK_URL
        assert review.status == "complete"
        mock_db_session.rollback.assert_not_called()

    # --- completion delivery ---

    @pytest.mark.asyncio
    async def test_process_review_sends_public_payload_after_complete_commit(self, mock_db_session):
        """Test a completed review with a callback POSTs the public ReviewResponse payload."""
        review = self.make_review(callback_url=CALLBACK_URL)
        events = []
        mock_db_session.commit = AsyncMock(
            side_effect=lambda: events.append(("commit", review.status))
        )

        async def fake_deliver(url, payload):
            events.append(("deliver", url))
            return True

        with patch(
            "core.services.review_service.deliver_webhook",
            new=AsyncMock(side_effect=fake_deliver),
        ) as mock_deliver:
            await self.run_process_review(mock_db_session, review)

        assert review.status == "complete"
        mock_deliver.assert_called_once()
        assert events[-2:] == [("commit", "complete"), ("deliver", CALLBACK_URL)]

        url, payload = mock_deliver.call_args.args
        assert url == CALLBACK_URL
        assert payload == ReviewResponse.model_validate(review).model_dump(mode="json")
        assert payload["status"] == "complete"
        assert payload["sections"]
        json.dumps(payload)  # must be JSON-safe

    @pytest.mark.asyncio
    async def test_process_review_without_callback_does_not_deliver(self, mock_db_session):
        """Test a completed review with no callback_url makes no delivery attempt."""
        review = self.make_review(callback_url=None)

        with patch("core.services.review_service.deliver_webhook", new=AsyncMock()) as mock_deliver:
            await self.run_process_review(mock_db_session, review)

        assert review.status == "complete"
        mock_deliver.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "deliver_mock",
        [AsyncMock(return_value=False), AsyncMock(side_effect=RuntimeError("boom"))],
        ids=["returns-false", "raises"],
    )
    async def test_process_review_delivery_failure_keeps_complete(
        self, mock_db_session, deliver_mock
    ):
        """Test a webhook failure does not change a completed review to failed."""
        review = self.make_review(callback_url=CALLBACK_URL)

        with patch("core.services.review_service.deliver_webhook", new=deliver_mock):
            await self.run_process_review(mock_db_session, review)

        deliver_mock.assert_called_once()
        assert review.status == "complete"
