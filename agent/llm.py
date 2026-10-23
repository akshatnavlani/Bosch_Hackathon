"""Provider-aware LLM client for connectivity smoke tests (D1-04)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agent.config import GROQ_BASE_URL, LLMSettings

PING_PROMPT = "Reply with exactly: pong"
PING_MAX_TOKENS = 16


class LLMError(RuntimeError):
    """Raised when an LLM request fails or returns an unusable response."""


@dataclass(frozen=True)
class PingResult:
    """Normalized result of a single ping completion."""

    model: str
    reply: str


class LLMClient(Protocol):
    def ping(self) -> PingResult:
        """Send exactly one minimal chat completion."""


def create_llm_client(settings: LLMSettings) -> LLMClient:
    """Build a client for the selected provider."""
    if settings.provider == "openai":
        return _OpenAICompatibleClient(
            provider="openai",
            api_key=settings.openai_api_key or "",
            model=settings.model,
            timeout_seconds=settings.timeout_seconds,
            max_retries=settings.max_retries,
            base_url=None,
        )
    if settings.provider == "gemini":
        return _GeminiClient(
            api_key=settings.gemini_api_key or "",
            model=settings.model,
            timeout_seconds=settings.timeout_seconds,
        )
    if settings.provider == "groq":
        return _OpenAICompatibleClient(
            provider="groq",
            api_key=settings.groq_api_key or "",
            model=settings.model,
            timeout_seconds=settings.timeout_seconds,
            max_retries=settings.max_retries,
            base_url=GROQ_BASE_URL,
        )
    if settings.provider == "openai_compatible":
        return _OpenAICompatibleClient(
            provider="openai_compatible",
            api_key=settings.openai_compatible_api_key or "",
            model=settings.model,
            timeout_seconds=settings.timeout_seconds,
            max_retries=settings.max_retries,
            base_url=settings.openai_compatible_base_url,
            require_api_key=False,
        )
    if settings.provider == "ollama":
        return _OpenAICompatibleClient(
            provider="ollama",
            api_key="ollama",  # OpenAI SDK requires a non-empty key; Ollama ignores it
            model=settings.model,
            timeout_seconds=settings.timeout_seconds,
            max_retries=settings.max_retries,
            base_url=settings.ollama_base_url,
            require_api_key=False,
        )
    raise LLMError(f"Unsupported provider: {settings.provider}")


class _OpenAICompatibleClient:
    """OpenAI SDK client for openai, groq, openai_compatible, and ollama."""

    def __init__(
        self,
        *,
        provider: str,
        api_key: str,
        model: str,
        timeout_seconds: int,
        max_retries: int,
        base_url: str | None,
        require_api_key: bool = True,
    ) -> None:
        self.provider = provider
        self.model = model
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._base_url = base_url
        self._require_api_key = require_api_key
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError(
                "The openai package is required for this provider. "
                'Install it with: pip install -e ".[dev]" (or pip install openai).'
            ) from exc
        if self._require_api_key and not self._api_key:
            raise LLMError(f"Missing API key for provider={self.provider}.")
        kwargs: dict[str, Any] = {
            "api_key": self._api_key or "unused",
            "timeout": self._timeout_seconds,
            "max_retries": self._max_retries,
        }
        if self._base_url:
            kwargs["base_url"] = self._base_url
        self._client = OpenAI(**kwargs)
        return self._client

    def ping(self) -> PingResult:
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": PING_PROMPT}],
                max_tokens=PING_MAX_TOKENS,
                temperature=0,
            )
        except Exception as exc:
            raise _normalize_openai_error(exc, self.provider) from exc

        reply = _extract_openai_reply(response)
        if not reply:
            raise LLMError(f"Provider {self.provider} returned an empty or malformed response.")
        model_id = getattr(response, "model", None) or self.model
        return PingResult(model=str(model_id), reply=reply)


class _GeminiClient:
    """google-genai adapter for Gemini."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.provider = "gemini"
        self.model = model
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from google import genai
        except ImportError as exc:
            raise LLMError(
                "The google-genai package is required for provider=gemini. "
                'Install it with: pip install -e ".[dev]" (or pip install google-genai).'
            ) from exc
        self._client = genai.Client(api_key=self._api_key)
        return self._client

    def ping(self) -> PingResult:
        client = self._get_client()
        try:
            # google-genai uses http_options for timeout in ms when supported
            response = client.models.generate_content(
                model=self.model,
                contents=PING_PROMPT,
                config={
                    "max_output_tokens": PING_MAX_TOKENS,
                    "temperature": 0,
                },
            )
        except Exception as exc:
            raise LLMError(f"Gemini request failed: {_safe_error_message(exc)}") from exc

        reply = _extract_gemini_reply(response)
        if not reply:
            raise LLMError("Provider gemini returned an empty or malformed response.")
        model_id = getattr(response, "model_version", None) or self.model
        return PingResult(model=str(model_id), reply=reply)


def _extract_openai_reply(response: Any) -> str:
    try:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None) if message is not None else None
        if content is None:
            return ""
        return str(content).strip()
    except (AttributeError, IndexError, TypeError):
        return ""


def _extract_gemini_reply(response: Any) -> str:
    text = getattr(response, "text", None)
    if text is not None and str(text).strip():
        return str(text).strip()
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return ""
        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        if not parts:
            return ""
        part_text = getattr(parts[0], "text", None)
        return str(part_text).strip() if part_text is not None else ""
    except (AttributeError, IndexError, TypeError):
        return ""


def _normalize_openai_error(exc: Exception, provider: str) -> LLMError:
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    message = _safe_error_message(exc)
    name = type(exc).__name__
    if "Authentication" in name or status in {401, 403}:
        return LLMError(
            f"Authentication failed for provider={provider}. "
            f"Check the API key for this provider. ({message})"
        )
    if "NotFound" in name or status == 404:
        return LLMError(f"Model or endpoint not found for provider={provider}. ({message})")
    if "Timeout" in name or "timeout" in message.lower():
        return LLMError(
            f"Request timed out for provider={provider}. "
            f"Increase LLM_TIMEOUT_SECONDS or check connectivity. ({message})"
        )
    if "Connection" in name or "connect" in message.lower():
        return LLMError(
            f"Could not reach provider={provider}. "
            f"Check network / base URL / that the server is running. ({message})"
        )
    return LLMError(f"LLM request failed for provider={provider}: {message}")


def _safe_error_message(exc: BaseException) -> str:
    """Stringify an exception without echoing likely secret material."""
    text = str(exc).strip() or type(exc).__name__
    # Collapse overly long SDK dumps; never include Authorization headers.
    lowered = text.lower()
    for needle in ("authorization:", "api-key", "api_key=", "bearer "):
        if needle in lowered:
            return type(exc).__name__
    if len(text) > 300:
        return text[:300] + "…"
    return text
