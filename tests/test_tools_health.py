"""Unit tests for container_health (D1-09) — mocked Docker, no live daemon required."""

from __future__ import annotations

from typing import Any

import pytest
from agent.tools.health import (
    HIGH_RESTART_THRESHOLD,
    container_health,
    resolve_container_name,
)
from docker.errors import APIError, DockerException, NotFound


class _FakeContainer:
    def __init__(self, attrs: dict[str, Any]):
        self.attrs = attrs
        self.labels = (attrs.get("Config") or {}).get("Labels") or {}

    def reload(self) -> None:
        return None


class _FakeContainers:
    def __init__(
        self,
        by_name: dict[str, _FakeContainer] | None = None,
        *,
        get_error: Exception | None = None,
        list_containers: list[_FakeContainer] | None = None,
    ):
        self.by_name = by_name or {}
        self.get_error = get_error
        self.list_containers = list_containers

    def get(self, container_id: str) -> _FakeContainer:
        if self.get_error is not None:
            raise self.get_error
        if container_id not in self.by_name:
            raise NotFound(f"Not found: {container_id}")
        return self.by_name[container_id]

    def list(self, **_kwargs: Any) -> list[_FakeContainer]:
        if self.list_containers is not None:
            return self.list_containers
        return list(self.by_name.values())


class _FakeDockerClient:
    def __init__(self, containers: _FakeContainers):
        self.containers = containers
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _inspect(
    *,
    name: str = "payment",
    status: str = "running",
    health: str | None = "healthy",
    restart_count: int = 0,
    oom: bool = False,
    exit_code: int = 0,
    error: str = "",
    compose_service: str | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "Status": status,
        "OOMKilled": oom,
        "ExitCode": exit_code,
        "Error": error,
    }
    if health is not None:
        state["Health"] = {"Status": health}
    labels: dict[str, str] = {}
    if compose_service is not None:
        labels["com.docker.compose.service"] = compose_service
    return {
        "Name": f"/{name}",
        "RestartCount": restart_count,
        "State": state,
        "Config": {"Labels": labels},
    }


def test_resolve_container_name_aliases() -> None:
    assert resolve_container_name("payment") == "payment"
    assert resolve_container_name("product_catalog") == "product-catalog"
    assert resolve_container_name("productcatalog") == "product-catalog"
    assert resolve_container_name("valkey") == "valkey-cart"


def test_container_health_running_healthy() -> None:
    client = _FakeDockerClient(
        _FakeContainers({"payment": _FakeContainer(_inspect(name="payment"))})
    )
    result = container_health("payment", client=client)

    assert result["ok"] is True
    assert result["kind"] == "health"
    assert result["service"] == "payment"
    assert result["raw_refs"] == ["docker://payment"]
    pointers = {i["pointer"] for i in result["items"]}
    assert "health:payment:status" in pointers
    assert "health:payment:restarts" in pointers
    assert "health:payment:oom" in pointers
    status_item = next(i for i in result["items"] if i["pointer"].endswith(":status"))
    assert "status=running" in status_item["snippet"]
    assert "health=healthy" in status_item["snippet"]
    restarts = next(i for i in result["items"] if i["pointer"].endswith(":restarts"))
    assert restarts["snippet"] == "restarts=0"
    oom = next(i for i in result["items"] if i["pointer"].endswith(":oom"))
    assert "OOMKilled=false" in oom["snippet"]
    assert "no unhealthy signals" in result["summary"]


def test_container_health_unhealthy_signals() -> None:
    client = _FakeDockerClient(
        _FakeContainers(
            {
                "payment": _FakeContainer(
                    _inspect(
                        name="payment",
                        status="exited",
                        health="unhealthy",
                        restart_count=HIGH_RESTART_THRESHOLD,
                        oom=True,
                        exit_code=137,
                        error="killed",
                    )
                )
            }
        )
    )
    result = container_health("payment", client=client)

    assert result["ok"] is True
    assert "unhealthy signals" in result["summary"]
    assert "OOMKilled" in result["summary"]
    assert "health=unhealthy" in result["summary"]
    assert "high_restarts" in result["summary"]
    assert any(i["pointer"] == "health:payment:exit" for i in result["items"])


def test_container_health_alias_lookup() -> None:
    client = _FakeDockerClient(
        _FakeContainers(
            {
                "product-catalog": _FakeContainer(
                    _inspect(name="product-catalog", compose_service="product-catalog")
                )
            }
        )
    )
    result = container_health("product_catalog", client=client)
    assert result["ok"] is True
    assert result["service"] == "product_catalog"
    assert "docker://product-catalog" in result["raw_refs"]


def test_container_health_compose_label_fallback() -> None:
    # Name lookup fails; label scan finds the container
    labeled = _FakeContainer(_inspect(name="weird-prefix-payment", compose_service="payment"))
    containers = _FakeContainers(by_name={}, list_containers=[labeled])
    client = _FakeDockerClient(containers)
    result = container_health("payment", client=client)
    assert result["ok"] is True
    assert result["raw_refs"] == ["docker://weird-prefix-payment"]


def test_container_health_missing_service() -> None:
    result = container_health("")
    assert result["ok"] is False
    assert result["kind"] == "health"
    assert "service" in result["summary"].lower()
    assert result.get("error") == "missing_service"
    assert result["items"] == []


def test_container_health_not_found() -> None:
    client = _FakeDockerClient(_FakeContainers({}))
    result = container_health("payment", client=client)
    assert result["ok"] is False
    assert result["items"] == []
    assert result.get("error") == "not_found"
    assert "not found" in result["summary"].lower()


def test_container_health_docker_unreachable() -> None:
    client = _FakeDockerClient(_FakeContainers(get_error=APIError("connection refused")))
    result = container_health("payment", client=client)
    assert result["ok"] is False
    assert result["items"] == []
    assert "Docker unreachable" in result["summary"]
    assert result.get("error")


def test_container_health_from_env_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> Any:
        raise DockerException("Cannot connect to Docker daemon")

    monkeypatch.setattr("agent.tools.health._default_client", _boom)
    result = container_health("payment")
    assert result["ok"] is False
    assert "Docker unreachable" in result["summary"]


@pytest.mark.skipif(
    True,
    reason=("SKIPPED: live Docker smoke not required for D1-09 CI; mock tests cover acceptance"),
)
def test_live_docker_smoke_optional() -> None:
    result = container_health("frontend")
    assert "ok" in result
