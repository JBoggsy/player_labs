---
name: crewrift-belief-audit
description: "Use to compare what crewborg BELIEVED against what was TRUE — sync its policy-artifact belief telemetry into the event warehouse as belief_* partitions, then scan for systematic belief-vs-ground-truth divergences (wrong confirmed imposters, crew-topped rankings, phantom/lagged deaths, votes against own belief, clock desync). Triggers: 'where do crewborg's beliefs diverge from reality', 'sync beliefs with ground truth', 'build the belief log', 'is its suspicion ranking right', 'did it know X was dead', 'audit the beliefs on this batch'. Pairs with crewrift-event-warehouse (build the warehouse first) and feeds crewrift-diagnose (divergences are hypothesis fuel)."
---

# Crewrift Belief Audit

The warehouse (`crewrift-event-warehouse`) holds the **objective** story — what actually
happened, per tick, from expanded replays. Crewborg's policy-artifact telemetry holds the
**subjective** story — what it perceived, believed, and decided. This skill joins the two
into one dataset and scans the joint log for the places belief and reality **diverge** —
which is usually where the improvement mechanism lives (crewrift-diagnose §2: "the gap
between what was true and what it chose").

Two scripts, run in order, both idempotent:

1. **`scripts/build_belief_log.py`** — extracts the belief-relevant `domain.*` trace events
   from every subject seat's `artifacts/policy_artifact_<slot>.zip` and writes them as
   native warehouse partitions (`events/key=belief_<name>/…`), enriched at write time with
   ground truth so downstream queries never need the zips again.
2. **`scripts/scan_divergences.py`** — reads only the warehouse and emits every
   belief-vs-truth divergence as one typed row, with per-kind/per-role rates and examples.

## Prerequisites

- Episodes fetched **with artifacts** (`coworld-episode-artifacts`; `--elevated` if any
  opponents' seats matter — but the subject's own artifact comes with normal auth).
- A warehouse built over those same episodes (`crewrift-event-warehouse`,
  version-matched `--expand-replay`). The join needs its `player_manifest` (color↔slot↔role
  ground truth), `phase`, `kill`/`died`, and `episode_players.parquet`.
- The subject's recipe should carry `CREWBORG_TRACE_GROUPS=all` (the standard eval recipe
  does). Without the belief/knowledge groups, most partitions will simply be empty.

## 1. Build the synced belief log

```bash
B=crewrift_lab/.claude/skills/crewrift-belief-audit/scripts/build_belief_log.py
uv run python "$B" --warehouse /tmp/wh --episodes /tmp/wh_episodes   # --policy crewborg default
```

What it does, and why it's trustworthy:

- **The clock is already shared.** Telemetry `tick` IS the server tick — the bridge drives
  the SDK runtime from the engine's tick-marker sprite (`crewborg/docs/trace-logs.md`,
  "Line format") — so belief rows align to warehouse `ts` directly. No offset estimation.
- **…but it verifies anyway.** Per seat it compares `domain.phase_change` ticks to the
  replay's `phase` events and writes `belief_sync_report.json`; a median offset > 30 ticks
  flags the seat (`sync_ok: false` — reconnect stall / marker loss; the Thread-5 lesson is
  that a lagging client clock silently invalidates deadline reasoning, so **check the flag
  before trusting per-tick joins on an episode**).
- **Identity is joined at write time.** Crewborg speaks *colors*, the warehouse speaks
  *slots*. Every belief row's `value` gains `truth_roles` — `{color: crew|imposter}` ground
  truth for every color the payload mentions — plus `self_slot` / `self_color`. Role
  strings are normalized (`crewmate` → `crew`).

Default extraction set (see `belief_common.BELIEF_EVENTS`): phase/role/teammate belief,
body sightings, believed deaths, per-suspect observation intervals, confirmed/believed
imposter set moves, meeting suspicion snapshots + decisions + LLM path, chat in/out, votes,
kill/report/vent attempts, tasks, chat-evidence, honor-society events, occupancy
reacquisitions. Heavy per-tick families (`decision_snapshot`, `suspicion_tick`, viewer)
are excluded by default — add via `--include domain.decision_snapshot` for a targeted dig.

### Query it like any other partition

