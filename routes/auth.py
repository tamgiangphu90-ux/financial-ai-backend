import base64
import hashlib
import hmac
import json
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from fastapi import APIRouter
from pydantic import BaseModel, Field

from database.session import sqlite_execute
from utils.config import get_settings
from utils.errors import ServiceError


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

ZALO_PROFILE_URL = "https://graph.zalo.me/v2.0/me"
SESSION_TTL_HOURS = 24 * 30


class ZaloAuthRequest(BaseModel):
    access_token: str = Field(min_length=16)


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _sign(value: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).digest()
    return _urlsafe_b64encode(digest)


def _session_token(payload: dict[str, Any], secret: str) -> str:
    encoded_payload = _urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    return f"{encoded_payload}.{_sign(encoded_payload, secret)}"


def _generate_appsecret_proof(access_token: str, app_secret: str) -> str:
    return hmac.new(
        app_secret.encode("utf-8"),
        access_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _extract_avatar(profile: dict[str, Any]) -> str | None:
    picture = profile.get("picture")
    if isinstance(picture, dict):
        data = picture.get("data")
        if isinstance(data, dict) and isinstance(data.get("url"), str):
            return data["url"]
        if isinstance(picture.get("url"), str):
            return picture["url"]

    avatar = profile.get("avatar")
    return avatar if isinstance(avatar, str) else None


async def _fetch_zalo_profile(access_token: str, app_secret: str) -> dict[str, Any]:
    appsecret_proof = _generate_appsecret_proof(access_token, app_secret)
    params = {
        "access_token": access_token,
        "appsecret_proof": appsecret_proof,
        "fields": "id,name,picture",
    }

    timeout = get_settings().request_timeout
    try:
        response = await asyncio.to_thread(
            requests.get,
            ZALO_PROFILE_URL,
            params=params,
            timeout=timeout,
        )
    except requests.Timeout as exc:
        raise ServiceError("Zalo verification timed out", status_code=504, code="zalo_timeout") from exc
    except requests.RequestException as exc:
        raise ServiceError("Unable to verify Zalo access token", status_code=502, code="zalo_unreachable") from exc

    try:
        data = response.json()
    except ValueError as exc:
        logger.warning("Zalo profile response was not JSON: status=%s body=%s", response.status_code, response.text[:500])
        raise ServiceError("Invalid response from Zalo", status_code=502, code="zalo_invalid_response") from exc

    if response.status_code >= 400 or data.get("error"):
        logger.warning("Zalo token verification failed: status=%s response=%s", response.status_code, data)
        raise ServiceError("Invalid Zalo access token", status_code=401, code="zalo_invalid_token")

    zalo_id = data.get("id")
    if not isinstance(zalo_id, str) or not zalo_id.strip():
        logger.warning("Zalo profile missing id: %s", data)
        raise ServiceError("Zalo profile is missing user id", status_code=502, code="zalo_profile_invalid")

    return data


def _upsert_user(profile: dict[str, Any]) -> dict[str, Any]:
    zalo_id = str(profile["id"]).strip()
    external_id = f"zalo:{zalo_id}"
    display_name = str(profile.get("name") or "Zalo User").strip() or "Zalo User"
    avatar = _extract_avatar(profile)
    metadata = {"provider": "zalo", "zalo_id": zalo_id, "avatar": avatar}

    sqlite_execute(
        """
        INSERT INTO users (external_id, display_name, preferences_json)
        VALUES (?, ?, ?)
        ON CONFLICT(external_id) DO UPDATE SET
            display_name = excluded.display_name
        """,
        (external_id, display_name, json.dumps(metadata, ensure_ascii=False)),
    )
    rows = sqlite_execute(
        "SELECT id, external_id, display_name, created_at FROM users WHERE external_id = ?",
        (external_id,),
    )

    return {
        "id": external_id,
        "zalo_id": zalo_id,
        "name": display_name,
        "avatar": avatar,
        "created_at": rows[0]["created_at"] if rows else None,
    }


@router.post("/zalo")
async def authenticate_zalo(payload: ZaloAuthRequest):
    settings = get_settings()
    if not settings.zalo_app_secret_key:
        raise ServiceError(
            "Zalo authentication is not configured",
            status_code=503,
            code="zalo_secret_missing",
        )

    profile = await _fetch_zalo_profile(payload.access_token, settings.zalo_app_secret_key)
    user = _upsert_user(profile)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
    session_payload = {
        "sub": user["id"],
        "provider": "zalo",
        "exp": int(expires_at.timestamp()),
    }

    return {
        "user": user,
        "session": {
            "token_type": "app_session",
            "session_token": _session_token(session_payload, settings.zalo_app_secret_key),
            "expires_at": expires_at.isoformat(),
        },
    }
