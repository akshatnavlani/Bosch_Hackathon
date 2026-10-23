"""CI-safe checks for D1-12 CP1 architecture one-pager (no live demo calls)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_architecture_one_pager_exists_and_covers_required_topics() -> None:
    path = ROOT / "docs" / "architecture-one-pager.md"
    assert path.is_file(), "docs/architecture-one-pager.md missing"
    text = path.read_text(encoding="utf-8").lower()
    for needle in (
        "components",
        "tools",
        "decision flow",
        "safety",
        "langgraph",
        "query_metrics",
        "query_traces",
        "query_logs",
        "container_health",
        "kill switch",
        "flagd",
        "paymentfailure",
        "p1",
    ):
        assert needle in text, f"docs/architecture-one-pager.md must mention {needle!r}"


def test_readme_links_architecture_one_pager() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/architecture-one-pager.md" in readme, (
        "README.md must link docs/architecture-one-pager.md"
    )
