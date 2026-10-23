"""Policy and graph loading checks for the stage prompts."""

from agent.graph import STAGE_PROMPTS
from agent.prompts import DIAGNOSE_PROMPT, INVESTIGATE_PROMPT, load_prompt


def test_prompts_forbid_feature_flag_diagnosis() -> None:
    for prompt in (INVESTIGATE_PROMPT, DIAGNOSE_PROMPT):
        lowered = prompt.lower()
        assert "feature-flag" in lowered
        assert "flagd" in lowered
        assert "telemetry only" in lowered


def test_prompts_require_verbatim_evidence_citations_and_escalation() -> None:
    for prompt in (INVESTIGATE_PROMPT, DIAGNOSE_PROMPT):
        lowered = prompt.lower()
        assert "pointer" in lowered
        assert "snippet" in lowered
        assert "verbatim" in lowered
        assert "escalat" in lowered
        assert "guess" in lowered


def test_graph_loads_versioned_stage_prompts() -> None:
    assert STAGE_PROMPTS["investigate"] == load_prompt("investigate")
    assert STAGE_PROMPTS["diagnose"] == load_prompt("diagnose")
    assert "v1" in STAGE_PROMPTS["investigate"]
    assert "v1" in STAGE_PROMPTS["diagnose"]


def test_unknown_prompt_stage_is_rejected() -> None:
    try:
        load_prompt("feature_flags")
    except ValueError as exc:
        assert "unknown prompt stage" in str(exc)
    else:
        raise AssertionError("unknown prompt stage should be rejected")
