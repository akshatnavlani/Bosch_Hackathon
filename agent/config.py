"""Environment and runtime settings for the Incident Zero agent.

Loads LLM (and later observability / Action API) configuration from the
environment via python-dotenv. Only the selected LLM provider's credentials
are required.
"""

from __future__ import annotations

import os
from typing import Literal
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator

load_dotenv()

LLMProvider = Literal["openai", "gemini", "groq", "openai_compatible", "ollama"]

SUPPORTED_PROVIDERS: frozenset[str] = frozenset(
    {"openai", "gemini", "groq", "openai_compatible", "ollama"}
)

DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-3.5-flash-lite",
    "groq": "llama-3.1-8b-instant",
    "ollama": "llama3.2",
}

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_MAX_RETRIES = 0

_SECRET_FIELDS = frozenset(
    {
        "openai_api_key",
        "gemini_api_key",
        "groq_api_key",
        "openai_compatible_api_key",
    }
)


class ConfigError(ValueError):
    """Raised when LLM configuration is missing or invalid."""


class LLMSettings(BaseModel):
    """Normalized LLM settings for the selected provider only."""

    model_config = ConfigDict(extra="forbid")

    provider: LLMProvider
    model: str
    timeout_seconds: int = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0)
    max_retries: int = Field(default=DEFAULT_MAX_RETRIES, ge=0)

    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL

    @field_validator("timeout_seconds", "max_retries", mode="before")
    @classmethod
    def _coerce_int(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("must be an integer")
            return stripped
        return value

    def __repr__(self) -> str:
        data = self.model_dump()
        for key in _SECRET_FIELDS:
            if data.get(key):
                data[key] = "***"
        parts = ", ".join(f"{k}={v!r}" for k, v in data.items())
        return f"LLMSettings({parts})"

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> LLMSettings:
        """Load and validate LLM settings from the environment."""
        env = environ if environ is not None else os.environ
        provider_raw = (env.get("LLM_PROVIDER") or "").strip()
        if not provider_raw:
            raise ConfigError(
                "LLM_PROVIDER is required. "
                f"Supported values: {', '.join(sorted(SUPPORTED_PROVIDERS))}."
            )
        provider = provider_raw.lower()
        if provider not in SUPPORTED_PROVIDERS:
            raise ConfigError(
                f"Unsupported LLM_PROVIDER={provider_raw!r}. "
                f"Supported values: {', '.join(sorted(SUPPORTED_PROVIDERS))}."
            )

        timeout_seconds = _parse_int_env(
            env,
            "LLM_TIMEOUT_SECONDS",
            DEFAULT_TIMEOUT_SECONDS,
            minimum=1,
        )
        max_retries = _parse_int_env(
            env,
            "LLM_MAX_RETRIES",
            DEFAULT_MAX_RETRIES,
            minimum=0,
        )

        model_override = (env.get("LLM_MODEL") or "").strip()
        kwargs: dict[str, object] = {
            "provider": provider,
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
        }

        if provider == "openai":
            key = (env.get("OPENAI_API_KEY") or "").strip()
            if not key:
                raise ConfigError(
                    "Missing OPENAI_API_KEY for provider=openai. "
                    "Set OPENAI_API_KEY in the environment or .env file."
                )
            kwargs["openai_api_key"] = key
            kwargs["model"] = model_override or DEFAULT_MODELS["openai"]

        elif provider == "gemini":
            key = (env.get("GEMINI_API_KEY") or "").strip()
            if not key:
                raise ConfigError(
                    "Missing GEMINI_API_KEY for provider=gemini. "
                    "Set GEMINI_API_KEY in the environment or .env file."
                )
            kwargs["gemini_api_key"] = key
            kwargs["model"] = model_override or DEFAULT_MODELS["gemini"]

        elif provider == "groq":
            key = (env.get("GROQ_API_KEY") or "").strip()
            if not key:
                raise ConfigError(
                    "Missing GROQ_API_KEY for provider=groq. "
                    "Set GROQ_API_KEY in the environment or .env file."
                )
            kwargs["groq_api_key"] = key
            kwargs["model"] = model_override or DEFAULT_MODELS["groq"]

        elif provider == "openai_compatible":
            base_url = (env.get("OPENAI_COMPATIBLE_BASE_URL") or "").strip()
            if not base_url:
                raise ConfigError(
                    "Missing OPENAI_COMPATIBLE_BASE_URL for provider=openai_compatible. "
                    "Set OPENAI_COMPATIBLE_BASE_URL to the organiser chat-completions endpoint."
                )
            _validate_base_url(base_url, "OPENAI_COMPATIBLE_BASE_URL")
            if not model_override:
                raise ConfigError(
                    "LLM_MODEL is required for provider=openai_compatible "
                    "(no default model for organiser endpoints)."
                )
            api_key = (env.get("OPENAI_COMPATIBLE_API_KEY") or "").strip() or None
            kwargs["openai_compatible_base_url"] = base_url.rstrip("/")
            kwargs["openai_compatible_api_key"] = api_key
            kwargs["model"] = model_override

        else:  # ollama
            base_url = (
                env.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL
            ).strip() or DEFAULT_OLLAMA_BASE_URL
            _validate_base_url(base_url, "OLLAMA_BASE_URL")
            kwargs["ollama_base_url"] = base_url.rstrip("/")
            kwargs["model"] = model_override or DEFAULT_MODELS["ollama"]

        try:
            return cls(**kwargs)
        except Exception as exc:  # pydantic ValidationError
            raise ConfigError(f"Invalid LLM configuration: {exc}") from exc


def load_llm_settings(environ: dict[str, str] | None = None) -> LLMSettings:
    """Public helper used by the CLI and tests."""
    return LLMSettings.from_env(environ)


def _parse_int_env(
    env: dict[str, str],
    name: str,
    default: int,
    *,
    minimum: int,
) -> int:
    raw = env.get(name)
    if raw is None or not str(raw).strip():
        return default
    text = str(raw).strip()
    try:
        value = int(text)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer (got {text!r}).") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be >= {minimum} (got {value}).")
    return value


def _validate_base_url(url: str, var_name: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError(f"{var_name} must be an absolute http(s) URL with a host (got {url!r}).")
