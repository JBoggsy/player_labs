# pw_match_report.py: one-page match report per episode

Answers "give me one readable page on this match". Turns one traced episode into a page:
who won and how, the Elo outcome score, the glory composition, a timeline, the top moments with
a zoomed movement panel each, per-seat metrics and replay links. Ink & Print HTML (single
column, fits a 390 px phone; tables scroll sideways) plus a JSON of everything on the page.
Index of all tools: [README.md](README.md).

## Command

```bash
uv run python paintbot_pw_lab/tools/pw_match_report.py ROOT... [--out DIR] [--viewer-base URL] [--tag TAG]
```

- Output per episode: hosted `<episode dir>/pw_report/`, local `NAME.pw_report/` beside
  `NAME.replay` (both inside gitignored data dirs). `--out DIR`: that directory for one episode, or
  `DIR/<episode_id>/` for several (`:` → `_`, so a local episode is `DIR/local_NAME/`).
- Files: `report.html`, `report.json`, `timeline.png` + `.json`, `moment_N.png` + `.json`.
- Episodes that fail to load get no report, are printed `FAILED [code] … (no report)`, and make the
  exit code 1. About 1 s per cached episode (3 reports in 4 s including start-up).

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py report ROOT... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | roots; `--out DIR`, `--viewer-base URL`, `--tag` |
| Outputs | per episode `report.html`, `report.json`, `timeline.png(+json)`, `moment_N.png(+json)`; default `<episode dir>/pw_report/` (hosted) or `NAME.pw_report/` beside a local `NAME.replay` |
| `--json` result | `{reports: [{episode_id, html, json}]}` |
| Exit codes | 0 ok; 1 some episodes failed to load or verify (the rest are used; one `failures[]` entry each, `counts.failed_by_code`); 2 usage error: bad arguments, roots with no episode, or an unknown selector (none beyond the roots; `result.valid` lists the valid values); 3 `pw_trace` not built (`next[0]` = `paintbot_pw_lab/tools/build_tools.sh`); no report is written for a failed episode |
| Idempotence / cache | a rerun rewrites the same directory from the cached tables |
| Typical next step | open `report.html` (or read `report.json`) and link it by path |

## Page contents

1. **Headline and lead**: winner, how it was decided (elimination / meter reached the target /
   higher meter at the time limit / draw), glory, the **Elo outcome score** per team
   (`clamp(0.5 + (own glory − other glory) / 2000, 0, 1)`, `pw_metrics.elo_outcome`), meter, mean hearts held, kills.
2. **Glory**: start − countdown + awards by kind − what settling took = final, per team (exact).
3. **Timeline**: `pw_viz.plot_timeline` with the moments marked by number.
4. **Top moments** (at most 6, in match order), each with its tick, links and a panel:
   - `first_capture`: each team's first `capture_complete` (always shown). If it was taken from the
     other team the title says so and it weighs 2.
   - `heart_lost`: a `capture_complete` whose `previous_owner` was the other team (weight 2).
   - `kill_burst`: ≥ 3 enemy kills by one team, each ≤ 72 ticks after the previous; weight = kills
     − own losses in the span.
   - `elimination`: a team with every cog out (weight 10).
   Selection: first captures, then the rest by weight (earlier first on ties). **The weight is a
   heuristic for what to show, not a measured win-probability swing** (for measured swings use
   [`pw_winprob.py credit`](pw_winprob.md)); the page says so. Thresholds are named constants at the top of the file and in `report.json`
   `evidence.thresholds`.
   Panel: `pw_viz.movement_panel` from 10 s before to 2 s after (kill bursts: 5 s before the first
   kill to 2 s after the last), zoomed to at least 3,600 units around the moment and widened to
   cover every victim and every killer's firing spot (so long-range killers are in view), showing
   seats that were alive inside the box. A black ring marks the moment.
