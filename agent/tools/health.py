"""Container health tool (container_health) via Docker Engine API."""

from __future__ import annotations

from typing import Any, Protocol

import docker
from docker.errors import DockerException, NotFound

# Demo compose sets container_name == service key. Aliases cover underscore /
# compacted spellings agents may pass from OTEL/alert labels.
SERVICE_CONTAINER_ALIASES: dict[str, str] = {
    "product_catalog": "product-catalog",
    "productcatalog": "product-catalog",
    "frontend_proxy": "frontend-proxy",
    "frontendproxy": "frontend-proxy",
    "image_provider": "image-provider",
    "imageprovider": "image-provider",
    "load_generator": "load-generator",
    "loadgenerator": "load-generator",
    "valkey": "valkey-cart",
    "valkey_cart": "valkey-cart",
    "otel_collector": "otel-collector",
    "otelcollector": "otel-collector",
    "astronomy_db": "astronomy-db",
    "astronomydb": "astronomy-db",
    "flagd_ui": "flagd-ui",
    "flagdui": "flagd-ui",
    "opamp_server": "opamp-server",
    "opampserver": "opamp-server",
    "telemetry_docs": "telemetry-docs",
}

# Restart counts at or above this are called out as an unhealthy signal.
HIGH_RESTART_THRESHOLD = 3


class _ContainersAPI(Protocol):
    def get(self, container_id: str) -> Any: ...

    def list(self, **kwargs: Any) -> list[Any]: ...


class _DockerClient(Protocol):
    containers: _ContainersAPI


def _envelope(
    *,
    ok: bool,
    service: str,
    summary: str,
    items: list[dict[str, str]] | None = None,
    raw_refs: list[str] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": ok,
        "kind": "health",
        "service": service,
        "summary": summary,
        "items": items or [],
        "raw_refs": raw_refs or [],
    }
    if error is not None:
        out["error"] = error
    return out


def resolve_container_name(service: str) -> str:
    """Map a demo service / alias name to the compose ``container_name``."""
    key = service.strip()
    if not key:
        return key
    lowered = key.lower()
    if lowered in SERVICE_CONTAINER_ALIASES:
        return SERVICE_CONTAINER_ALIASES[lowered]
    underscored = lowered.replace("-", "_")
    if underscored in SERVICE_CONTAINER_ALIASES:
        return SERVICE_CONTAINER_ALIASES[underscored]
    if "_" in key:
        return key.replace("_", "-")
    return key


def _default_client() -> docker.DockerClient:
    return docker.from_env()


def _attrs(container: Any) -> dict[str, Any]:
    """Return inspect-like attrs; prefer refreshed attrs when available."""
    if hasattr(container, "reload"):
        try:
            container.reload()
        except DockerException:
            pass
    raw = getattr(container, "attrs", None)
    return dict(raw) if isinstance(raw, dict) else {}


def _find_by_compose_label(client: _DockerClient, service: str) -> Any | None:
    """Fallback: match ``com.docker.compose.service`` when name lookup fails."""
    try:
        containers = client.containers.list(all=True)
    except DockerException:
        return None
    target = service.lower()
    for c in containers:
        labels = (_attrs(c).get("Config") or {}).get("Labels") or {}
        if not isinstance(labels, dict):
            labels = getattr(c, "labels", None) or {}
        compose_svc = str(labels.get("com.docker.compose.service") or "").lower()
        if compose_svc == target:
            return c
    return None


def _get_container(client: _DockerClient, container_name: str, service: str) -> Any | None:
    try:
        return client.containers.get(container_name)
    except NotFound:
        return _find_by_compose_label(client, service) or _find_by_compose_label(
            client, container_name
        )


def _state_block(attrs: dict[str, Any]) -> dict[str, Any]:
    state = attrs.get("State")
    return dict(state) if isinstance(state, dict) else {}


def _health_status(state: dict[str, Any]) -> str | None:
    health = state.get("Health")
    if isinstance(health, dict):
        status = health.get("Status")
        return str(status) if status is not None else None
    return None