```sql
-- suspicion ranking accuracy per meeting: was the top suspect truly an imposter?
SELECT episode_id, ts,
       json_extract_string(value,'$.ranking[0].color')                    AS top_color,
       json_extract(value,'$.ranking[0].p')::double                       AS top_p,
       json_extract_string(value,'$.truth_roles.' ||
         json_extract_string(value,'$.ranking[0].color'))                 AS top_true_role
FROM read_parquet('/tmp/wh/events/key=belief_suspicion_snapshot/*.parquet')
WHERE json_extract_string(value,'$.role') = 'crewmate';
```

Belief rows carry the standard 8-column warehouse schema, so they join to ground-truth
partitions on `(episode_id, ts)` and to `episode_players` on `(episode_id, slot)` exactly
as `references/event-catalog.md` describes.

## 2. Scan for divergences

```bash
S=crewrift_lab/.claude/skills/crewrift-belief-audit/scripts/scan_divergences.py
uv run python "$S" --warehouse /tmp/wh          # -> /tmp/wh/belief_divergences.jsonl
```

One row per divergence: `(episode_id, slot, ts, role, kind, severity, detail)`. Kinds:

| kind | severity | meaning |
|---|---|---|
| `confirmed_crew` | high | witnessed-imposter set gained a truly-crew color (witness false positive — the class behind the HS liar-ledger ground-truth gate) |
| `believed_crew` | medium | over-the-flee-bar set gained a truly-crew color |
| `teammate_wrong` | high | imposter's teammate belief includes a crew color |
| `teammate_incomplete` | low | imposter never completed teammate identification |
| `ranking_top_crew` | high | meeting ranking topped a crew color at p ≥ `--confident-bar` (default 0.5) while a true imposter ranked lower |
| `imposter_unranked` | medium | a live true imposter missing from a meeting ranking |
| `death_belief_lag` | low | belief noticed a death > `--death-lag-tol` (default 240) ticks late |
| `phantom_death` | high | belief recorded a death the replay never shows |
| `vote_crew_over_imposter` | high | voted a truly-crew target while its OWN ranking had a true imposter at ≥ that posterior (vote against own belief — decision-layer, not belief-layer) |
| `role_mismatch` | high | `role_resolved` disagrees with the seat's true role |
| `clock_desync` | medium | the build's phase-alignment check flagged the seat |

The console output gives per-kind × per-role counts and per-seat rates plus worst examples;
the JSONL is the full set for downstream stats (rate deltas across versions, correlation
with losses, etc.).

## Reading the results (what matters, what doesn't)

- **Rates, not incidents.** A single `imposter_unranked` is normal (the imposter may
  genuinely have shown nothing); a *rate* materially above other versions', or clustered in
  lost episodes, is a lever. Join `belief_divergences.jsonl` to `episode_players` on
  `(episode_id, slot)` for win/loss splits.
- **`vote_crew_over_imposter` is the decision layer, not the belief layer** — the belief
  was right and the action contradicted it. Route those to the meeting/vote path
  (`modes/attend_meeting.py`), not to suspicion.
- **Known, already-shipped divergence classes** (don't rediscover): belief-clock lag under
  meeting load (fixed v111 — spend-read cache + auto-submit margin; `clock_desync` now
  catches the residual reconnect-stall class), the bimodal posterior ceiling (W2: softer
  bars unlock nothing, the separation lives in social counters — suspicion-v5 refit is the
  open lever), HS witness false positives (gated by `tools/harvest_liars.py`).
- Divergence rows are **evidence for crewrift-diagnose**, which turns them into mechanistic
  hypotheses → `crewrift-experiment` tests them.

## See also

- **`crewrift-event-warehouse`** — build the ground-truth side first; its
  `references/event-catalog.md` documents every truth partition these tools join against.
- **`crewrift-diagnose`** — consumes the divergence report as hypothesis fuel.
- [`crewborg/docs/trace-logs.md`](../../../crewrift/crewborg/docs/trace-logs.md) — the belief
  telemetry format reference (event families, tick semantics, reading caveats).
- Tests: `crewrift_lab/tools/tests/test_belief_audit.py` (synthetic episode with planted
  divergences; run `uv run pytest crewrift_lab/tools/tests/test_belief_audit.py`).