5. **Seats**: per seat (grouped by team) kills, deaths, K/D, shots, gun accuracy (enemy hits /
   rays), HP dealt/taken, captures, alive share, heart-reach share, idle share, stuck ticks, and a
   `VM?` flag for the vm-disabled heuristic. Definitions: [pw_metrics.md](pw_metrics.md); stuck and
   VM? are marked as inferred on the page.
6. **Evidence and links**: engine release, rules, hash verification, the results cross-check
   source, episode notes (e.g. `team_from_parity`), and the link caveats below.

## Replay links

For hosted episodes, from `episode.json`:

- **Observatory episode page**: `https://softmax.com/observatory/v2?tab=episode-requests&detail=episode-request:<ereq_id>`
  (the pattern verified 2026-07-28 in another lab; not re-checked for this tool).
- **Watch replay**: `https://softmax.com/observatory/coworld-replays/<coworld_id>?replay_uri=<encoded replay_url>`,
  with `&t=<tick>` on each moment. The paintbot-pw web viewer seeks to `?t=<tick>`
  (`coworld/paintbot/viewer.js`: `seek(Number(t))`, clamped to the final tick, so `t` is a world
  tick as in our tables). **The Observatory wrapper does not forward `t` to the viewer**
  (metta `page.tsx:6-14`, `CoworldReplayFrame.tsx:1248-1272`), so this link opens at 0:00;
  the page says so and shows the tick to scrub to. Only a directly served viewer
  (`--viewer-base`) honours `t`.
- **`--viewer-base URL`**: when you have a directly served viewer, adds `URL?replay=<encoded
  replay_url>&t=<tick>` links. `report.json` always carries the `viewer_query` string.

`links` (top level and per moment) = `{episode_page, replay_url, observatory_replay,
viewer_query, viewer}` (`viewer` only with `--viewer-base`; `{}` for a local tape).

Local tapes get no links (the page says so).

## report.json

`episode_id, source, path, coworld_version, engine_release, rules, map, ticks, tick_rate, winner,
winner_name, decided_by, teams[{team, name, policies, policy_names, result, glory, elo_outcome,
glory_initial, glory_countdown, glory_<kind>…, glory_settled_loss, meter_points, hearts_held_mean,
hearts_held_end, first_capture_tick, captures, kills, deaths, gun_enemy_accuracy, cogs_out_end,
team_lives_end}], policies[{policy_key, policy_name, seats, team, result, elo_outcome}],
seats[{seat, team, policy_name, kills, deaths, kd, shots, gun_enemy_accuracy, dealt_hp_enemy,
taken_hp, captures_completed, pickups_medkit, alive_share, heart_reach_share, idle_share,
stuck_ticks, vm_disabled_suspect}], moments[{rank, kind, t, team, swing, title, x, z, points?,
from, to, links, image, panel_width}], links, evidence{hash_verified, results_check, notes,
state_every, thresholds}, images`. Unknown values are `null`.

## Verified (2026-09-29, coworld-v0.3.78 build)

- Ran on all 13 episodes then under `episode_data/` (the rules-44 samples plus fresh league episodes another agent had fetched): 13
  reports, 0 failures. Read the full page for `ereq_5092af64…` in headless Chrome at 1,100 px and
  inside a 390 px frame. Its moments match the tables: Ember's first capture H4 at t = 260 (seat 0),
  three Azure kill bursts, Azure retaking H4 from Ember at t = 1468 (seat 5), and Ember eliminated
  at t = 1649.
- The moment-selection and kill-burst rules have unit tests (`tools/tests/test_pw_viz.py`).

2026-09-29, coworld-v0.3.79: a hosted sample and a local recording in one run with
`--out DIR --viewer-base URL` wrote `DIR/<episode_id>/` and `DIR/local_<name>/` (6 moments,
empty `links` for the local tape), exit 0, 3.4 s.

Not verified: that the hosted links open (no browser session against softmax.com here), whether the
wrapper honours `t`, and draws (no draw in the corpus).
