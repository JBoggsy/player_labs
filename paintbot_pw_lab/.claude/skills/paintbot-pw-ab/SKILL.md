---
name: paintbot-pw-ab
description: "Use when someone asks whether a Paintbot PW change actually helped — 'did v5 beat v4', 'A/B the candidate', 'is the new BASIC better against the leaders', 'can we stop the eval yet'. Binds the shared coworld-ab method to this lab: pick a design (paired vs a common opponent, head-to-head, or field), compose pinned 8-vs-8 request bodies, create them (within lab authorization; costs XP credits), stream, stop by SPRT or fixed N, run compare.py, review replays, record ids with the verdict. Agent-drivable: `pw.py ab-requests|compare ... --json`."
---

# Paintbot PW A/B

Decide whether a candidate BASIC policy beats the baseline **now**, on the ladder's own
number: the **score outcome** `clamp(0.5 + (our mean result score − their mean result score)/(2 × margin_scale), 0, 1)` per
episode. Recheck the live ranking scale; the 2026-10-05 OpenSkill scale is 600. Pass
`--target score_outcome --margin-scale 600` explicitly; the default `elo_outcome` remains historical ([docs/mechanics.md §1](../../../docs/mechanics.md)). Read the shared
[`coworld-ab`](../../../../.claude/skills/coworld-ab/SKILL.md) skill for the method (fresh,
matched, pin every seat, respect inconclusive). This file is the Paintbot PW binding. Tool
references: [compare.md](../../../docs/tools/compare.md),
[pw_ab_requests.md](../../../docs/tools/pw_ab_requests.md), and the index
[docs/tools/README.md](../../../docs/tools/README.md).

## Procedure

Run from the repo root (`personal_labs_paintbot_pw/`).

1. **Frame it.** Baseline and candidate as exact `name:vN` (both uploaded), the one change
   between them, the target metric (use `score_outcome` with the verified margin scale), and the metric list you will
   report (`--metrics`; fewer metrics = a less strict BY correction). Write down the stopping
   rule: SPRT H0/H1/α/β (default 0 / +0.05 / 0.05 / 0.05) or a fixed N with no peeking.

