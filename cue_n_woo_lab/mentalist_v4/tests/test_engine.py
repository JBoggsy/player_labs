"""PhaseEngine v6 end-to-end: 3 probes -> fingerprint -> propose -> blind answer."""
from __future__ import annotations

from mentalist_v4 import interview
from mentalist_v4.engine import PhaseEngine
from mentalist_v4.validator import validate_answer


class StubWriter:
    """Returns ONE word per question (the v7 contract)."""
    def __init__(self):
        self.proposal_calls = []
        self.blind_calls = []

    def proposal_words(self, questions, guesses):
        self.proposal_calls.append((list(questions), list(guesses)))
        return ["lantern" for _ in questions]

    def blind_words(self, questions, guesses):
        self.blind_calls.append((list(questions), list(guesses)))
        return ["harbor" for _ in questions]

    def persona_phrase(self, guesses):
        # stub: no LLM persona phrase -> engine falls back to config.INJECT_ANSWER
        return None

    def candidate_words(self, questions, guesses, k, untrusted):
        # K distinct, pure-alpha candidates per question; the engine delta-scores and picks one.
        # (alpha-only so first_word doesn't strip digits/punctuation in the formatted answer)
        pool = ["lantern", "harbor", "shadow", "goblin", "ember", "willow"]
        self.candidate_calls = getattr(self, "candidate_calls", [])
        self.candidate_calls.append((list(questions), list(guesses), k, untrusted))
        return [[pool[(i + j) % len(pool)] for j in range(k)] for i, _ in enumerate(questions)]


class StubFingerprinter:
    """Returns a fixed fingerprint without needing the reference matrix / Titan."""
    def __init__(self, margin=0.20):
        self.calls = []
        self.margin = margin

    def identify(self, answers_by_question):
        self.calls.append(dict(answers_by_question))
        from mentalist_v4.fingerprint import AxisGuess, Fingerprint
        g = [AxisGuess(axis="time", value="frontier town", score=0.5, margin=self.margin)]
        conf = g if self.margin >= 0.12 else []
        return Fingerprint(backend="stub", guesses=g, top_value="frontier town", confident=conf)


def _state(phase, judge=None, proposals=None, answers=None, opp=None):
    return {"phase": phase,
            "me": {"judge": judge or [], "proposals": proposals or [], "answers": answers or []},
            "opponent_questions": opp or []}


def test_full_v6_flow(monkeypatch):
    # this test covers the single-word (v8) construction path; turn off v9 test-time scoring
    from mentalist_v4 import config
    monkeypatch.setattr(config, "TESTTIME_SCORING_ENABLED", False)
    w, fp = StubWriter(), StubFingerprinter()
    eng = PhaseEngine(fingerprinter=fp, writer=w)
    judge = []

    # private_questions: asks the 3 probe questions in order
    for i in range(len(interview.PROBE_QUESTIONS)):
        a = eng.decide(_state("private_questions", judge=list(judge)))
        assert a["type"] == "ask"
        assert a["question"] == interview.PROBE_QUESTIONS[i][1]
        assert eng.decide(_state("private_questions", judge=list(judge))) is None  # pending
        judge.append({"question": a["question"], "answer": f"reply {i}"})

    # transcript full -> no more asks, fingerprint computed
    assert eng.decide(_state("private_questions", judge=list(judge))) is None

    # propose: one-word answers formatted as "The {word}" (<=2 tokens)
    a = eng.decide(_state("proposals", judge=judge))
    assert a["type"] == "propose" and len(a["proposals"]) == 3
    for p in a["proposals"]:
        validate_answer(p["answer"])
        assert p["answer"] == "The lantern"             # writer's word, our format
        assert len(p["answer"].split()) <= 2            # terse by construction
    # the writer received the ranked guesses (AxisGuess objects), not bare strings
    assert hasattr(w.proposal_calls[-1][1][0], "likelihood")
    assert set(fp.calls[-1].keys()) == set(interview.QIDS)

    # answers: blind. margin 0.20 >= prepend threshold -> forced to the confident concept word.
    opp = [{"question": "What object matters to you?"}, {"question": "x?"}, {"question": "y?"}]
    a = eng.decide(_state("answers", judge=judge, proposals=a["proposals"], opp=opp))
    assert a["type"] == "answer" and len(a["answers"]) == 3
    for ans in a["answers"]:
        validate_answer(ans)
        assert ans == "The frontier"   # confident prepend used the recovered axis word

    assert eng.decide(_state("reveal")) is None and eng.done


