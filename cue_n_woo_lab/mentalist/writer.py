"""LLMWriter — Claude writes short, on-topic answers in the classified style.

The probes showed the winning answer needs BOTH ingredients: genuine topical
quality (the LLM's job) and the judge's style as an early-diverging tilt (the
classifier label + the real judge transcript as few-shot evidence). Pure style
markers lose 0%; generic-plain is a coin flip (probe finding 3).

**Dual backend.** The writer talks to Claude through the `anthropic` SDK, which
exposes the same `messages.create` + tool-use API over two transports, selected
at runtime (config.resolve_backend / the same convention as crewrift's suspectra):

- **Bedrock** (`USE_BEDROCK=true`, set by `upload-policy --use-bedrock`): the
  hosted pod runs under the tournament Bedrock IRSA role; creds come from that
  role, region from AWS_REGION (the platform injects it). No API key needed.
- **Anthropic API** (`ANTHROPIC_API_KEY` present): a direct key, attached at
  upload via `--secret-env ANTHROPIC_API_KEY=...`. The infra-independent path —
  works even when the pod's Bedrock model access is unavailable.

Why two: hosted Bedrock model access has failed before (a stale upload predating
the platform's player-pod secret-env fix; see WORKING_CONTEXT), and a single
backend is a single point of failure. With both wired, an upload can carry a key
as belt-and-braces even when relying on Bedrock.

Every public method degrades gracefully: if no backend is configured or the call
fails, the caller gets deterministic fallback answers, never an exception — a
weak submitted answer strictly beats a crash or a decline (decline scores 0; a
real answer facing a decline takes 110 uncontested).
"""
from __future__ import annotations

import os
import re
import sys
import time
from typing import Any

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

from . import config
from .validator import repair_answer

# Anthropic SDK exceptions worth retrying (transient): timeouts, connection
# drops, 429s, and 5xx. Other APIStatusError codes (4xx auth/validation/access)
# are permanent — fail fast to the deterministic fallback.
_RETRYABLE_EXC = (APIConnectionError, APITimeoutError, RateLimitError)

_ANSWERS_TOOL = {
    "name": "submit_answers",
    "description": "Submit the final answers, one per question, in order.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["answers"],
        "properties": {
            "answers": {"type": "array", "items": {"type": "string"}},
        },
    },
}


def _log(msg: str) -> None:
    print(f"[mentalist.writer] {msg}", file=sys.stderr, flush=True)


def _style_brief(style_matches: list[Any]) -> str:
    """Describe the classification to Claude: confident label, or hedged top-3."""
    top = style_matches[0]
    if top.score < config.LOW_CONFIDENCE_COSINE:
        return (
            "Our style classifier found NO good match in the known style pool, so rely on "
            "the transcript excerpts alone to infer the judge's voice."
        )
    lines = [f'The judge\'s hidden style is almost certainly: "{top.style}".']
    runners = [m for m in style_matches[1:] if m.score > 0.6 * top.score]
    if runners:
        alts = "; ".join(f'"{m.style}"' for m in runners)
        lines.append(f"Close runner-up styles (hedge toward wording that also fits these): {alts}.")
    return " ".join(lines)


def _transcript_block(transcript: list[dict[str, str]]) -> str:
    if not transcript:
        return "(no private transcript available)"
    parts = []
    for i, turn in enumerate(transcript, 1):
        parts.append(f"Q{i}: {turn.get('question', '')}\nJudge: {turn.get('answer', '')}")
    return "\n\n".join(parts)


_RULES = (
    "Rules for every answer you write:\n"
    "- It must genuinely, sensibly answer its question. This matters most: an answer that is "
    "pure style flavor but doesn't really answer the question always loses.\n"
    "- Phrase it the way the JUDGE would phrase it — its vocabulary, tone, and verbal tics — "
    "with the most style-distinctive wording in the FIRST one or two words (the scorer weighs "
    "the first word where the two candidate answers differ; never open with a generic phrase "
    "that echoes the question).\n"
    "- At most 12 space-separated words. Shorter and punchier is better.\n"
    "- Plain printable ASCII only: no curly quotes, no em dashes, no newlines, single spaces.\n"
)


