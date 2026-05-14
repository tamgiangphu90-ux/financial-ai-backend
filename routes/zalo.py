import logging
from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, Request

from utils.errors import ServiceError


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zalo", tags=["zalo"])

USER_CONSENT_EVENTS = {
    "user_consent",
    "user_consented",
    "consent",
    "consent_granted",
}
USER_REVOKE_EVENTS = {
    "user_revoke",
    "user_revoked",
    "revoke",
    "consent_revoked",
}
DELETE_USER_DATA_EVENTS = {
    "delete_user_data",
    "user_data_delete",
    "user_data_deleted",
    "delete_data",
}


@router.post("/webhook")
async def zalo_webhook(request: Request):
    try:
        payload = await request.json()
    except (JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Invalid JSON received from Zalo webhook")
        raise ServiceError("Invalid JSON payload", status_code=400, code="invalid_json") from exc

    if not isinstance(payload, dict):
        logger.warning("Invalid Zalo webhook payload type: %s", type(payload).__name__)
        raise ServiceError(
            "JSON payload must be an object",
            status_code=400,
            code="invalid_payload",
        )

    event_type = extract_event_type(payload)
    logger.info("Incoming Zalo webhook event: event_type=%s payload=%s", event_type, payload)

    try:
        await dispatch_zalo_event(event_type, payload)
    except Exception as exc:
        logger.exception("Failed to process Zalo webhook event: event_type=%s", event_type)
        raise ServiceError(
            "Failed to process Zalo webhook",
            status_code=500,
            code="zalo_webhook_error",
        ) from exc

    return {"success": True}


def extract_event_type(payload: dict[str, Any]) -> str:
    event_type = (
        payload.get("event_name")
        or payload.get("event")
        or payload.get("type")
        or payload.get("eventType")
        or "unknown"
    )
    return str(event_type).strip().lower()


async def dispatch_zalo_event(event_type: str, payload: dict[str, Any]) -> None:
    if event_type in USER_CONSENT_EVENTS:
        await handle_user_consent_event(payload)
        return

    if event_type in USER_REVOKE_EVENTS:
        await handle_user_revoke_event(payload)
        return

    if event_type in DELETE_USER_DATA_EVENTS:
        await handle_delete_user_data_event(payload)
        return

    logger.info("No Zalo webhook handler registered for event_type=%s", event_type)


async def handle_user_consent_event(payload: dict[str, Any]) -> None:
    logger.info("Handling Zalo user consent event: payload=%s", payload)


async def handle_user_revoke_event(payload: dict[str, Any]) -> None:
    logger.info("Handling Zalo user revoke event: payload=%s", payload)


async def handle_delete_user_data_event(payload: dict[str, Any]) -> None:
    logger.info("Handling Zalo delete user data event: payload=%s", payload)
