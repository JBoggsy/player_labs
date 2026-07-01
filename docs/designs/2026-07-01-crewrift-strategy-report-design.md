# Crewrift strategy report — design

**Status:** proposed (not yet implemented)
**Date:** 2026-07-01
**Scope:** a new game-specific skill + tools that turn the Crewrift event warehouse into a
complete, detailed, cross-episode report on **how a given policy plays each of the two roles**.

---

## Problem

The `crewrift-event-warehouse` skill is a *data-collation* step: it replays episodes into a
policy-indexed DuckDB/Parquet dataset of per-tick gameplay events, and ships a query dashboard +
recipe library. But answering a whole-strategy question today — *"how does this policy play
imposter? how does it play crew?"* — means hand-writing a dozen SQL queries and stitching the
answers together by hand, every time, for every policy. There is no tool that runs the full
battery and produces a finished strategic profile.

We want a tool that looks at **one policy's rows in the warehouse**, measures how it behaves across
**many episodes** (never a single game), and generates a **complete, detailed report** on its
strategy in both roles — the kind of profile you'd write to scout an opponent or to diagnose our
own player.

### The questions the report must answer

**As imposter:**
- How do they choose a target to follow?
- How closely do they follow?
- If/when they lose track of a target, how do they reacquire it?
- If/when they lose track and can't reacquire, what's their next move?
- If they don't have a target, how do they search?
- How far do they tail opponents?
- How, if at all, do they pretend to be a crewmate?
- How do they chat — how do they deflect/blame?

**As crewmate:**
- How do they select the next task? What order do they complete tasks in?
- How do they navigate around other agents (cluster, flee, personal space)?
- When and why do they call an emergency meeting?
- How do they chat and vote? What do they consider suspicious?

Plus any other strategically relevant signal the data supports (survival/death mode, score
composition, consistency across games).

---

## Goals / non-goals

