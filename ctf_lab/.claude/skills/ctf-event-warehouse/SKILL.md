---
name: ctf-event-warehouse
description: "Build and query the CTF event warehouse — a policy-indexed DuckDB/Parquet dataset of gameplay events (kills, flag steals/returns, captures, respawns, scores) + beacon belief traces (snapshots, objective/alive/engage transitions) over many episodes — for deep, mechanistic, cross-episode questions about a policy's behaviour. Triggers: 'what fraction of beacon's steals get delivered', 'where do carriers die on the return', 'is the escort near the carrier', 'build the CTF warehouse for this batch', 'query the CTF events', 'beacon delivery rate / capture conversion'."
---

# CTF Event Warehouse

The deep-dig tool for CTF. `agg_eval.py` gives a one-line scoreline from results.json; the
warehouse tells you **how** — it re-simulates every episode's replay into ground-truth game
events, reads beacon's per-episode belief trace, **re-keys both from episode *slot* to
policy / version / team / seat / role**, and collates them into a queryable **DuckDB +
Parquet** store. Ask cross-episode, by-policy, by-role behavioural questions in SQL.

The tool is `ctf_lab/tools/event_warehouse.py` (one file, run via `uv`). It ingests two feeds:

- **replay events** (ground truth) — via the version-matched `expand_replay_json` binary
  (build it first, below): `kill`, `flag_steal`, `flag_return_home`, `capture`, `respawn`,
  `score`, `phase`, `game_over`, each with tick + actor slot.
- **beacon trace events** — from beacon's per-episode trace (the `jsonl@artifact` member, or
  the folded `CTF_DIAG` policy log): `snapshot` (full belief), `objective`, `alive`, `engage`.

**Use it when** a survey/A-B question needs the actual behaviour: capture-conversion /
delivery rate, where carriers die, escort proximity, engagement outcomes, objective
time-share. **Don't** use it for a quick batch scoreline — that's `tools/agg_eval.py`.

## Build it

1. **Build the version-matched replay reader once** (needs the Nim toolchain; fetches the
   private game repo via `gh`):
   ```bash
   ctf_lab/tools/build_expand_replay.sh          # builds bin/expand_replay + bin/expand_replay_json
   ```
   If it prints `hash failed` on a FRESH replay, the league redeployed the game — bump
   `CTF_REF` in `ctf_lab/tools/versions.env` and rebuild (`--force`).

2. **Pull episodes WITH replays + logs** (the warehouse needs them — do NOT use the
   `--no-replay/--no-logs` results-only fetch here):
   ```bash
   uv run python .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py \
       --xreq <xreq_id> --elevated -o ctf_lab/scratch/<batch>
   ```

3. **Build the warehouse** (`--episodes` is repeatable; point at a batch dir or a single
   episode dir):
   ```bash
   uv run python ctf_lab/tools/event_warehouse.py \
       --episodes ctf_lab/scratch/<batch> --out ctf_lab/scratch/wh_<batch>
   ```
   It prints row counts and **flags hash-failed episodes** (version skew → their replay
   events are absent; bump `CTF_REF`).

## Query it

```bash
duckdb ctf_lab/scratch/wh_<batch>/warehouse.duckdb
```

Tables: `episodes` (winner, per-team score), `participants` (slot → policy/version/team/
seat/role/outcome), `replay_events` (joined to the actor's identity), `trace_events`
(belief snapshots + transitions, with `self_x/self_y`, `objective`, `alive`, `i_carry`,
`n_enemies`, and the full `data_json`).

Recipe queries (the questions the warehouse exists for):

```sql
-- Delivery rate: steals vs captures by policy (why beacon wins/loses)
SELECT actor_policy,
       SUM(key='flag_steal')::INT steals, SUM(key='capture')::INT captures
FROM replay_events WHERE actor_policy IS NOT NULL GROUP BY actor_policy;

-- Where beacon dies, by role (cross-episode) — from the belief trace
SELECT role, COUNT(*) FROM trace_events
WHERE name='alive' AND alive=false AND policy_name='beacon' GROUP BY role;

-- Objective time-share (what beacon spends ticks doing)
SELECT objective, COUNT(*) FROM trace_events
WHERE policy_name='beacon' AND name='snapshot' GROUP BY objective ORDER BY 2 DESC;

-- Escort check: attacker distance to the carrier while a teammate carries (needs
-- self_x/self_y from trace_events joined to the flag position in replay_events).
```

## Discipline

- **Version skew is the #1 failure.** A hash-failed episode silently drops its replay
  events; the build logs it — bump `CTF_REF` when a FRESH batch hash-fails.
- **Attribute by policy_version_id / policy_name, never by display name** (game-assigned,
  varies; a `top_n`/`random` roster can even seat your own policy as the opponent).
- **Role labels are inferred** from beacon's version (v2-v4 = 5 defenders, v5 = 3); pre-role
  v1 rows carry a nominal label only. Trust `replay_events` (ground truth) over inferred
  role for anything load-bearing.
- Pair with `tools/agg_eval.py` (fast scoreline) and `coworld-episode-artifacts` (the pull).