class LLMWriter:
    """Claude writer over the anthropic SDK; Bedrock or direct-API backend.

    Construction never raises: if no backend is configured the writer is a
    no-op that always returns deterministic fallbacks, so the harness can use it
    unconditionally.
    """

    def __init__(self) -> None:
        self.model_id = os.environ.get("BEDROCK_CLAUDE_MODEL_ID") or config.LLM_MODEL_ID
        self.client, self.backend = self._build_client()
        if self.client is None:
            _log("no LLM backend configured (USE_BEDROCK unset, ANTHROPIC_API_KEY absent); fallback-only")
        else:
            _log(f"LLM backend: {self.backend}, model {self.model_id}")

    @staticmethod
    def _truthy(name: str) -> bool:
        return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}

    def _build_client(self) -> tuple[Any, str]:
        """Pick a backend from the environment. Bedrock takes precedence (the
        hosted default), then a direct Anthropic key, else no client."""
        timeout = float(config.LLM_TIMEOUT_SECONDS)
        if self._truthy("USE_BEDROCK") or self._truthy("CLAUDE_CODE_USE_BEDROCK"):
            from anthropic import AnthropicBedrock

            region = (
                os.environ.get("AWS_REGION")
                or os.environ.get("AWS_DEFAULT_REGION")
                or config.BEDROCK_REGION
            )
            client = AnthropicBedrock(
                aws_region=region,
                aws_access_key=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
                aws_profile=os.environ.get("AWS_PROFILE"),
                timeout=timeout,
                max_retries=0,  # we own retries (_call_with_retry)
            )
            return client, "bedrock"
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            from anthropic import Anthropic

            model = os.environ.get("ANTHROPIC_API_MODEL_ID") or config.ANTHROPIC_API_MODEL_ID
            self.model_id = model
            return Anthropic(api_key=api_key, timeout=timeout, max_retries=0), "anthropic"
        return None, "none"

    def blind_answers(
        self,
        style_matches: list[Any],
        transcript: list[dict[str, str]],
        questions: list[str],
        prior_error: str | None = None,
    ) -> list[str]:
        """In-style, on-topic answers to the opponent's challenge questions."""
        prompt = (
            "You are competing in a two-player game judged by a language model that has been "
            "steered to write in a hidden style. For each question below, the judge will pick "
            "between your answer and an opponent's answer, preferring the one that best answers "
            "the question in its own voice. The opponent answers blind and will likely sound "
            "generic — your edge is sounding like the judge while answering at least as well.\n\n"
            f"{_style_brief(style_matches)}\n\n"
            "The judge's actual writing (its answers to our private interview):\n"
            f"{_transcript_block(transcript)}\n\n"
            f"{_RULES}\n"
            f"{'Previous attempt was rejected: ' + prior_error if prior_error else ''}\n"
            "Questions to answer, in order:\n"
            + "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
            + "\n\nCall submit_answers with one answer per question, same order."
        )
        fallbacks = [self.fallback_answer(q, style_matches) for q in questions]
        return self._call_for_answers(prompt, len(questions), fallbacks)

    def proposal_answers(
        self,
        style_matches: list[Any],
        transcript: list[dict[str, str]],
        questions: list[str],
        prior_error: str | None = None,
    ) -> list[str]:
        """Our secret answers to our own challenge questions.

        Same job as blind_answers plus one extra pressure: a blind opponent must
        NOT produce the same answer (equal/prefix answers trigger the 40/40
        duplicate-conflict penalty), so distinctive in-style specifics beat
        universally obvious ones.
        """
        prompt = (
            "You are competing in a two-player game judged by a language model that has been "
            "steered to write in a hidden style. The questions below are OUR challenge "
            "questions; you write our secret answer to each. The judge will later pick between "
            "our answer and a blind opponent's answer to the same question, preferring the one "
            "that best answers it in the judge's own voice.\n\n"
            f"{_style_brief(style_matches)}\n\n"
            "The judge's actual writing (its answers to our private interview):\n"
            f"{_transcript_block(transcript)}\n\n"
            f"{_RULES}"
            "- Extra rule for these secret answers: avoid the single most obvious generic answer "
            "(if the opponent writes the same or a prefix of ours, both sides are penalized). "
            "Prefer a specific, judge-flavored take a generic answerer would not produce.\n\n"
            f"{'Previous attempt was rejected: ' + prior_error if prior_error else ''}\n"
            "Our challenge questions, in order:\n"
            + "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
            + "\n\nCall submit_answers with one answer per question, same order."
        )
        fallbacks = [self.fallback_answer(q, style_matches) for q in questions]
        return self._call_for_answers(prompt, len(questions), fallbacks)

    def _call_for_answers(self, prompt: str, n: int, fallbacks: list[str]) -> list[str]:
        if self.client is None:
            return fallbacks
        try:
            raw = self._call_with_retry(prompt)
        except Exception as exc:  # any LLM failure -> deterministic fallback
            _log(f"{self.backend} call failed ({exc!r}); using fallback answers")
            return fallbacks
        answers = [str(a) for a in raw][:n]
        while len(answers) < n:
            answers.append(fallbacks[len(answers)])
        return [repair_answer(a, fallback=fallbacks[i]) for i, a in enumerate(answers)]

    def _call_with_retry(self, prompt: str) -> list[Any]:
        last_exc: Exception | None = None
        for attempt in range(config.LLM_ATTEMPTS):
            try:
                t0 = time.time()
                response = self.client.messages.create(
                    model=self.model_id,
                    max_tokens=config.LLM_MAX_TOKENS,
                    tools=[_ANSWERS_TOOL],
                    tool_choice={"type": "tool", "name": "submit_answers"},
                    messages=[{"role": "user", "content": prompt}],
                )
                _log(f"{self.backend} ok in {time.time() - t0:.1f}s (attempt {attempt + 1})")
                for block in response.content:
                    if getattr(block, "type", None) == "tool_use" and block.name == "submit_answers":
                        return block.input["answers"]
                raise RuntimeError("Claude did not call submit_answers")
            except _RETRYABLE_EXC as exc:
                last_exc = exc
                if attempt == config.LLM_ATTEMPTS - 1:
                    raise
                time.sleep(2 ** attempt)
            except APIStatusError as exc:
                # 5xx is transient; 4xx (auth/access/validation) is permanent.
                last_exc = exc
                if exc.status_code < 500 or attempt == config.LLM_ATTEMPTS - 1:
                    raise
                time.sleep(2 ** attempt)
        raise last_exc or RuntimeError("LLM retry loop exhausted")

    @staticmethod
    def fallback_answer(question: str, style_matches: list[Any]) -> str:
        """No-LLM emergency answer: lead with a style cue word, then question keywords.

        Weak, but legal, non-empty, and faintly on-topic — strictly better than
        declining (0) or crashing the episode.
        """
        style_words = re.findall(r"[A-Za-z]{4,}", style_matches[0].style) if style_matches else []
        content = [w for w in re.findall(r"[A-Za-z0-9']+", question.lower())
                   if w not in _STOPWORDS and len(w) > 2]
        lead = style_words[0].capitalize() if style_words else "Honestly"
        body = " ".join(content[:6]) or "it depends on the moment"
        return repair_answer(f"{lead} speaking, {body} matters most to me")


# Back-compat alias: the harness historically imported BedrockWriter.
BedrockWriter = LLMWriter


_STOPWORDS = {
    "the", "and", "you", "your", "what", "when", "where", "how", "would", "could",
    "should", "with", "that", "this", "for", "are", "was", "were", "into", "about",
    "have", "has", "had", "can", "will", "than", "then", "them", "they", "their",
}
