import asyncio
import logging
import re

import requests

from utils.config import get_settings


logger = logging.getLogger(__name__)


class LLMProvider:
    """Small provider wrapper so app logic does not depend on one LLM API shape."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.hf_token)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback: str,
        max_tokens: int = 520,
        temperature: float = 0.75,
    ) -> str:
        if not self.settings.hf_token:
            return fallback

        payload = {
            "model": self.settings.hf_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.hf_token}",
            "Content-Type": "application/json",
        }

        try:
            response = await asyncio.to_thread(
                requests.post,
                self.settings.hf_api_url,
                headers=headers,
                json=payload,
                timeout=60,
            )
            if response.status_code >= 400:
                logger.warning("LLM request failed with status %s: %s", response.status_code, response.text[:300])
                return fallback
            data = response.json()
            answer = data["choices"][0]["message"]["content"].strip()
            if not answer or self._looks_like_repeated_fallback(answer, fallback):
                return fallback
            return answer
        except Exception as exc:
            logger.exception("LLM request failed: %s", exc)
            return fallback

    def _looks_like_repeated_fallback(self, answer: str, fallback: str) -> bool:
        answer_norm = self._normalize(answer)
        fallback_norm = self._normalize(fallback)
        if not answer_norm:
            return True
        if fallback_norm and answer_norm == fallback_norm:
            return True
        if fallback_norm and answer_norm.count(fallback_norm[: min(120, len(fallback_norm))]) > 1:
            return True

        paragraphs = [self._normalize(item) for item in re.split(r"\n{2,}", answer) if item.strip()]
        unique = set(paragraphs)
        return len(paragraphs) >= 4 and len(unique) <= max(1, len(paragraphs) // 2)

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()
