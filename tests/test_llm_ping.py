"""Unit tests for D1-04 multi-provider LLM ping (mocked; no live API keys required)."""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from agent.config import (
    DEFAULT_MODELS,
    ConfigError,
    LLMSettings,
    load_llm_settings,
)
from agent.llm import LLMError, PingResult, create_llm_client
from agent.main import main


def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_RETRIES",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "OPENAI_COMPATIBLE_BASE_URL",
        "OPENAI_COMPATIBLE_API_KEY",
        "OLLAMA_BASE_URL",
        "LLM_API_KEY",
        "LLM_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_openai_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        load_llm_settings()


def test_gemini_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        load_llm_settings()


def test_groq_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    with pytest.raises(ConfigError, match="GROQ_API_KEY"):
        load_llm_settings()


def test_openai_compatible_requires_base_url_and_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    with pytest.raises(ConfigError, match="OPENAI_COMPATIBLE_BASE_URL"):
        load_llm_settings()
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://llm.example/v1")
    with pytest.raises(ConfigError, match="LLM_MODEL"):
        load_llm_settings()


def test_ollama_does_not_require_cloud_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    settings = load_llm_settings()
    assert settings.provider == "ollama"
    assert settings.model == DEFAULT_MODELS["ollama"]
    assert settings.openai_api_key is None
    assert settings.gemini_api_key is None
    assert settings.groq_api_key is None


@pytest.mark.parametrize(
    ("provider", "key_env", "key_value"),
    [
        ("openai", "OPENAI_API_KEY", "sk-test-openai"),
        ("gemini", "GEMINI_API_KEY", "gemini-test"),
        ("groq", "GROQ_API_KEY", "gsk-test"),
    ],
)
def test_provider_selection_and_defaults(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    key_env: str,
    key_value: str,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", provider.upper())  # casing tolerated
    monkeypatch.setenv(key_env, key_value)
    settings = load_llm_settings()
    assert settings.provider == provider
    assert settings.model == DEFAULT_MODELS[provider]
    assert settings.timeout_seconds == 20
    assert settings.max_retries == 0


def test_model_override_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    settings = load_llm_settings()
    assert settings.model == "gpt-4o"


def test_invalid_provider_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    with pytest.raises(ConfigError, match="Unsupported LLM_PROVIDER"):
        load_llm_settings()


def test_invalid_timeout_and_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "nope")
    with pytest.raises(ConfigError, match="LLM_TIMEOUT_SECONDS"):
        load_llm_settings()
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "20")
    monkeypatch.setenv("LLM_MAX_RETRIES", "-1")
    with pytest.raises(ConfigError, match="LLM_MAX_RETRIES"):
        load_llm_settings()


def test_unselected_provider_keys_not_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-only-openai")
    # Gemini/Groq keys intentionally absent
    settings = load_llm_settings()
    assert settings.provider == "openai"
    assert settings.gemini_api_key is None
    assert settings.groq_api_key is None


def test_openai_compatible_ignores_openai_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-be-used")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://organiser.example/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "compat-key")
    monkeypatch.setenv("LLM_MODEL", "organiser-model")
    settings = load_llm_settings()
    assert settings.openai_api_key is None
    assert settings.openai_compatible_api_key == "compat-key"
    assert settings.openai_compatible_base_url == "https://organiser.example/v1"
    assert settings.model == "organiser-model"


def test_malformed_base_url_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "not-a-url")
    monkeypatch.setenv("LLM_MODEL", "m")
    with pytest.raises(ConfigError, match="OPENAI_COMPATIBLE_BASE_URL"):
        load_llm_settings()


def test_settings_repr_redacts_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret")
    settings = load_llm_settings()
    text = repr(settings)
    assert "sk-super-secret" not in text
    assert "***" in text


# ---------------------------------------------------------------------------
# Client helpers
# ---------------------------------------------------------------------------


def _fake_openai_response(*, content: str | None, model: str = "returned-model") -> Any:
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], model=model)


@pytest.fixture
def openai_settings() -> LLMSettings:
    return LLMSettings(
        provider="openai",
        model="gpt-4o-mini",
        openai_api_key="sk-test",
    )


def test_create_openai_client_pings_once(
    monkeypatch: pytest.MonkeyPatch,
    openai_settings: LLMSettings,
) -> None:
    mock_create = MagicMock(return_value=_fake_openai_response(content="pong"))
    mock_client = MagicMock()
    mock_client.chat.completions.create = mock_create

    class _FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            assert kwargs["api_key"] == "sk-test"
            assert "base_url" not in kwargs or kwargs.get("base_url") is None

        def __getattr__(self, name: str) -> Any:
            return getattr(mock_client, name)

    monkeypatch.setattr("openai.OpenAI", _FakeOpenAI)
    # Force fresh import path inside client
    client = create_llm_client(openai_settings)
    # Inject by calling ping after patching OpenAI at module used by client
    import openai as openai_mod

    monkeypatch.setattr(openai_mod, "OpenAI", _FakeOpenAI)
    result = client.ping()
    assert result == PingResult(model="returned-model", reply="pong")
    assert mock_create.call_count == 1
    kwargs = mock_create.call_args.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["messages"][0]["content"] == "Reply with exactly: pong"
    assert kwargs["max_completion_tokens"] == 256


