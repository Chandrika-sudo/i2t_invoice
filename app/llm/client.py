"""OpenAI-compatible LLM client used by the invoice reviewer."""

from __future__ import annotations

import json
import requests

from app.config.settings import get_llm_config
from app.utils.logger import get_logger

logger = get_logger("llm.client")


class LLMError(Exception):
    """Raised when the configured LLM cannot be called successfully."""


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.0,
) -> str:
    """Call an OpenAI-compatible /chat/completions endpoint."""
    config = get_llm_config()
    api_key = config["api_key"]

    if not api_key:
        raise LLMError("LLM_API_KEY is not configured")

    url = f'{config["api_base"].rstrip("/")}/chat/completions'
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config["model"],
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=config["timeout"],
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("LLM request failed: %s", exc)
        raise LLMError(f"LLM request failed: {exc}") from exc

    try:
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty model response")
        return content.strip()
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.error("Unexpected LLM response: %s", exc)
        raise LLMError(f"Unexpected LLM response shape: {exc}") from exc
