from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from api.middleware.auth import get_current_user
from api.schemas.review import WebhookRegister, WebhookRegisterResponse
from core.database import get_db
from core.models.user import User
from core.services.review_service import register_callback_url

log = structlog.get_logger()

router = APIRouter(prefix="/reviews", tags=["webhooks"])


@router.post("/{review_id}/webhook", response_model=WebhookRegisterResponse)
async def register_webhook_endpoint(
    review_id: UUID,
    data: WebhookRegister,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Register a callback URL to be notified when a review completes.
    Returns 404 if not found or not owned by current user.
    """
    try:
        review = await register_callback_url(
            db=db,
            review_id=review_id,
            user_id=UUID(str(current_user.id)),
            callback_url=str(data.callback_url),
        )

        if not review:
            log.warning(
                "review_not_found",
                review_id=str(review_id),
                user_id=str(current_user.id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found",
            )

        log.info(
            "webhook_registered",
            review_id=str(review_id),
            user_id=str(current_user.id),
        )

        return WebhookRegisterResponse(
            review_id=UUID(str(review.id)),
            callback_url=str(data.callback_url),
            status="registered",
        )

    except HTTPException:
        raise
    except Exception as exc:
        log.error("webhook_registration_error", error=str(exc))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register webhook",
        )