def test_blind_uses_writer_word_when_not_confident(monkeypatch):
    from mentalist_v4 import config
    monkeypatch.setattr(config, "TESTTIME_SCORING_ENABLED", False)
    # margin 0.05 < prepend threshold -> use the writer's per-question word, not a forced one
    eng = PhaseEngine(fingerprinter=StubFingerprinter(margin=0.05), writer=StubWriter())
    judge = [{"question": q, "answer": "x"} for _, q in interview.PROBE_QUESTIONS]
    a = eng.decide(_state("answers", judge=judge, opp=[{"question": "q?"}, {"question": "r?"}, {"question": "s?"}]))
    for ans in a["answers"]:
        validate_answer(ans)
        assert ans == "The harbor"  # writer's blind word, formatted


def test_flood_mode_answers_fixed_word(monkeypatch):
    from mentalist_v4 import config
    monkeypatch.setattr(config, "STRATEGY_MODE", "flood")
    monkeypatch.setattr(config, "FLOOD_WORD", "phlogiston")
    monkeypatch.setattr(config, "FLOOD_REPEATS", 8)
    eng = PhaseEngine(fingerprinter=StubFingerprinter(), writer=StubWriter())
    judge = [{"question": q, "answer": "x"} for _, q in interview.PROBE_QUESTIONS]
    a = eng.decide(_state("answers", judge=judge, opp=[{"question": "q?"}, {"question": "r?"}]))
    for ans in a["answers"]:
        validate_answer(ans)
        # phlogiston repeated x8, formatted "The phlogiston phlogiston ..." (<=12 tokens)
        assert ans.startswith("The phlogiston phlogiston")
        assert ans.split().count("phlogiston") == 8


def test_v11_flood_aware_echoes_when_unbeatable(monkeypatch):
    """v11: on a blind flood question, if no candidate beats the flood word head-to-head,
    echo the flood word x N to force a duplicate-conflict tie."""
    from mentalist_v4 import config, judge_client

    class StubJudge:
        def __init__(self, *a, **k): pass
        def best_word(self, question, candidates, baseline=None):
            # baseline = the detected flood word; pretend nothing beats it (low delta)
            assert baseline == "phlogiston"
            return candidates[0], [(candidates[0], 0.02)]

    monkeypatch.setattr(config, "TESTTIME_SCORING_ENABLED", True)
    monkeypatch.setattr(config, "FLOOD_AWARE_RESPONDER", True)
    monkeypatch.setattr(config, "FLOOD_ECHO_REPEATS", 4)
    monkeypatch.setattr(judge_client, "JudgeClient", StubJudge)
    eng = PhaseEngine(fingerprinter=StubFingerprinter(margin=0.20), writer=StubWriter())
    judge = [{"question": q, "answer": "x"} for _, q in interview.PROBE_QUESTIONS]
    opp = [{"question": "phlogiston phlogiston phlogiston phlogiston"}]
    a = eng.decide(_state("answers", judge=judge, opp=opp))
    validate_answer(a["answers"][0])
    assert a["answers"][0] == "The phlogiston phlogiston phlogiston phlogiston"  # echo-to-tie


