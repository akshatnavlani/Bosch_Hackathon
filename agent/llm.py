"""Provider-aware LLM client for connectivity smoke tests (D1-04)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agent.config import GROQ_BASE_URL, LLMSettings

PING_PROMPT = "Reply with exactly: pong"
# Reasoning models (e.g. Groq openai/gpt-oss-*) spend completion budget on
# hidden thinking first; 16 tokens often yields content=null / finish_reason=length.
PING_MAX_TOKENS = 256


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
        request: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": PING_PROMPT}],
            "temperature": 0,
            # Prefer max_completion_tokens (Groq); max_tokens still works on OpenAI.
            "max_completion_tokens": PING_MAX_TOKENS,
        }
        # gpt-oss / similar reasoning models on Groq need low effort + enough tokens
        # or content comes back empty with finish_reason=length.
        if self.provider == "groq" and _is_reasoning_model(self.model):
            request["reasoning_effort"] = "low"
        try:
            response = client.chat.completions.create(**request)
        except Exception as exc:
            # Older OpenAI-compatible servers may reject max_completion_tokens.
            if "max_completion_tokens" in str(exc).lower():
                fallback = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": PING_PROMPT}],
                    "temperature": 0,
                    "max_tokens": PING_MAX_TOKENS,
                }
                try:
                    response = client.chat.completions.create(**fallback)
                except Exception as retry_exc:
                    raise _normalize_openai_error(retry_exc, self.provider) from retry_exc
            else:
                raise _normalize_openai_error(exc, self.provider) from exc

        reply = _extract_openai_reply(response)
        if not reply:
            finish = _finish_reason(response)
            hint = ""
            if finish == "length":
                hint = (
                    " Completion hit the token limit (often reasoning consumed the budget). "
                    "Try a larger budget or a non-reasoning model."
                )
            raise LLMError(
                f"Provider {self.provider} returned an empty or malformed response.{hint}"
            )
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


def _is_reasoning_model(model: str) -> bool:
    lowered = model.lower()
    return any(token in lowered for token in ("gpt-oss", "qwen3", "muse-spark"))


def _finish_reason(response: Any) -> str | None:
    try:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return None
        reason = getattr(choices[0], "finish_reason", None)
        return str(reason) if reason is not None else None
    except (AttributeError, IndexError, TypeError):
        return None


def _extract_openai_reply(response: Any) -> str:
    try:
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        if message is None:
            return ""
        content = getattr(message, "content", None)
        if content is not None and str(content).strip():
            return str(content).strip()
        # Some providers put the only usable text in reasoning when content is empty.
        reasoning = getattr(message, "reasoning", None)
        if reasoning is not None and str(reasoning).strip():
            return str(reasoning).strip()
        return ""
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
