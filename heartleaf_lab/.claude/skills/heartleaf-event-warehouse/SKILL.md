---
name: heartleaf-event-warehouse
description: "Use to fetch and query the Heartleaf event warehouse — the HOSTED heartleaf-round-warehouse reporter on Observatory that re-simulates every episode of a round (or your xreq) into five queryable Parquet/JSON parts: events, player_stats, dinner_edges, chats (LLM invitation-classified), manifest — for deep, cross-episode, by-policy behavioural questions. Triggers: 'how many guests does cady draw', 'who dines with whom', 'invitation success rate', 'where does the score come from', 'fetch the warehouse for round X / this xreq', 'query heartleaf events'."
---

# Heartleaf Event Warehouse

The deep-dig tool for Heartleaf. Unlike the Crewrift/CTF warehouses (built locally from
downloaded replays), Heartleaf's warehouse is a **hosted v2 wasm reporter on Observatory** —
`heartleaf-round-warehouse` (`rptr_5c331a88-9403-455e-b736-316f63622714`, ours). It fires
automatically on **every closed Heartleaf league round**, re-simulates each episode's replay
server-side (the Heartleaf sim is compiled into the wasm at `heartleaf_ref`), re-keys events
from slot to **policy identity**, and emits five typed output parts per run:

| part | format | one row per |
|---|---|---|
| `events` | Parquet | player-tagged event — `episode_id, tick, day, slot, policy_version, policy_name, kind, value(JSON)`. Kinds: `join{home}`, `harvest{amount,total,foods}`, `enter_house/exit_house{house,own}`, `chat{text,heard_count,heard_by}`, `dinner{host,host_slot,was_host,guests,food,score}`, `score{amount,total}`, `leave`; `trace_warning{message,fail_tick}` on hash mismatch |
| `player_stats` | Parquet | (episode, slot) — ~45 behavioural columns: identity/outcome (`won`, `final_score`, `score_rank`), movement, space/home fractions, gardening, **dinner hosting** (`dinners_hosted`, `avg_guests_hosted`, `score_per_hosted_dinner`), chat/social reach, dining-network scalars, day→evening rhythm |
| `dinner_edges` | Parquet | (episode, host_slot, guest_slot) — the directed dining network with `times`, `total_food`, `total_score` |
| `chats` | Parquet | chat — text + audience + **LLM-classified `is_invitation`** (regex fallback: `classifier` column) + a deterministic `success_rate` (did hearers attend the advertised party that night) |
| `manifest` | JSON | run summary — per-episode ok/skipped/failed, `events_written`, `heartleaf_ref` |

**Use it when** a question needs actual behaviour across episodes: guests-per-party,
invitation conversion, who-dines-with-whom, harvest rhythm, where score comes from.
**Don't** re-derive any of this locally from replays — the reporter already did it.

## Get it

Everything goes through the wrapper (auth from `softmax login`):

```bash
W=heartleaf_lab/.claude/skills/heartleaf-event-warehouse/scripts/warehouse.py

uv run python "$W" list-runs                     # recent runs (newest first)
# League rounds — the warehouse ALREADY EXISTS, just fetch:
uv run python "$W" fetch --last 5 --out /tmp/hl_wh          # N most recent round runs
uv run python "$W" fetch --round round_<id> --out /tmp/hl_wh
uv run python "$W" fetch --run rrun_<id> --out /tmp/hl_wh   # exact run id
# Your own experience request — trigger an on-demand run, poll, download:
uv run python "$W" run-xreq --xreq xreq_<id> --out /tmp/hl_wh
```

Each run lands in `out/<rrun_id>/{events,player_stats,dinner_edges,chats}.parquet +
manifest.json`, so multi-round warehouses are one glob. `--run/--round/--last` combine
and dedupe; `run-xreq` requires the xreq to be terminal (409 otherwise).

## Query it

```python
import duckdb; con = duckdb.connect()
for t in ("events","player_stats","dinner_edges","chats"):
    con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('/tmp/hl_wh/*/{t}.parquet')")
```

```sql
-- Where does each policy's score come from? (hosting is the ONLY scorer)
SELECT policy_name, COUNT(*) games, ROUND(AVG(final_score),1) score,
       ROUND(AVG(dinners_hosted),2) hosted, ROUND(AVG(avg_guests_hosted),2) guests_per
FROM player_stats GROUP BY 1 ORDER BY score DESC;

-- Invitation conversion (the current score lever: guests-per-party).
-- NB speaker_policy is a version UUID and often NULL; speaker_name is the readable key.
SELECT speaker_name, COUNT(*) invites, ROUND(AVG(success_rate),3) AS conv
FROM chats WHERE is_invitation GROUP BY 1 ORDER BY invites DESC;

-- Who dines with whom (repeat relationships). host_policy/guest_policy are version
-- UUIDs (NULL in xreq runs) — join player_stats on (episode_id, slot) for names.
SELECT h.policy_name AS host, g.policy_name AS guest, SUM(e.times) meals
FROM dinner_edges e
JOIN player_stats h ON h.episode_id=e.episode_id AND h.slot=e.host_slot
JOIN player_stats g ON g.episode_id=e.episode_id AND g.slot=e.guest_slot
GROUP BY 1,2 ORDER BY meals DESC;

-- Dinner ground truth from events (value is JSON — extract per kind)
SELECT policy_name, json_extract_string(value,'$.host') host,
       CAST(json_extract(value,'$.score') AS INT) pts
FROM events WHERE kind='dinner' AND CAST(json_extract(value,'$.was_host') AS BOOLEAN);
```

## Discipline

- **Check the manifest before trusting a run**: `episodes_ok` vs `episodes_total`, and any
  `trace_warning` rows. A per-tick hash mismatch means the league game moved past the
  reporter's compiled sim (`heartleaf_ref`, currently `ffa907e`) — partial events survive
  with a `trace_warning` event; the fix is a reporter rebuild (source:
  `~/coding/role_repos/reporter_lab/heartleaf/reporters/roundwarehouse/`).
- **`run-xreq` only makes sense on Heartleaf xreqs.** Feed it another game's episodes and
  every episode fails `Replay magic does not match` (the run still "completes" — read the
  manifest, not the run status).
- **In xreq (episodes-subject) runs, `policy_version` can be NULL** while `policy_name`
  (e.g. `Cady (Ivan)`, `player_3 (Yura)`) is populated — key on `policy_name` there;
  round runs populate both.
- `list-runs`/`fetch --round` see only the **latest 100 runs** (~2 days of rounds). For
  older rounds, keep the `rrun_` id or query the API directly.
- Reporter identity, output contract, and run API: `GET /v2/reporters/{id}`,
  `/v2/reporters/runs/{rrun}/output[/{part}]` — the parts' full column lists live in the
  reporter's declared `outputs[].description` (self-documenting; fetch the reporter detail).

## See also

- **`coworld-experience-requests`** — create the batches this deep-digs.
- **`heartleaf-gossip`** reporter — the narrative sibling that chains this warehouse.
- `crewrift-event-warehouse` / `ctf-event-warehouse` — same idea, built locally; this one
  is hosted, so there is no expand_replay build step and no artifact download.
