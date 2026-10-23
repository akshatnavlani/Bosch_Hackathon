"""Placeholder tests for safety controls (approval, kill switch, dry-run)."""


def test_safety_package_importable() -> None:
    import agent.safety  # noqa: F401
