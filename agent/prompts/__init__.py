"""Versioned prompt loading for the agent's LLM stages."""

from __future__ import annotations

from functools import cache
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


@cache
def load_prompt(stage: str) -> str:
    """Load a checked-in prompt by stage name."""
    if stage not in {"investigate", "diagnose", "report"}:
        raise ValueError(f"unknown prompt stage: {stage}")
    path = _PROMPT_DIR / f"{stage}.md"
    return path.read_text(encoding="utf-8")


INVESTIGATE_PROMPT = load_prompt("investigate")
DIAGNOSE_PROMPT = load_prompt("diagnose")

__all__ = ["DIAGNOSE_PROMPT", "INVESTIGATE_PROMPT", "load_prompt"]
