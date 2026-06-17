"""PhaseEngine — pure, transport-free Cue-n-Woo policy state machine (v6, fingerprint-core).

Post-passphrase strategy (docs/designs/mentalist-v4-strategy-and-design.md, v6):
- private_questions: ask the 3 fingerprint probes (interview.PROBE_QUESTIONS), in order.
  Once all 3 replies are in, identify the steered style (Fingerprinter, question-keyed).
- proposals: author 3 style-discriminating challenge questions (author.pick_questions); the
  committed answers are TERSE, in-concept, written by the AnswerWriter centered on the
  fingerprint (avoiding the obvious answer -> duplicate-conflict hedge).
- answers (blind): answer the opponent's 3 questions in the fingerprinted style, terse.

Server contract (unchanged, verified vs v2/coworld/game.py): after every action the server
broadcasts a fresh state; `ask` is synchronous (judge reply appended to me.judge before the
next state); phases are global; idempotence from per-slot counts + one in-flight guard;
phase == "reveal"/`done` ends the game.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from . import author, config, interview
from .fingerprint import Fingerprint, Fingerprinter
from .validator import repair_answer


def _noop_emit(name: str, data: dict | None = None, *, step=None) -> None:
    pass


@dataclass
class PhaseEngine:
    emit: Callable[..., None] = _noop_emit
    fingerprinter: Fingerprinter | None = None
    writer: Any = None  # writer.AnswerWriter | None

    pending: str | None = field(default=None, init=False)
    _asks_target: int = field(default=0, init=False)
    _questions: list[str] = field(default_factory=list, init=False)  # our challenge questions
    _fingerprint: Fingerprint | None = field(default=None, init=False)
    done: bool = field(default=False, init=False)

    def decide(self, state: dict[str, Any]) -> dict[str, Any] | None:
        phase = state.get("phase")
        me = state.get("me") or {}
        if phase == "reveal" or state.get("done"):
            self.done = True
            self.emit("episode_end", {"results_present": state.get("results") is not None}, step="reveal")
            return None
        self._settle_pending(me)
        if self.pending is not None:
            return None
        if phase == "private_questions":
            return self._probe(me)
        if phase == "proposals" and not (me.get("proposals") or []):
            return self._propose(me)
        if phase == "answers" and not (me.get("answers") or []):
            return self._answer(state)
        return None

    # -- private_questions: ask the 3 fingerprint probes -----------------------
    def _probe(self, me: dict[str, Any]) -> dict[str, Any] | None:
        transcript = me.get("judge") or []
        n = len(transcript)
        if n >= len(interview.PROBE_QUESTIONS):
            self._ensure_fingerprint(transcript)
            return None
        qid, qtext = interview.PROBE_QUESTIONS[n]
        self._asks_target = n + 1
        self.emit("probe", {"index": n, "qid": qid}, step=f"interview:{n + 1}")
        return self._send("ask", {"question": qtext})

    def _ensure_fingerprint(self, transcript: list[dict[str, Any]]) -> None:
        if self._fingerprint is not None or self.fingerprinter is None:
            return
        # map each probe's qid -> the judge's answer (by ask order)
        answers = {}
        for i, turn in enumerate(transcript):
            if i < len(interview.QIDS):
                answers[interview.QIDS[i]] = turn.get("answer", "")
        self._fingerprint = self.fingerprinter.identify(answers)

    def _ranked(self):
        """Top-K fingerprint guesses (AxisGuess w/ likelihood) to hand the writer."""
        return self._fingerprint.ranked_guesses(5) if self._fingerprint else []

    def _format(self, word: str) -> str:
        """Wrap a single content word into the winning 'The {word}' form, legal + terse."""
        from .writer import first_word
        w = first_word(word) or "moment"
        return repair_answer(config.ANSWER_TEMPLATE.format(word=w),
                             fallback=config.GENERIC_FALLBACK_ANSWER)

    def _format_phrase(self, phrase: str) -> str:
        """Wrap a multi-word echo ('phlogiston phlogiston ...') as 'The {phrase}', kept legal
        (repair_answer caps at the 12-token limit). Used by the flood echo-to-tie path so the
        repeated word survives instead of being collapsed to one by first_word()."""
        cleaned = " ".join(w for w in (phrase or "").split() if w)
        return repair_answer(f"The {cleaned}" if cleaned else config.GENERIC_FALLBACK_ANSWER,
                             fallback=config.GENERIC_FALLBACK_ANSWER)

    def _confident_prepend_word(self) -> str | None:
        """If the top guess is very confident, use its concept word directly (skip the LLM)."""
        if not (config.CONFIDENT_PREPEND_ENABLED and self._fingerprint and self._fingerprint.guesses):
            return None
        top = self._fingerprint.guesses[0]
        if top.margin >= config.CONFIDENT_PREPEND_MIN_MARGIN:
            from .writer import first_word
            return first_word(top.value) or None
        return None

    def _concept_guess_text(self) -> str:
        """Our best-guess concept (top fingerprint values joined) to steer the test-time judge."""
        return "; ".join(self._fingerprint.guess_values(4)) if self._fingerprint else ""

    def _build_answers(self, questions: list[str], proposal: bool) -> list[str]:
        """Pick one word per question -> 'The {word}'.

        v9: when test-time scoring is on and we have a concept guess, generate K candidate
        words per question, delta-score them against the live judge (steered by our guess),
        and commit the max-delta word. Falls back to the LLM's first candidate / single-word
        path if scoring is off, the guess is empty, or the worker is unreachable.
        """
        if config.STRATEGY_MODE == "flood":
            # out-flood the incumbent: the dominant word repeated FLOOD_REPEATS times on every
            # answer (more reps than gabby's x4 wins the tiebreaker; repair caps at 12 tokens).
            phrase = " ".join([config.FLOOD_WORD] * max(1, config.FLOOD_REPEATS))
            return [self._format_phrase(phrase) for _ in questions]
        if (config.TESTTIME_SCORING_ENABLED and self.writer is not None
                and self._concept_guess_text()):
            return self._build_answers_scored(questions, proposal)
        # fallback path: single word per question (v8 behavior)
        forced = self._confident_prepend_word()
        if self.writer is not None:
            words = (self.writer.proposal_words(questions, self._ranked()) if proposal
                     else self.writer.blind_words(questions, self._ranked()))
        else:
            words = [self._fallback_word(q) for q in questions]
        out = []
        for i in range(len(questions)):
            # confident prepend overrides the LLM word on blind answers only
            w = forced if (forced and not proposal) else (
                words[i] if i < len(words) and words[i] else self._fallback_word(questions[i]))
            out.append(self._format(w))
        return out

    @staticmethod
    def _detect_flood_word(question: str) -> str | None:
        """A flooder repeats its word in the QUESTION ('goblin goblin goblin...'). Return the
        token repeated >= FLOOD_MIN_REPEATS times (case-insensitive), else None."""
        import re
        from collections import Counter
        toks = re.findall(r"[A-Za-z][A-Za-z'-]*", (question or "").lower())
        toks = [t for t in toks if t not in {"the", "a", "an", "and", "or", "of", "to"}]
        if not toks:
            return None
        word, n = Counter(toks).most_common(1)[0]
        return word if n >= config.FLOOD_MIN_REPEATS else None

    def _build_answers_scored(self, questions: list[str], proposal: bool) -> list[str]:
        from .judge_client import JudgeClient
        cand_lists = self.writer.candidate_words(
            questions, self._ranked(), config.TESTTIME_CANDIDATES_PER_Q, untrusted=not proposal)
        judge = JudgeClient(self._concept_guess_text(), timeout=config.JUDGE_TIMEOUT_SECONDS,
                            max_calls=config.JUDGE_MAX_CALLS)
        flood_aware = config.FLOOD_AWARE_RESPONDER and not proposal
        out = []
        for q, cands in zip(questions, cand_lists):
            if config.MULTI_BASELINE_SCORING:
                from .judge_client import NEUTRAL
                baselines = [NEUTRAL] + list(config.FLOOD_BASELINES)
                best, rows = judge.best_word_multi(q, cands, baselines)
                chosen = best or (cands[0] if cands else self._fallback_word(q))
                self.emit("word_scored_multi",
                          {"question": q[:60], "chosen": chosen, "scored_ok": best is not None,
                           "top": [(c, round(m, 3)) for c, m, _ in rows[:5]]},
                          step="propose" if proposal else "answer")
                out.append(self._format(chosen))
                continue
            flood = self._detect_flood_word(q) if flood_aware else None
            if flood:
                # score our candidates HEAD-TO-HEAD vs the opponent's flood word
                best, scored = judge.best_word(q, cands, baseline=flood)
                top_delta = scored[0][1] if scored else 0.0
                if best is not None and top_delta >= config.FLOOD_ECHO_DELTA:
                    chosen = best
                    mode = "beat"
                else:
                    # nothing beats it (phlogiston case) -> echo to force a duplicate-conflict tie
                    chosen = " ".join([flood] * config.FLOOD_ECHO_REPEATS)
                    mode = "echo_tie"
                self.emit("flood_response", {"question": q[:60], "flood_word": flood, "mode": mode,
                                             "chosen": chosen, "top_delta": round(top_delta, 3),
                                             "candidates": scored[:5] if scored else cands[:5]},
                          step="answer")
                out.append(self._format(chosen) if mode == "beat" else self._format_phrase(chosen))
                continue
            best, scored = judge.best_word(q, cands)
            chosen = best or (cands[0] if cands else self._fallback_word(q))
            self.emit("word_scored", {"question": q[:60], "chosen": chosen, "scored_ok": best is not None,
                                      "candidates": scored[:5] if scored else cands[:5]},
                      step="propose" if proposal else "answer")
            out.append(self._format(chosen))
        return out

    def _fallback_word(self, question: str) -> str:
        from .writer import AnswerWriter
        return AnswerWriter._fallback(question, self._ranked())

    # -- proposals: style-discriminating questions + one-word in-concept answers --
    def _propose(self, me: dict[str, Any]) -> dict[str, Any]:
        self._ensure_fingerprint(me.get("judge") or [])
        self._questions = author.pick_questions(config.CHALLENGE_QUESTIONS_PER_PLAYER)
        answers = self._build_answers(self._questions, proposal=True)
        proposals = [{"question": q, "answer": a} for q, a in zip(self._questions, answers)]
        self.emit("authored", {"proposals": proposals,
                               "guesses": [(g.value, round(g.likelihood, 2)) for g in self._ranked()]},
                  step="propose")
        return self._send("propose", {"proposals": proposals})

    # -- answers: blind, one word in the fingerprinted style -------------------
    def _answer(self, state: dict[str, Any]) -> dict[str, Any] | None:
        questions = [q.get("question", "") for q in state.get("opponent_questions") or []]
        if not questions:
            return None
        self._ensure_fingerprint((state.get("me") or {}).get("judge") or [])
        answers = self._build_answers(questions, proposal=False)
        self.emit("responded", {"questions": questions, "answers": answers,
                                "forced": self._confident_prepend_word()}, step="answer")
        return self._send("answer", {"answers": answers})

    # -- idempotence / framing -------------------------------------------------
    def _settle_pending(self, me: dict[str, Any]) -> None:
        if self.pending == "ask" and len(me.get("judge") or []) >= self._asks_target:
            self.pending = None
        elif self.pending == "propose" and (me.get("proposals") or []):
            self.pending = None
        elif self.pending == "answer" and (me.get("answers") or []):
            self.pending = None

    def _send(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.pending = kind
        return {"type": kind, **payload}

    def on_error(self, error: str) -> None:
        self.emit("server_rejected", {"error": error[:200], "pending": self.pending})
        self.pending = None
