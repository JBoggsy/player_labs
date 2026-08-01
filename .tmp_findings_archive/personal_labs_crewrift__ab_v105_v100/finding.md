## Finding — v105 social rework: crew win-rate suggestive-up, but a new no-vote regression

**Gate passed** (the whole point vs the throttled historical data): v105 seat-0
meeting-LLM fired at **71.6%**, v100 at **81.9%** — both arms genuinely exercised the
meeting-LLM path. Pacing at 400 concurrent held; no throttling collapse.

**Target (win-rate), natural roles, ops-filtered:**
- crew **15% → 22%** (p=0.11) — moved the intended direction but NOT significant.
  Underpowered: 200/arm → ~160 crew, ~40 imposter per arm after split+ops-filter.
- imposter **57% → 59%** (p=0.86) — flat.

**Regression (significant):** `no_vote_rate` **0% → 9% crew (p=0.00)**, **0% → 14%
imposter (p=0.02)**. v105 sometimes attends a meeting and casts no vote; v100 never did.
Not explained by `meeting_vote_gated`/`budget_exhausted` (both present in v100 too). The
one genuinely-new v105 event is `domain.meeting_spend` (20,848 in v105, absent in v100) —
the `spend.py` follow-up-budget gate. Suspected mechanism: a spend/budget path exits the
meeting without submitting the tentative vote. Needs a focused diagnose/experiment.

**Verdict:** inconclusive on the persuasion bet (crew signal encouraging but under-powered),
and v105 introduces a real vote-submission regression that should be root-caused before any
submit. Do NOT ship v105 as-is. Next: (a) diagnose the no-vote path in spend.py; (b) if the
crew signal holds, re-run at ~300/arm for power once the regression is fixed.