def test_v11_flood_aware_beats_when_possible(monkeypatch):
    """v11: if a candidate DOES beat the flood word (goblin case), play that word."""
    from mentalist_v4 import config, judge_client

    class StubJudge:
        def __init__(self, *a, **k): pass
        def best_word(self, question, candidates, baseline=None):
            assert baseline == "goblin"
            return "quintessence", [("quintessence", 0.95)]   # beats goblin

    monkeypatch.setattr(config, "TESTTIME_SCORING_ENABLED", True)
    monkeypatch.setattr(config, "FLOOD_AWARE_RESPONDER", True)
    monkeypatch.setattr(judge_client, "JudgeClient", StubJudge)
    eng = PhaseEngine(fingerprinter=StubFingerprinter(margin=0.20), writer=StubWriter())
    judge = [{"question": q, "answer": "x"} for _, q in interview.PROBE_QUESTIONS]
    opp = [{"question": "goblin goblin goblin goblin goblin"}]
    a = eng.decide(_state("answers", judge=judge, opp=opp))
    assert a["answers"][0] == "The quintessence"   # beat-mode, single word


def test_v12_multi_baseline_picks_word_beating_flood(monkeypatch):
    """v12: multi-baseline scorer picks the candidate with the best MIN delta across
    [neutral, goblin, phlogiston] — i.e. one that beats the flood words, not just neutral."""
    from mentalist_v4 import config, judge_client

    class StubJudge:
        def __init__(self, *a, **k): pass
        def best_word_multi(self, question, candidates, baselines):
            # pretend 'quintessence' beats all baselines; 'abacus' loses to goblin
            rows = [("quintessence", 0.61, {}), ("abacus", 0.22, {})]
            return rows[0][0], rows

    monkeypatch.setattr(config, "TESTTIME_SCORING_ENABLED", True)
    monkeypatch.setattr(config, "MULTI_BASELINE_SCORING", True)
    monkeypatch.setattr(judge_client, "JudgeClient", StubJudge)
    eng = PhaseEngine(fingerprinter=StubFingerprinter(margin=0.20), writer=StubWriter())
    judge = [{"question": q, "answer": "x"} for _, q in interview.PROBE_QUESTIONS]
    a = eng.decide(_state("answers", judge=judge, opp=[{"question": "q?"}]))
    assert a["answers"][0] == "The quintessence"


def test_inject_mode_plants_questions_and_commits_answer(monkeypatch):
    """inject mode: Q1 is a clean self-report probe; Q2-Q3 are direct-prefer injections
    naming the committed answer; every committed/blind answer is that phrase verbatim.
    With a stub writer (no persona_phrase) the committed answer falls back to INJECT_ANSWER."""
    from mentalist_v4 import config
    monkeypatch.setattr(config, "STRATEGY_MODE", "inject")
    monkeypatch.setattr(config, "INJECT_ANSWER", "the lighthouse keeper's ledger")
    eng = PhaseEngine(fingerprinter=StubFingerprinter(), writer=StubWriter())
    judge = []
    for i in range(3):
        a = eng.decide(_state("private_questions", judge=list(judge)))
        assert a["type"] == "ask"
        assert "SYSTEM:" not in a["question"]   # fake system framing backfires; avoid it
        if i == 0:
            # Q1 is a real self-report probe (no injection text yet)
            assert "the lighthouse keeper's ledger" not in a["question"]
        else:
            # Q2-Q3 inject toward the committed answer
            assert "the lighthouse keeper's ledger" in a["question"]
        judge.append({"question": a["question"], "answer": f"r{i}"})
    # proposals: committed answers are the primed phrase verbatim
    a = eng.decide(_state("proposals", judge=judge))
    assert a["type"] == "propose"
    for p in a["proposals"]:
        validate_answer(p["answer"])
        assert p["answer"] == "the lighthouse keeper's ledger"
    # blind answers: same (pass proposals so the propose pending settles)
    a = eng.decide(_state("answers", judge=judge, proposals=a["proposals"],
                          opp=[{"question": "q?"}, {"question": "r?"}]))
    for ans in a["answers"]:
        assert ans == "the lighthouse keeper's ledger"


