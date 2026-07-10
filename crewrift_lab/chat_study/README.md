# chat_study — what meeting chat draws suspicion vs. persuades

A light-ML study of Crewrift meeting chat: turn every natural-language chat message into a
feature vector and fit a **readable** model of two outcomes, measured from **real vote
movement** — so we change crewborg's social behaviour on evidence, not intuition.

Built 2026-07-07. Corpus: the 3 event warehouses that carry resolved vote targets
(`v96_rank_wh` + `crew_wh` + `v101_wh`), **851 episodes / 2,450 meetings / 6,757 NL chats**
(4,803 crew + 1,954 imposter) / 13,441 votes.

## Two questions (both labelled from votes, not opinion)

- **A. Suspicion drawn** — after a message, do votes shift onto **the speaker**?
- **B. Persuasion** — after a message, do votes shift onto the player the speaker **accused**?

## Pipeline (each stage idempotent; re-run any time)

```sh
# 1. merge warehouses -> per-chat rows w/ symbolic features + vote timelines
uv run python crewrift_lab/chat_study/build_dataset.py       # -> dataset/{chats,votes}.parquet
#    add more data later: --warehouses /path/a_wh /path/b_wh  and/or  --glob-dir /tmp
#    (auto-discovers every *_wh under the dir; warehouses without vote targets are skipped)

# 2. LLM-label each DISTINCT chat text (Bedrock Haiku, cached) with semantic flags
#    (accuse / evidence / defend-self / question / vouch / bandwagon + accused color)
uv run python crewrift_lab/chat_study/label_chats.py         # -> dataset/{llm_cache.json,chats_labeled.parquet}
#    needs AWS creds + boto3; ~3.2k distinct texts, ~14 min; --refresh to re-label

# 3. compute the persuasion label + fit both models, split by speaker role
uv run python crewrift_lab/chat_study/fit.py                 # -> models/{report.md,coeffs.json}
```

## Features

- **Symbolic** (`f_*`, computed in stage 1): first_speaker, word_count, is_question,
  names_color, self_reference, says_vote, says_sus.
- **Semantic** (`s_*`, LLM in stage 2): accuses, provides_evidence, defends_self,
  asks_question, vouches, bandwagons.
- **Timing controls** (`f_latency_ticks`, `f_speak_order`, `f_votes_remaining`): kept in the
  model but reported separately. They matter because a late message has few votes left to
  move — a mechanical effect that would otherwise swamp the content signal. Content
  coefficients read "holding when-in-the-meeting fixed."

The model is standardized L2 logistic regression (coefficients per 1 SD, comparable
across features); `cv_auc` is a meeting-grouped sanity check that the signal is real
(0.61–0.92), **not** the goal — the coefficients are.

## Headline findings (see `models/report.md` for the full tables)

Read the **actionable (non-control)** coefficients. Sign = effect on the outcome.

**What PERSUADES (moves votes onto your accused target):**
- **Citing concrete evidence works — especially for imposters.** `s_provides_evidence` is
  the standout actionable lever on the imposter persuasion model (+0.34 coef; raw: imposter
  accusations *with* evidence land 64% of the time vs **43% without** — a 21pp swing). A
  fabricated-but-concrete cue ("X vented near the body") persuades; a bare "X is sus" does not.
- **Explicit vote language helps** (`f_says_vote` +0.71 crew, `f_says_sus` +0.50/+0.70): say
  "vote X" / "X is sus", not just imply it.
- **Bandwagoning persuades for imposters** (`s_bandwagons` +0.75): piling onto an existing
  accusation moves votes; opening a *fresh* accusation ("first_speaker") does less.
- **Asking questions does NOT persuade** (`s_asks_question` −0.36/−0.40) — it defers, it
  doesn't drive a vote.

**What DRAWS SUSPICION onto yourself (avoid as imposter):**
- **Self-referential defensiveness** (`f_self_reference` +0.15 imposter, +0.23 imposter
  suspicion model): "it wasn't me / I was doing tasks" reads as guilty. Defending yourself
  unprompted backfires.
- Timing controls dominate raw suspicion; among content, defensiveness + question-dodging
  are the tells.

## Implication for crewborg (the point of the study)

crewborg-imposter chats **1.88 lines/seat vs notsus 3.56** (half as much), and its
deterministic meeting path leans on **bandwagon + fabricated cues** already. The study says
the right upgrades are: (1) **always attach a concrete (safe) evidence cue** to an
accusation/bandwagon — it's the biggest persuasion lever and crewborg's `fabricate_accusation`
already produces these, so the change is to fire it more and never bare-accuse; (2) **use
explicit "vote X" / "X sus" phrasing**; (3) **do NOT self-defend unprompted** (raises
suspicion); (4) **prefer bandwagoning a live pile to opening a fresh accusation.** These map
directly onto `strategy/meeting/imposter.py` + `memory/imposter.md`.

Caveat: `s_accuses` shows a spurious negative coefficient — it's ~collinear with "there is an
accused target at all" (77% of chats), so L2 can't identify it; the signal is in the
*differentiating* features above, confirmed by raw rates.