def test_groq_uses_groq_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    mock_create = MagicMock(return_value=_fake_openai_response(content="pong"))

    class _FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=mock_create))

    import openai as openai_mod

    monkeypatch.setattr(openai_mod, "OpenAI", _FakeOpenAI)
    settings = LLMSettings(provider="groq", model="openai/gpt-oss-20b", groq_api_key="gsk")
    result = create_llm_client(settings).ping()
    assert result.reply == "pong"
    assert captured["base_url"] == "https://api.groq.com/openai/v1"
    assert captured["api_key"] == "gsk"
    assert mock_create.call_args.kwargs.get("reasoning_effort") == "low"
    assert mock_create.call_args.kwargs.get("max_completion_tokens") == 256


def test_openai_compatible_uses_compat_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    mock_create = MagicMock(return_value=_fake_openai_response(content="ok"))

    class _FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=mock_create))

    import openai as openai_mod

    monkeypatch.setattr(openai_mod, "OpenAI", _FakeOpenAI)
    settings = LLMSettings(
        provider="openai_compatible",
        model="organiser-model",
        openai_compatible_base_url="https://organiser.example/v1",
        openai_compatible_api_key="compat-secret",
    )
    create_llm_client(settings).ping()
    assert captured["base_url"] == "https://organiser.example/v1"
    assert captured["api_key"] == "compat-secret"


def test_empty_reply_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_create = MagicMock(return_value=_fake_openai_response(content="  "))

    class _FakeOpenAI:
        def __init__(self, **_kwargs: Any) -> None:
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=mock_create))

    import openai as openai_mod

    monkeypatch.setattr(openai_mod, "OpenAI", _FakeOpenAI)
    settings = LLMSettings(provider="openai", model="gpt-4o-mini", openai_api_key="sk")
    with pytest.raises(LLMError, match="empty or malformed"):
        create_llm_client(settings).ping()


def test_gemini_ping(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_response = SimpleNamespace(text="pong", model_version="gemini-returned")

    class _FakeModels:
        def generate_content(self, **kwargs: Any) -> Any:
            assert kwargs["model"] == "gemini-3.5-flash-lite"
            assert kwargs["contents"] == "Reply with exactly: pong"
            return mock_response

    class _FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            assert kwargs["api_key"] == "gem-key"
            self.models = _FakeModels()

    fake_genai = SimpleNamespace(Client=_FakeClient)
    monkeypatch.setitem(__import__("sys").modules, "google.genai", fake_genai)
    monkeypatch.setitem(
        __import__("sys").modules,
        "google",
        SimpleNamespace(genai=fake_genai),
    )

    settings = LLMSettings(
        provider="gemini",
        model="gemini-3.5-flash-lite",
        gemini_api_key="gem-key",
    )
    # Patch import inside _GeminiClient
    import agent.llm as llm_mod

    def _fake_get_client(self: Any) -> Any:
        return _FakeClient(api_key=self._api_key)

    monkeypatch.setattr(llm_mod._GeminiClient, "_get_client", _fake_get_client)
    result = create_llm_client(settings).ping()
    assert result.reply == "pong"
    assert result.model == "gemini-returned"


def test_auth_error_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    class AuthenticationError(Exception):
        status_code = 401

    mock_create = MagicMock(side_effect=AuthenticationError("bad key sk-leak"))

    class _FakeOpenAI:
        def __init__(self, **_kwargs: Any) -> None:
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=mock_create))

    import openai as openai_mod

    monkeypatch.setattr(openai_mod, "OpenAI", _FakeOpenAI)
    settings = LLMSettings(provider="openai", model="gpt-4o-mini", openai_api_key="sk")
    with pytest.raises(LLMError, match="Authentication failed") as exc_info:
        create_llm_client(settings).ping()
    assert "sk-leak" not in str(exc_info.value) or "Authentication" in str(exc_info.value)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_ping_llm_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class _FakeClient:
        def ping(self) -> PingResult:
            return PingResult(model="gpt-4o-mini", reply="pong\nextra")

    monkeypatch.setattr("agent.main.create_llm_client", lambda _s: _FakeClient())
    code = main(["ping-llm"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Provider: openai" in out
    assert "Model: gpt-4o-mini" in out
    assert "Reply: pong" in out
    assert "extra" not in out.split("Reply: ", 1)[1].splitlines()[0]


def test_cli_ping_llm_config_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clear_llm_env(monkeypatch)
    # No LLM_PROVIDER
    code = main(["ping-llm"])
    assert code == 2
    err = capsys.readouterr().err
    assert "configuration error" in err
    assert "LLM_PROVIDER" in err


def test_cli_ping_llm_llm_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class _FakeClient:
        def ping(self) -> PingResult:
            raise LLMError("network down")

    monkeypatch.setattr("agent.main.create_llm_client", lambda _s: _FakeClient())
    code = main(["ping-llm"])
    assert code == 1
    assert "llm error: network down" in capsys.readouterr().err


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_PROVIDER") != "openai",
    reason="SKIPPED: live OpenAI smoke requires OPENAI_API_KEY and LLM_PROVIDER=openai",
)
def test_live_openai_smoke_optional() -> None:
    settings = load_llm_settings()
    result = create_llm_client(settings).ping()
    assert result.model
    assert result.reply