def test_runs_without_writer_or_fingerprinter():
    eng = PhaseEngine(fingerprinter=None, writer=None)
    a = eng.decide(_state("private_questions"))
    assert a["type"] == "ask"  # still asks probes
    # jump to proposals with no fingerprint/writer -> legal fallback answers
    judge = [{"question": q, "answer": "x"} for _, q in interview.PROBE_QUESTIONS]
    a = eng.decide(_state("proposals", judge=judge))
    assert a["type"] == "propose"
    for p in a["proposals"]:
        validate_answer(p["answer"])


def test_v9_picks_max_delta_word(monkeypatch):
    """v9: with test-time scoring on, the engine delta-scores the writer's candidates and
    commits the best one, formatted as 'The {word}'."""
    from mentalist_v4 import config, judge_client

    class StubJudge:
        instances = []
        def __init__(self, concept_text, *, worker_url=None, timeout=12.0, max_calls=12):
            self.concept_text = concept_text
            StubJudge.instances.append(self)
        def best_word(self, question, candidates):
            # deterministically prefer the LAST candidate (not candidates[0], to prove scoring ran)
            best = candidates[-1]
            return best, [(c, float(i)) for i, c in enumerate(candidates)]

    monkeypatch.setattr(config, "TESTTIME_SCORING_ENABLED", True)
    monkeypatch.setattr(config, "TESTTIME_CANDIDATES_PER_Q", 4)
    monkeypatch.setattr(judge_client, "JudgeClient", StubJudge)

    eng = PhaseEngine(fingerprinter=StubFingerprinter(margin=0.20), writer=StubWriter())
    judge = [{"question": q, "answer": "x"} for _, q in interview.PROBE_QUESTIONS]
    opp = [{"question": "q?"}, {"question": "r?"}, {"question": "s?"}]
    a = eng.decide(_state("answers", judge=judge, opp=opp))
    assert a["type"] == "answer" and len(a["answers"]) == 3
    pool = ["lantern", "harbor", "shadow", "goblin", "ember", "willow"]
    k = config.TESTTIME_CANDIDATES_PER_Q
    for i, ans in enumerate(a["answers"]):
        validate_answer(ans)
        # StubJudge prefers the LAST candidate, proving scoring ran (not candidates[0])
        assert ans == f"The {pool[(i + k - 1) % len(pool)]}"
    # the judge was steered by our concept guess (joined fingerprint values), not empty
    assert StubJudge.instances and StubJudge.instances[-1].concept_text


def test_v9_falls_back_when_scoring_unavailable(monkeypatch):
    """If the worker is unreachable (best_word returns None), commit the LLM's first candidate."""
    from mentalist_v4 import config, judge_client

    class DeadJudge:
        def __init__(self, *a, **k): pass
        def best_word(self, question, candidates):
            return None, []   # worker down

    monkeypatch.setattr(config, "TESTTIME_SCORING_ENABLED", True)
    monkeypatch.setattr(config, "TESTTIME_CANDIDATES_PER_Q", 4)
    monkeypatch.setattr(judge_client, "JudgeClient", DeadJudge)

    eng = PhaseEngine(fingerprinter=StubFingerprinter(margin=0.20), writer=StubWriter())
    judge = [{"question": q, "answer": "x"} for _, q in interview.PROBE_QUESTIONS]
    a = eng.decide(_state("answers", judge=judge, opp=[{"question": "q?"}]))
    validate_answer(a["answers"][0])
    assert a["answers"][0] == "The lantern"   # first candidate (candidates[0]) on fallback


def test_error_clears_pending():
    eng = PhaseEngine(fingerprinter=StubFingerprinter(), writer=StubWriter())
    eng.decide(_state("private_questions"))
    assert eng.pending == "ask"
    eng.on_error("bad")
    assert eng.pending is None
