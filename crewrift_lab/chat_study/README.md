# chat_study — what meeting chat draws suspicion vs. persuades

A light-ML study of Crewrift meeting chat: turn every natural-language chat message into a
feature vector and fit a **readable** model of two outcomes, measured from **real vote
movement** — so we change crewborg's social behaviour on evidence, not intuition.

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
