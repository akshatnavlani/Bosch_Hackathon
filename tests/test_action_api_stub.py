"""Tests for the stub Action API client (D1-13). No network, no real writes."""

import logging

import pytest
from agent.adapters.action_api import ActionAPIClient
from agent.adapters.stubs import StubTransport


def test_all_methods_return_ok_stub() -> None:
    client = ActionAPIClient(base_url="http://example.test")
    results = [
        client.restart("payment"),
        client.toggle_flag("example-flag", True),
        client.throttle_loadgen(5),
        client.scale("cart", 2),
    ]
    for result in results:
        assert result["ok"] is True
        assert result["stub"] is True


def test_restart_payload_shape() -> None:
    result = ActionAPIClient(base_url="").restart("payment")
    assert result["payload"] == {"action_type": "restart", "target": "payment", "params": {}}


def test_default_transport_is_stub_and_records_calls() -> None:
    client = ActionAPIClient()
    client.scale("cart", 3)
    assert isinstance(client.transport, StubTransport)
    assert client.transport.calls == [
        {"action_type": "scale", "target": "cart", "params": {"replicas": 3}}
    ]


def test_stub_logs_payload(caplog: pytest.LogCaptureFixture) -> None:
    client = ActionAPIClient(base_url="")
    with caplog.at_level(logging.INFO):
        client.restart("payment")
    assert "payment" in caplog.text


def test_base_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACTION_API_URL", "http://action.test:9000")
    assert ActionAPIClient().base_url == "http://action.test:9000"


def test_base_url_defaults_to_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ACTION_API_URL", raising=False)
    assert ActionAPIClient().base_url == ""