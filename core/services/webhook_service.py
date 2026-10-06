import httpx
import structlog

log = structlog.get_logger()

WEBHOOK_TIMEOUT_SECONDS = 10.0


async def deliver_webhook(callback_url: str, payload: dict) -> bool:
    """
    POST a completed review payload to a registered callback URL.
    Never raises; returns True on a 2xx response, False otherwise.
    """
    review_id = payload.get("id")
    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            response = await client.post(callback_url, json=payload)
            response.raise_for_status()

        log.info(
            "webhook_delivered",
            review_id=review_id,
            status_code=response.status_code,
        )
        return True

    except httpx.HTTPStatusError as exc:
        log.warning(
            "webhook_delivery_failed",
            review_id=review_id,
            status_code=exc.response.status_code,
        )
        return False

    except Exception as exc:
        log.warning(
            "webhook_delivery_failed",
            review_id=review_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return False