**Goals**
- Profile **any** policy in a warehouse from **replay-derived events alone** (works for opponents
  — Aaron/Andre/notsus — as well as crewborg; no dependence on crewborg's own trace logs).
- Characterize every behaviour **both in absolute terms and relative to the rest of the field**
  in the same warehouse (e.g. "tails at 22px median vs field 60px — 3× closer than the norm").
- Answer the questions **across episodes**, with a per-episode spread so the report can say
  "does this every game" vs "high-variance."
- Combine a deterministic metric battery with **agent interpretation of the actual flagged chat
  lines** — the structured extractors flag/aggregate; the agent reads the real text to explain.
- Produce a finished, self-contained **Ink & Print HTML** report.

**Non-goals**
- Not a batch overview (that's `crewrift-survey`) and not a candidate-vs-baseline A/B (that's
  `crewrift-ab`). This is a *descriptive deep profile of one policy's strategy*.
- Not a warehouse builder — it consumes an already-built warehouse (`crewrift-event-warehouse`
  builds it). It does not re-step replays.
- No new *objective* event extraction in the replay expander — the battery is built from the
  events the warehouse already emits. The only new extraction is one **chat** interpreter.

---

## Architecture

A new game-specific skill **`crewrift-strategy`** under
`crewrift_lab/.claude/skills/crewrift-strategy/`, layered directly on top of
`crewrift-event-warehouse`. It follows the established lab pattern (mirrors `crewrift-survey`):
a **script flags/aggregates, the agent interprets, a render step produces the HTML**.

Three stages:

```
  built warehouse  ──▶  strategy_probes.py  ──▶  profile.json
  (crewrift-event-      (fixed SQL battery,       (metrics: subject vs field,
   warehouse)            evidence sampling)         n, per-episode spread;
                                                    + evidence bundles)
                                     │
                                     ▼
                          agent reads profile.json
                          + opens flagged evidence   ──▶  narrative.md
                          (real chat lines, replay         (per-role, per-question
                           links for standout eps)          prose answers)
                                     │
                                     ▼
                          strategy_report.py         ──▶  strategy_report.html
                          (folds narrative + numbers        (self-contained,
                           + small charts)                   Ink & Print house style)
```

### Component 1 — `strategy_probes.py` (deterministic battery)

- **Location:** `crewrift_lab/.claude/skills/crewrift-strategy/scripts/strategy_probes.py`
- **Input:** `--warehouse <dir> --policy <name>` (policy matched by prefix, e.g. `crewborg`
  matches `crewborg:v75`; a `--version` filter optional). `--out profile.json`.
- **What it does:** opens the warehouse's `events` + `episode_players` parquet as DuckDB views
  (the recipe boilerplate), runs the **probe battery** (below), and for every probe records both
  the **subject** value and the **field** value (all other policies aggregated) with the sample
  size `n` and a per-episode spread (e.g. IQR or stdev across episodes). Where a probe is
  interpretive, it also samples a bounded set of **evidence rows** (the concrete chat lines, kill
  sequences, task orders, replay links) into the JSON for the agent to read.
- **Output:** one `profile.json`:
  ```jsonc
  {
    "meta": { "warehouse": "...", "policy": "crewborg", "episodes": 100,
              "roles": {"imposter": 60, "crew": 118}, "skewed_episodes": 0,
              "field_policies": ["crewborg-aaln", "truecrew"] },
    "imposter": {
      "follow_closeness": { "subject": {"median_px": 22, "alignment": 0.71, "chase_rate": 0.18},
                            "field": {"median_px": 60, ...}, "n": 240, "spread": {...} },
      "target_selection": { ... },
      "reacquire": { ... },
      /* ... one block per probe ... */
      "chat_deflect": { "subject": {...}, "field": {...},
                        "evidence": [{"episode_id": "...", "ts": 1234,
                                      "text": "red was following me the whole time",
                                      "stance": "deflect", "replay_url": "..."}] }
    },
    "crew": { /* task_order, navigation, meetings, votes, chat_suss, ... */ },
    "cross_role": { "survival": {...}, "score_composition": {...} }
  }
  ```
- **Design note:** the probe SQL is centralized (a `PROBES` list of named `(role, sql, shaper)`),
  so a new question is a new list entry, not new plumbing — the same philosophy as the dashboard's
  `PRESETS`. Every player-aggregate probe guards `WHERE slot >= 0`; embedded slots (victim, follow
  target) self-join `episode_players` per the catalog cheat-sheet.

### Component 2 — the agent (interpretation)

Driven by `SKILL.md`. The agent:
1. Reads `profile.json` — the numbers and the field contrast.
2. **Opens the flagged evidence** — reads the actual `chat` lines the extractors flagged
   (deflect/blame/suspicion), and may open replay links for standout episodes — to interpret the
   *how*, not just the *how much*. This is the part a query cannot give.
3. Writes `narrative.md`: a real, specific, per-role answer to each checklist question, citing the
   numbers and the field contrast, distinguishing consistent behaviour from high-variance.

The `SKILL.md` carries the **per-role question checklist** (agent makes a todo per question) so no
question is silently dropped, plus the discipline notes (decompose by role, mind small n,
field-contrast, ops-vs-behaviour).

### Component 3 — `strategy_report.py` (render)

- **Location:** `crewrift_lab/.claude/skills/crewrift-strategy/scripts/strategy_report.py`
- **Input:** `profile.json` + `narrative.md` (+ `--title`). **Output:** `strategy_report.html`.
- **What it does:** folds the agent's prose together with the metric tables, **field-contrast bars**
  (subject vs field, the mini-bar from the design mockups), and small charts, into a self-contained
  HTML report in the **Ink & Print** house style. Reuses the survey's `STYLE` block and the shared
  building blocks (masthead, data table, `.detail` callouts, heat/bar cells) per
  `crewrift_lab/docs/report-style.md`. Structured **finding-first, per role, per question**.
- **Verify by looking:** per report-style.md, the HTML is screenshotted at 375/768/1280 and read
  before the report is presented (`ux.ify` or the `shoot.mjs` path).

### Component 4 — `chat_stance` extractor (one new build, in the warehouse package)

The deflect/blame, pretend-to-be-crew, and "what do they consider suspicious" questions require
chat interpretation beyond the existing `suss` (who a message accuses). We add **one** new LLM chat
extractor following the documented `suss.py` template.

- **Location:** `crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/crewrift_event_warehouse/chat_stance.py`
  (next to `suss.py` — it is reusable warehouse infrastructure, not strategy-specific), wired as a
  `crewrift-event-warehouse chat-stance` subcommand.
- **What it does:** the four `suss.py` steps — distinct texts → classify once via Bedrock Haiku
  (temperature 0, JSON-array out) → cache to `chat_stance_cache.json` → write a native
  `events/key=chat_stance` partition keyed by speaker. Each message gets a small **stance enum**:
  `accuse / defend_self / defend_other / vouch / claim_task / deflect / info / noise`.
- **Consumed by:** the probes aggregate it (deflect rate, self-defense rate, accusation-by-role);
  the agent reads the flagged lines for prose. Idempotent + cached like `suss`.
- **Dependency:** AWS creds + Bedrock (Haiku), same as `suss`. The strategy report degrades
  gracefully if `chat_stance`/`chat_suss` partitions are absent (chat questions answered
  qualitatively from raw `chat` text the agent samples), but the intended path runs both extractors.

---

## The probe battery (per question)

Each question is grounded in specific warehouse signal (keys/fields per
`references/event-catalog.md`, patterns per `references/recipes.md`).

### Imposter

| Question | Signal / probe |
|---|---|
| Target selection | `following_interval`/`isolation_interval` self-joined to target's role/policy: which role they follow, preference for already-isolated victims, in-view→follow onset latency (`player_visible_interval` → `following_interval`). |
| Follow closeness | `following_interval.min/median_distance`, `alignment_ratio`, `lag_ratio`; `chase_interval` rate. Field-contrast bar. |
| Lose & reacquire | `following_interval.ended_by`; after a drop, re-entry into a `following_interval` on the **same** target within N ticks = reacquire rate, vs switch target, vs go idle. |
| Can't reacquire → next move | Post-drop behaviour: `headed_to` a new room / re-enters cluster / patrols / idles. |
| No-target search | `entered_room`/`headed_to` distribution + entropy, revisit cadence: structured patrol vs random wander. |
| How far they tail | Follow interval duration + distance distribution (ties to closeness). |
| Pretend to be crew | Imposter `started_task`/`task_attempt` (fake-tasking) rate, loiter time in task rooms, cluster-riding — vs their kill activity. |
| Chat deflect/blame | `chat_suss` (who accused) + `chat_stance` (deflect/defend-self rate, accuse-real-crew misdirection); evidence = the flagged lines. |
| Kill conversion (context) | Recipe-3 isolation→kill conversion, kill latency from ready, post-kill nearest-crew distance (the current objective's core metric). |

### Crewmate

| Question | Signal / probe |
|---|---|
| Task selection & order | `started_task`/`completed_task` sequence → nearest-task-greedy vs assigned-order vs room-clustered; abandon rate by room (recipe 4). |
| Navigation around agents | `proximity_interval`/`isolation_interval` with subject as actor: cluster-seeking vs solo-tasking, median personal-space distance held, flee-on-approach. |
| Meetings | `vote_called_button` rate + trigger context (near a body? isolated? shortly after a kill it witnessed?). |
| Chat & voting / suspicion | Vote correctness (recipe 5), suss accuracy (recipe 6), `chat_stance` accusation targeting, abstention (`vote_timeout`) rate; evidence = flagged lines. |

### Cross-role

Survival curve (when they die; killed vs ejected via `died`/`body`/vote outcome), score composition
by `score.reason`, and a per-episode spread on every metric (consistency vs variance).

---

## Testing / validation

- **Probes:** pytest over a small **synthetic DuckDB fixture** — a handful of hand-built event rows
  (a follow interval, a kill, a task sequence, a couple of chat rows) — asserting each probe's SQL
  returns the expected metric and the subject/field split is correct. This makes the battery
  trustworthy without a live warehouse.
- **`chat_stance`:** a cache-hit + JSON-array-parse test mirroring `suss`'s tests (no live Bedrock
  call in the unit test; the classifier is stubbed).
- **End-to-end deliverable check:** build a real warehouse from a batch of crewborg episodes with
  the confirmed-good expander (`/tmp/expand-043`, covers Prime 0.4.3–0.4.7), run the full pipeline,
  and produce one actual crewborg strategy report — read the rendered HTML at all breakpoints —
  before calling the work done.

---

## Affected files

**New**
- `crewrift_lab/.claude/skills/crewrift-strategy/SKILL.md`
- `crewrift_lab/.claude/skills/crewrift-strategy/scripts/strategy_probes.py`
- `crewrift_lab/.claude/skills/crewrift-strategy/scripts/strategy_report.py`
- `crewrift_lab/.claude/skills/crewrift-strategy/scripts/tests/test_probes.py`
- `crewrift_lab/tools/event-warehouse/crewrift-event-warehouse/crewrift_event_warehouse/chat_stance.py`
- test for `chat_stance` under the warehouse package's `tests/`

**Modified**
- `crewrift-event-warehouse` CLI (`cli.py`) — register the `chat-stance` subcommand.
- `crewrift_lab/AGENTS.md` and/or the warehouse `SKILL.md` "See also" — index the new skill +
  extractor.
- `crewrift_lab/tools/event-warehouse/.../README.md` — document the `chat_stance` event + subcommand.

---

## Risks / open questions

- **Small-n per role.** A warehouse skewed toward one role gives thin data for the other; the report
  must surface `n` per role and the agent must flag low-confidence sections (discipline note in the
  skill). Not a blocker, but a reporting requirement.
- **Chat is sparse and templated.** Non-LLM policies emit little/no chat; the deflect/blame section
  degrades to "minimal chat" rather than fabricating a style. Handled by the graceful-degrade path.
- **Bedrock dependency for chat.** `chat_stance` needs AWS creds + Bedrock like `suss`; without them
  the objective/movement/kill/task/vote sections still render fully and the chat sections fall back
  to raw-text sampling.
- **Interval-event orientation.** `proximity_interval`/`isolation_interval` are global with arbitrary
  `player_a`/`player_b` ordering — probes must handle both orientations (union) per the catalog note.
- **Field contrast with a 3-policy field.** The Prime field is small (crewborg + Aaron + Andre), so
  "field" may be 1–2 other policies; the report states the field composition in `meta` so contrast is
  read honestly.
