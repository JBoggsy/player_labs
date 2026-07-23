---
name: ctf-ab
description: Use to decide whether a beacon change ACTUALLY helped — A/B the candidate against the baseline head-to-head, fresh, right now, against the same opponent. Triggers': 'did my change help', 'compare v25 vs v24', 'A/B test beacon', 'is the candidate better', 'did the spread change regress wins'. This is the CTF ADAPTER for the game-agnostic coworld-ab skill:' CTF's metrics (win/draw/loss under GV21 scoring, captures, kills/deaths, team kills + stacked-pair ticks from the event warehouse) over the shared stats engine.
---

# CTF A/B

The CTF adapter for the root **`coworld-ab`** skill — read that SKILL.md for the method
(fresh + matched arms, the discipline list, the report renderer). This file covers only
what's CTF-specific.

## Run it

```bash
AB=.claude/skills/coworld-ab/scripts
uv run python ctf_lab/.claude/skills/ctf-ab/scripts/compare.py \
  <baseline_dir> <candidate_dir> \
  --baseline beacon:vM --candidate beacon:vN \
  --target win_rate --json /tmp/ab/diff.json
uv run python "$AB/compare_report.py" /tmp/ab/diff.json --out /tmp/ab/ab.html \
  --eyebrow "CTF · A/B comparison" --finding finding.md --verdict "<one-line>"
```

Each `*_dir` is a `fetch_artifacts.py` output dir (episode dirs with
`episode.json` + `results.json`). The standard CTF A/B shape is **per-opponent
matched pairs**: for each opponent (e.g. focusfire, h006), fire baseline and
candidate 1v1 xreqs back-to-back (8 beacon seats vs 8 opponent seats, 10 eps),
then compare per opponent — CTF outcomes are strongly opponent-dependent, so a
pooled comparison masks matchup-specific regressions.

## CTF-specific reading of the metrics

- **Scoring is GV21**: +1 win / -1 loss / **-1 timeout draw**. `score_mean` cannot
  distinguish a draw from a loss; `draw_rate` is derived from "episode has no
  winner" (no `win` flags set). Watch `win/draw/loss` as a triple — a change that
  converts draws→wins and draws→losses in equal measure moves `win_rate` but not
  `score_mean`.
- **`team_kills_mean` / `stacked_ticks_mean`** come from the batch's event
  warehouse (`<batch_dir>/wh/warehouse.duckdb`, built by `ctf-event-warehouse`).
  Build the warehouse for BOTH arms before comparing, or those rows are skipped:
  team kills = kill events where victim slot parity == killer slot parity;
  stacked ticks = alive pos snapshots with a same-team player <25px.
- **kills/deaths in results.json are NULL on league episodes at 0.7.69+** but
  populated on experience-request episodes — A/Bs run on xreqs, so they're live
  here; don't reuse this adapter on league-round batches without checking.
