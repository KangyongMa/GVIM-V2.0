"""OpenAI-compatible JSON helpers for LLM-driven chemistry planning."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def _env_float(name: str, default: float, *, minimum: float = 1.0, maximum: float = 120.0) -> float:
    raw_value = os.environ.get(name)
    if raw_value is None or raw_value == "":
        return default
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def _coerce_timeout(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1.0, min(120.0, parsed))


def resolve_chemistry_llm_settings(mode: str = "smart") -> Dict[str, str]:
    """Resolve the chemistry LLM provider for structured JSON calls."""
    provider = str(
        os.environ.get("CHEMISTRY_STUDIO_LLM_PROVIDER")
        or os.environ.get("CHEMISTRY_COPILOT_LLM_PROVIDER")
        or ""
    ).strip().lower()
    deepseek_key = str(os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    openai_key = str(os.environ.get("OPENAI_API_KEY") or "").strip()

    if not provider:
        if deepseek_key:
            provider = "deepseek"
        elif openai_key:
            provider = "openai"

    raw_model = str(
        os.environ.get("CHEMISTRY_STUDIO_LLM_MODEL")
        or os.environ.get("CHEMISTRY_COPILOT_LLM_MODEL")
        or ""
    ).strip()
    raw_base_url = str(
        os.environ.get("CHEMISTRY_STUDIO_LLM_BASE_URL")
        or os.environ.get("CHEMISTRY_COPILOT_LLM_BASE_URL")
        or ""
    ).strip()

    if provider == "deepseek":
        model = raw_model or str(os.environ.get("DEEPSEEK_MODEL") or "").strip()
        if not model:
            model = "deepseek-v4-pro" if mode == "deep" else "deepseek-v4-flash"
        if model.startswith("deepseek/"):
            model = model.split("/", 1)[1]
        return {
            "provider": "deepseek",
            "api_key": deepseek_key,
            "base_url": raw_base_url
            or str(os.environ.get("DEEPSEEK_BASE_URL") or "").strip()
            or "https://api.deepseek.com/v1",
            "model": model,
        }

    if provider == "openai":
        model = raw_model or str(os.environ.get("OPENAI_MODEL") or "").strip()
        if not model:
            model = "gpt-4o-mini"
        if model.startswith("openai/"):
            model = model.split("/", 1)[1]
        return {
            "provider": "openai",
            "api_key": openai_key,
            "base_url": raw_base_url
            or str(os.environ.get("OPENAI_BASE_URL") or "").strip()
            or "https://api.openai.com/v1",
            "model": model,
        }

    return {}


def post_chemistry_llm_json(
    *,
    messages: List[Dict[str, Any]],
    mode: str = "smart",
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    timeout: float | None = None,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, str]]:
    """Call the configured chemistry LLM and parse strict JSON output."""
    settings = resolve_chemistry_llm_settings(mode=mode)
    api_key = str(settings.get("api_key") or "").strip()
    base_url = str(settings.get("base_url") or "").strip().rstrip("/")
    model = str(settings.get("model") or "").strip()
    if not api_key or not base_url or not model:
        return None, settings

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    provider = str(settings.get("provider") or "").strip().lower()
    model_key = model.lower()
    deepseek_thinking = (
        provider == "deepseek"
        and model_key in {"deepseek-v4-flash", "deepseek-v4-pro"}
        and str(mode or "").strip().lower() == "deep"
    )
    if not deepseek_thinking:
        payload["temperature"] = temperature
    if isinstance(max_tokens, int) and max_tokens > 0:
        payload["max_tokens"] = max_tokens
    if provider == "deepseek" and model_key in {"deepseek-v4-flash", "deepseek-v4-pro"}:
        payload["thinking"] = {"type": "enabled" if deepseek_thinking else "disabled"}

    request_timeout = _coerce_timeout(
        timeout,
        _env_float("CHEMISTRY_STUDIO_LLM_TIMEOUT_SEC", 30.0, minimum=3.0, maximum=120.0),
    )
    session = requests.Session()
    session.trust_env = False
    try:
        try:
            response = session.post(
                f"{base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json=payload,
                timeout=request_timeout,
            )
        except requests.RequestException as exc:
            logger.warning(
                "Chemistry LLM request failed (provider=%s, model=%s, timeout=%.1fs): %s",
                provider or "unknown",
                model,
                request_timeout,
                exc,
            )
            return None, settings
        if response.status_code != 200:
            logger.warning(
                "Chemistry LLM request returned HTTP %s (provider=%s, model=%s): %s",
                response.status_code,
                provider or "unknown",
                model,
                response.text[:400],
            )
            return None, settings
        try:
            data = response.json()
        except ValueError as exc:
            logger.warning(
                "Chemistry LLM returned invalid JSON (provider=%s, model=%s): %s",
                provider or "unknown",
                model,
                exc,
            )
            return None, settings
    finally:
        session.close()

    content = str(
        ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    ).strip()
    if not content:
        return None, settings
    try:
        return json.loads(content), settings
    except ValueError as exc:
        logger.warning(
            "Chemistry LLM returned non-JSON content (provider=%s, model=%s): %s",
            provider or "unknown",
            model,
            exc,
        )
        return None, settings