def _build_items(
    service: str,
    container_name: str,
    attrs: dict[str, Any],
) -> tuple[list[dict[str, str]], list[str]]:
    """Build evidence items and a list of unhealthy signal labels."""
    state = _state_block(attrs)
    status = str(state.get("Status") or "unknown")
    health = _health_status(state)
    # Engine API: RestartCount is top-level on inspect
    restart_count = int(attrs.get("RestartCount") or state.get("RestartCount") or 0)
    oom = bool(state.get("OOMKilled"))
    exit_code = state.get("ExitCode")
    err = str(state.get("Error") or "").strip()

    status_parts = [f"status={status}"]
    if health is not None:
        status_parts.append(f"health={health}")
    status_parts.append(f"container={container_name}")

    items: list[dict[str, str]] = [
        {
            "pointer": f"health:{service}:status",
            "snippet": " ".join(status_parts),
        },
        {
            "pointer": f"health:{service}:restarts",
            "snippet": f"restarts={restart_count}",
        },
        {
            "pointer": f"health:{service}:oom",
            "snippet": f"OOMKilled={str(oom).lower()}",
        },
    ]

    signals: list[str] = []
    if status.lower() != "running":
        signals.append(f"not_running({status})")
    if health is not None and health.lower() == "unhealthy":
        signals.append("health=unhealthy")
    if oom:
        signals.append("OOMKilled")
    if restart_count >= HIGH_RESTART_THRESHOLD:
        signals.append(f"high_restarts({restart_count})")
    if status.lower() != "running" and exit_code not in (None, 0):
        items.append(
            {
                "pointer": f"health:{service}:exit",
                "snippet": f"ExitCode={exit_code}" + (f" error={err}" if err else ""),
            }
        )
        signals.append(f"exit={exit_code}")
    elif err:
        items.append(
            {
                "pointer": f"health:{service}:error",
                "snippet": f"error={err}",
            }
        )
        signals.append("state_error")

    return items, signals


def container_health(
    service: str,
    *,
    client: _DockerClient | None = None,
) -> dict[str, Any]:
    """Return compact Docker health evidence for a named demo service container.

    Works from the host against compose containers (default Docker socket /
    ``DOCKER_HOST``). Never invents status — backend failures set ``ok=False``.
    """
    if not service or not str(service).strip():
        return _envelope(
            ok=False,
            service=service or "",
            summary="service is required for container_health",
            error="missing_service",
        )

    service = str(service).strip()
    container_name = resolve_container_name(service)
    raw_ref = f"docker://{container_name}"

    owns_client = client is None
    docker_client: _DockerClient | None = None
    try:
        try:
            docker_client = client if client is not None else _default_client()
        except DockerException as exc:
            detail = f"{type(exc).__name__}: {exc}"
            return _envelope(
                ok=False,
                service=service,
                summary=f"Docker unreachable: {detail}",
                error=detail,
                raw_refs=[raw_ref],
            )

        try:
            container = _get_container(docker_client, container_name, service)
        except DockerException as exc:
            detail = f"{type(exc).__name__}: {exc}"
            return _envelope(
                ok=False,
                service=service,
                summary=f"Docker unreachable: {detail}",
                error=detail,
                raw_refs=[raw_ref],
            )

        if container is None:
            return _envelope(
                ok=False,
                service=service,
                summary=(
                    f"container not found for service={service!r} "
                    f"(looked up name={container_name!r})"
                ),
                error="not_found",
                raw_refs=[raw_ref],
            )

        attrs = _attrs(container)
        names = attrs.get("Name") or ""
        if isinstance(names, str) and names:
            actual = names.lstrip("/")
            if actual:
                container_name = actual
                raw_ref = f"docker://{container_name}"

        items, signals = _build_items(service, container_name, attrs)
        if signals:
            summary = f"container {container_name}: unhealthy signals — " + ", ".join(signals)
        else:
            state = _state_block(attrs)
            status = str(state.get("Status") or "unknown")
            health = _health_status(state)
            health_bit = f", health={health}" if health is not None else ""
            summary = f"container {container_name}: {status}{health_bit}, no unhealthy signals"

        return _envelope(
            ok=True,
            service=service,
            summary=summary,
            items=items,
            raw_refs=[raw_ref],
        )
    finally:
        if owns_client and docker_client is not None and hasattr(docker_client, "close"):
            try:
                docker_client.close()  # type: ignore[union-attr]
            except DockerException:
                pass
