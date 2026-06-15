"""Backend selection is the one piece of writer.py worth testing on its own:
it decides, from the pod env alone, whether mentalist talks to Claude or silently
falls back — the exact failure that left v1 running templates in every league game.
The prompts, retry loop, and SDK calls are deliberately NOT tested (no critical
invariant, would just pin implementation; see cue_n_woo_lab/AGENTS.md)."""
import pytest

from mentalist import config
from mentalist.writer import BedrockWriter, LLMWriter


@pytest.fixture(autouse=True)
def _clean_backend_env(monkeypatch):
    for k in ("USE_BEDROCK", "CLAUDE_CODE_USE_BEDROCK", "ANTHROPIC_API_KEY",
              "AWS_PROFILE", "AWS_REGION", "AWS_DEFAULT_REGION",
              "BEDROCK_CLAUDE_MODEL_ID", "ANTHROPIC_API_MODEL_ID"):
        monkeypatch.delenv(k, raising=False)


def test_no_backend_is_fallback_only():
    """No creds in the env -> no client, so the writer returns fallbacks (never raises)."""
    w = LLMWriter()
    assert w.backend == "none"
    assert w.client is None


def test_anthropic_key_selects_direct_api(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    w = LLMWriter()
    assert w.backend == "anthropic"
    assert w.model_id == config.ANTHROPIC_API_MODEL_ID  # bare id, no "us." region prefix


def test_use_bedrock_selects_bedrock_with_inference_profile_id(monkeypatch):
    monkeypatch.setenv("USE_BEDROCK", "true")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    w = LLMWriter()
    assert w.backend == "bedrock"
    assert w.model_id == config.LLM_MODEL_ID
    assert w.model_id.startswith("us.")  # the only model-id form Bedrock accepts for this model


def test_bedrock_takes_precedence_over_api_key(monkeypatch):
    """A belt-and-braces upload may carry both; Bedrock is the hosted default."""
    monkeypatch.setenv("USE_BEDROCK", "true")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    assert LLMWriter().backend == "bedrock"


def test_fallback_only_writer_returns_fallbacks_not_exceptions():
    """The no-backend path must degrade, never crash: a submitted weak answer beats a decline."""
    w = LLMWriter()

    class _Match:
        style = "exaggerated pirate speech, nautical slang"
        score = 0.6

    out = w.blind_answers([_Match()], [], ["What would you do with a free afternoon?"])
    assert len(out) == 1 and out[0]  # non-empty legal fallback


def test_bedrock_writer_alias_preserved():
    assert BedrockWriter is LLMWriter
