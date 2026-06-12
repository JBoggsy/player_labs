"""BedrockWriter — Claude writes short, on-topic answers in the classified style.

The probes showed the winning answer needs BOTH ingredients: genuine topical
quality (the LLM's job) and the judge's style as an early-diverging tilt (the
classifier label + the real judge transcript as few-shot evidence). Pure style
markers lose 0%; generic-plain is a coin flip (probe finding 3).

Every public method degrades gracefully: if Bedrock is unreachable the caller
gets deterministic fallback answers, never an exception — a weak submitted
answer strictly beats a crash or a decline (decline scores 0; a real answer
facing a decline takes 110 uncontested).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from . import config
from .validator import repair_answer

_RETRYABLE = {"ServiceUnavailableException", "ThrottlingException", "TooManyRequestsException", "ModelTimeoutException"}

_ANSWERS_TOOL = {
    "toolSpec": {
        "name": "submit_answers",
        "description": "Submit the final answers, one per question, in order.",
        "inputSchema": {
            "json": {
                "type": "object",
                "additionalProperties": False,
                "required": ["answers"],
                "properties": {
                    "answers": {"type": "array", "items": {"type": "string"}},
                },
            }
        },
    }
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


class BedrockWriter:
    def __init__(self) -> None:
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or config.BEDROCK_REGION
        model = os.environ.get("BEDROCK_CLAUDE_MODEL_ID", config.BEDROCK_MODEL_ID)
        self.model_id = model
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=BotoConfig(connect_timeout=10, read_timeout=90, retries={"max_attempts": 0}),
        )

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
        try:
            raw = self._converse(prompt)
        except Exception as exc:  # any Bedrock failure -> deterministic fallback
            _log(f"Bedrock failed ({exc!r}); using fallback answers")
            return fallbacks
        answers = [str(a) for a in raw][:n]
        while len(answers) < n:
            answers.append(fallbacks[len(answers)])
        return [repair_answer(a, fallback=fallbacks[i]) for i, a in enumerate(answers)]

    def _converse(self, prompt: str) -> list[Any]:
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        last_exc: Exception | None = None
        for attempt in range(config.BEDROCK_ATTEMPTS):
            try:
                t0 = time.time()
                response = self.client.converse(
                    modelId=self.model_id,
                    messages=messages,
                    toolConfig={
                        "tools": [_ANSWERS_TOOL],
                        "toolChoice": {"tool": {"name": "submit_answers"}},
                    },
                    inferenceConfig={"maxTokens": config.BEDROCK_MAX_TOKENS},
                )
                _log(f"converse ok in {time.time() - t0:.1f}s (attempt {attempt + 1})")
                for block in response["output"]["message"]["content"]:
                    tool_use = block.get("toolUse")
                    if tool_use and tool_use["name"] == "submit_answers":
                        return tool_use["input"]["answers"]
                raise RuntimeError("Claude did not call submit_answers")
            except ClientError as exc:
                last_exc = exc
                code = exc.response.get("Error", {}).get("Code", "")
                if code not in _RETRYABLE or attempt == config.BEDROCK_ATTEMPTS - 1:
                    raise
                time.sleep(2 ** attempt)
            except BotoCoreError as exc:  # timeouts, connection errors
                last_exc = exc
                if attempt == config.BEDROCK_ATTEMPTS - 1:
                    raise
                time.sleep(2 ** attempt)
        raise last_exc or RuntimeError("Bedrock retry loop exhausted")

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


_STOPWORDS = {
    "the", "and", "you", "your", "what", "when", "where", "how", "would", "could",
    "should", "with", "that", "this", "for", "are", "was", "were", "into", "about",
    "have", "has", "had", "can", "will", "than", "then", "them", "they", "their",
}
