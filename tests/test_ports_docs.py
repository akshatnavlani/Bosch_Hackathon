"""CI-safe checks for D1-01 ports doc and smoke script (no live demo calls)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ports_md_exists_and_lists_key_ports() -> None:
    path = ROOT / "docs" / "ports.md"
    assert path.is_file(), "docs/ports.md missing"
    text = path.read_text(encoding="utf-8")
    for needle in ("8080", "9090", "16686", "3000", "4317", "compose.observability.yaml"):
        assert needle in text, f"docs/ports.md must mention {needle!r}"


def test_smoke_demo_script_exists_and_is_executable() -> None:
    path = ROOT / "scripts" / "smoke_demo.sh"
    assert path.is_file(), "scripts/smoke_demo.sh missing"
    assert path.stat().st_mode & 0o111, "scripts/smoke_demo.sh must be executable"