2. **Pick the design.**

   | Design | Use when | Cost |
   | --- | --- | --- |
   | `paired` (default) | "better against X": both arms vs the same opponent, same seeds, both sides | one request per (arm, opponent, side, seed): 15 seeds = 60 requests per opponent for 30 pairs |
   | `h2h` | runtime or mechanism diagnosis only | **local only**: two of our own policies is self-play, and hosted XP self-play is forbidden (`user_preferences.md`); the composer refuses it. Run `pw.py local screen CAND.bas BASE.bas --seeds 1-20 --record DIR --record-seeds 1-20` (`--record` needs `--record-seeds`), then `pw.py compare compare DIR --design h2h --baseline local:BASE.bas --candidate local:CAND.bas`. Neither winning nor losing locally is a performance signal; never select or reject a candidate on this result |
   | `field` | closest to the ladder: both arms vs several leaders, unpaired | per (arm, opponent, side); also the cheap fallback for one opponent without seeds (4 requests) |

   Opponents: the current leaders as exact `name:vN` refs. `uv run python paintbot_pw_lab/tools/pw.py leaders --top 3 --json`
   lists them (`result.leaders[].policy_ref`), naming every entrant from the latest public round's
   episodes, including the rows with a null `policy_label` that the shared resolver skips
   ([pw_scout.md § leaders](../../../docs/tools/pw_scout.md#leaders), [docs/field.md](../../../docs/field.md)).
   Never `top_n`/`random` seats in an A/B: 8 sampled seats are 7+ different champions on one team.

3. **Compose the bodies (no API call).**

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py ab-requests --design paired \
       --baseline OURS:v4 --candidate OURS:v5 --opponent LEADER:v12 --seeds 1-15 \
       --league-id league_... --run-id ab-v5-v4-1 --out paintbot_pw_lab/episode_data/ab-v5-v4-1/requests --json
   ```

   A fixed `--run-id` makes the bodies (and their idempotency keys) identical on a rerun, so
   re-composing never doubles a request.

   Check one body with `experience_request.py create BODY --check-schema` (read-only).
   Tell the human the design, request count, episode total and credit estimate (the plan
   assumes0.5 credits per episode; creation cost_preview is authoritative).

4. **Create.** Creating hosted experience requests is within the lab's authorization
   (`user_preferences.md`: create them without asking first when they answer the current
   question; never for self-play), but every episode **costs XP credits**: report the design,
   request count and credit estimate as an update, and start the XP dashboard for any request
   over 16 episodes. One body per call with the shared [`coworld-experience-requests`](../../../../.claude/skills/coworld-experience-requests/SKILL.md)
   helper; save each returned `xreq_…` id next to its label in the manifest (add an
   `xreq_id` field). Fire both arms back to back so field drift hits both.

   ```bash
   S=.claude/skills/coworld-experience-requests/scripts/experience_request.py
   uv run python "$S" create paintbot_pw_lab/episode_data/ab-v5-v4-1/requests/bodies/<label>.json
   ```

5. **Stream artifacts** into one directory per run (arms are told apart by policy, so one
   tree is fine). For many small requests, fetch them one after another rather than one
   watcher each, and back off on HTTP 429.

   ```bash
   uv run python .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py \
       --xreq xreq_... --watch --no-logs --out paintbot_pw_lab/episode_data/ab-v5-v4-1/episodes
   ```

   Keep seat logs (drop `--no-logs`) for our own policy when the question involves VM errors.

6. **Stop by SPRT** (or at the fixed N). Re-run as episodes land; traces are cached:

   ```bash
   uv run python paintbot_pw_lab/tools/pw.py compare sprt paintbot_pw_lab/episode_data/ab-v5-v4-1/episodes \
       --design paired --baseline OURS:v4 --candidate OURS:v5 --target score_outcome --margin-scale 600 --h0 0 --h1 0.05 --json
   ```

   The decision is `result.decision` (`continue`, `accept_h1`, `accept_h0`) with `result.llr` and
   its bounds.

   `continue` below 30 observations is by design. On `accept_h1`/`accept_h0`, cancelling the
   rest saves credits; say so in the update. Local fake arms showed per-pair SD ≈ 0.40 (pairing
   barely reduced variance there: unpaired differences of single-arm SD 0.31 would give ≈ 0.44), so H1 = +0.05 can take ~300 pairs; if that
   is unaffordable, raise H1 and say so ([compare.md](../../../docs/tools/compare.md)).

7. **Compare and render.**

   ```bash
   R=paintbot_pw_lab/episode_data/ab-v5-v4-1
   uv run python paintbot_pw_lab/tools/pw.py compare compare $R/episodes --design paired \
       --baseline OURS:v4 --candidate OURS:v5 --target score_outcome --margin-scale 600 --metrics score_outcome,win_rate,first_capture_rate,ops_fail_rate \
       --requests $R/requests/manifest.json --out $R/ab.json --json
   uv run python .claude/skills/coworld-ab/scripts/compare_report.py $R/ab.json --out $R/ab.html \
       --eyebrow "Paintbot PW · A/B comparison" --finding finding.md --verdict "..."
   ```

   `--out` writes the full result with every row (the renderer's input); `--json` prints the
   envelope (deltas, SPRT, exclusions; exit 1 if any episode failed to load). Read the
   "Exclusions and failure handling" line (`counts.exclusions`) before any number. `ops_fail_forfeit_scored`
   for our side means our build crashed episodes (a real regression, and 3 in a row
   disqualifies a league entry); any `LOAD FAILED` means re-fetch or investigate before
   trusting the result.

8. **Review replays qualitatively.** Pick 2–3 episodes per arm (a big loss, a typical game,
   the largest paired swing from the JSON `rows`) and unpack them with
   [`paintbot-pw-replay`](../paintbot-pw-replay/SKILL.md). Write what changed in behaviour
   into `finding.md`.

9. **Record** the verdict with the xreq ids, the manifest, `ab.json`, the design, the
   pre-registered metrics and the SPRT parameters in the lab's experiment record
   (WORKING_CONTEXT / the experiment's design doc), then propose the next step and pause.

## Pitfalls

- **Never pool rules or coworld versions** (compare.py refuses). A league tag bump mid-run
  splits the batch.
- **Engine seeds.** An explicit `game_config_overrides.seed` reaches the engine, so seed-paired
  requests play identical worlds (modulo the opponents' own behaviour); a league episode's API
  `seed: 2026` is a placeholder, not its world ([docs/field.md § Seeds](../../../docs/field.md#seeds-what-actually-reaches-the-engine)).
  `pairs_with_different_engine_seeds` should be 0; if it is not, the pairing matched requests,
  not worlds.
- **One single-episode request per (arm, opponent, side, seed).** An explicit seed makes every
  episode of its request the same world, so with the same roster extra episodes replay one
  match: they cost credits and add no information (compare.py keeps one copy, `duplicate_game`).
  Use more seeds, not more episodes per seed (the composer's default `--episodes 1`).
- **Head-to-head is not performance evidence.** Every clean candidate proceeds to hosted
  `paired` or `field` evaluation against real opponents regardless of local wins or losses.
- **Local arms are not performance evidence and cannot veto or rank candidates.** `pw.py local`/`paintbot-headless` recordings are for
  checking the tools and mechanisms ([`paintbot-pw-local`](../paintbot-pw-local/SKILL.md)).
- **After an SPRT stop**, the secondary metrics' p-values are descriptive only.

## Autonomous use

- **Preconditions:** `uv run python paintbot_pw_lab/tools/pw.py doctor --json` exits 0; baseline and candidate are uploaded
  versions (`name:vN`); the question and stopping rule are written down (step 1).
- **Commands:** `leaders --json` for opponent refs, `ab-requests ... --run-id ID --out RUN/requests --json` (no API call), create
  each body with the shared experience-request helper, stream artifacts into `RUN/episodes`,
  then loop `compare sprt RUN/episodes ... --json` as episodes land (cached traces make each pass
  cheap) and finish with `compare compare ... --out RUN/ab.json --json`.
- **Reading the envelopes:** `leaders` → `result.leaders[]` (rank, player, policy_ref, mmr);
  `ab-requests` → `result.requests[]` (label, arm, policy, side, opponent, seed, body)
  and `counts.episodes`; `compare sprt` → `result.decision`; `compare compare` → `result.deltas`
  (per metric and group: `base`, `cand`, `effect`, `p`, `verdict`, `test`), `result.sprt`, `counts.exclusions`, and
  `failures[]` for episodes that did not load.
- **Exit codes:** 0 use it. 1 some episodes failed to load: re-fetch them (a missing artifact is
  "retry") before trusting the verdict (`leaders`: 1 with code `rate_limited` = wait and retry).
  2 an arm policy is unknown or ambiguous (`result.valid` lists the labels), both arms share an
  episode (use `--design h2h`), rules versions are pooled (split the roots), or `ab-requests` was
  asked for `h2h` / given no target, `--opponent` or `--seeds` where the design needs them.
  3 run `next[0]` (build) and rerun.
- **Human gates:** creating experience requests is within lab authorization but **costs XP
  credits**: report the count and estimate. Never use XP requests for self-play. League
  **submission** of the winner and any public forum or wiki post are explicitly gated: stop and
  propose.
