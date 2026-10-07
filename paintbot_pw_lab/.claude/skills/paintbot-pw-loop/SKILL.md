---
name: paintbot-pw-loop
description: "Use when an agent should run the Paintbot PW improvement loop on its own — 'run the loop', 'keep improving the policy', a /loop or scheduled job over paintbot_pw_lab, or any unattended evaluate → diagnose → change → A/B cycle. Works only under a loop charter authorized by James in paintbot_pw_lab/WORKING_CONTEXT.md; every step is a pw.py command with a --json result and a rule for each exit code."
---

# Paintbot PW autonomous improvement loop

One loop iteration evaluates the current accepted policy, finds its weakest point, makes one
attributable change, compiles it through G1–G5, uploads it, A/Bs it against the field, and records the
verdict. `policy_file` always means strategy source, never compiled BASIC. Each step below names the command, the JSON field to read, and what to do on each
outcome. The step skills hold the detail:
[paintbot-pw-ab](../paintbot-pw-ab/SKILL.md), [paintbot-pw-diagnose](../paintbot-pw-diagnose/SKILL.md),
[paintbot-pw-local](../paintbot-pw-local/SKILL.md), [paintbot-pw-replay](../paintbot-pw-replay/SKILL.md),
[paintbot-pw-scout](../paintbot-pw-scout/SKILL.md), [paintbot-pw-tune](../paintbot-pw-tune/SKILL.md).
Tool index and the shared CLI contract: [docs/tools/README.md](../../../docs/tools/README.md).
Scoring and rank (what "better" means): [docs/mechanics.md §1](../../../docs/mechanics.md).

Run every command from the repo root (`personal_labs_paintbot_pw/`). Every `pw.py` command
takes `--json` and prints one object: `ok`, `outputs`, `counts`, `failures`, `result`, `next`.
Exit codes are uniform: **0** ok, **1** some inputs failed (partial results written, read
`failures`), **2** usage error (`result.valid` lists valid values: fix the call, never retry
unchanged), **3** a build or environment is missing (run the command in `next[0]`, then retry once).

## 0. The charter (required; the loop stops without it)

The loop acts only inside an objective James has authorized (repo `AGENTS.md`: authorization,
propose-and-pause). Read the `## Loop charter` section of
[`paintbot_pw_lab/WORKING_CONTEXT.md`](../../../WORKING_CONTEXT.md). If it is missing or
incomplete, **stop**: write a proposed charter into your report and report to the orchestrator and wait for PROCEED. It must name:

| Field | Meaning |
| --- | --- |
| `objective` | the target, e.g. "raise mean score_outcome vs the top 3 champions" |
| `policy_file` | the source we edit, e.g. `paintbot_pw_lab/strategy/STRATEGY.md` plus authored `skills/*/skill.bas` |
| `policy_name` | the upload name (`coworld upload-policy --name`) and the player identity to use |
| `baseline` | the accepted version `name:vN` (the loop updates this line on an accepted change) |
| `opponents` | explicit `policy_ref`s to evaluate against, never `top_n`/`random` |
| `allowed_changes` | the classes of change the loop may make on its own (e.g. "constants and thresholds", "target selection", "routing"); anything else is a new strategic direction |
| `credit_budget` | max XP credits per iteration and per day (budget 0.5 credits per episode) |
| `max_iterations` | iterations before the loop stops and reports |

## 1. Preflight

```bash
uv run python paintbot_pw_lab/tools/pw.py doctor --json
```

- exit 0 → continue.
- exit 3 → run each command in `next`, then rerun `doctor` once; still 3 → stop and report.
- exit 1 with failure code `rate_limited` or `api_unavailable` (the league check could not run)
  → wait and rerun `doctor`; do not move the pin. Nothing is missing.
- exit 1 with failure code `stale` (the league moved past `tools/release.env`) →
  `uv run python paintbot_pw_lab/tools/pw.py deployed-ref --write --json`, then
  `pw.py build` and `pw.py build-native` (shell build scripts: no `--json`, and their only
  argument is an optional tag; exit 0 = built). Read the `deployed-ref` envelope's
  `result.docs_rule_files_changed` (a count): if any rule-bearing engine file changed since
  `PW_DOCS_SHA`, the mechanics may have changed. **Stop the loop** and report `result.rule_diffstat` (and `result.docs_to_reverify`);
  re-verifying the mechanics docs comes first. Also re-read the league ranking settings if the
  charter's objective depends on them.
- `doctor`'s `result.loop` says whether the charter is complete (`ready`, `missing`): if not
  ready, stop here (step 0).
- Confirm identity before any upload: `uv run coworld player list` must mark the charter's
  player as active (●); switch with `uv run coworld player use` (James's user-level `coworld-player-swap` skill covers the details). (`softmax status` shows only
  the user, not the player.)

## 2. Evaluate the baseline

Skip if a fresh evaluation of `baseline` vs every charter opponent exists for the current
`release.env` tag (check `WORKING_CONTEXT.md`, which records the last evaluation's request ids).
If the charter names opponents by role ("the top 3") rather than exact refs, resolve today's
champions first; the shared resolver skips champions with a null leaderboard label (often the #1):

```bash
uv run python paintbot_pw_lab/tools/pw.py leaders --json   # result.leaders[]: rank, player, player_id, policy_ref (name:vN), policy_version_id, mmr, owner
```

`leaders` names every entrant from the round's episodes, so it also covers the champions the
resolver skips. Exit 1 with code `rate_limited` means wait and retry; 3 means the public API is
unreachable.

```bash
# the same policy as --baseline and --candidate = evaluate that one policy (one arm)
uv run python paintbot_pw_lab/tools/pw.py ab-requests --design field --baseline BASE:vN \
  --candidate BASE:vN --opponent OPP:vM [--opponent ...] --episodes 10 \
  --league-id league_ae677105-0ab8-4561-81ec-c9cf6735821c --run-id eval-<date> --out RUN/requests --json
```

Create the bodies with the shared skill (`experience_request.py create BODY --check-schema`,
then `create BODY`). Creating hosted requests is within lab authorization (`user_preferences.md`)
but **costs credits**: stay inside `credit_budget`, and bring up the XP dashboard for requests
over 16 episodes. Never create self-play requests (our policy on both teams). Stream as soon as
a request exists:

```bash
uv run python .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py \
  --xreq xreq_... --watch --out paintbot_pw_lab/episode_data/RUN
```

## 3. Diagnose

Follow [paintbot-pw-diagnose](../paintbot-pw-diagnose/SKILL.md) on the batch:

```bash
uv run python paintbot_pw_lab/tools/pw.py metrics paintbot_pw_lab/episode_data/RUN --json
uv run python paintbot_pw_lab/tools/pw.py flags   paintbot_pw_lab/episode_data/RUN --policy BASE --json
uv run python paintbot_pw_lab/tools/pw.py fights  paintbot_pw_lab/episode_data/RUN --json
uv run python paintbot_pw_lab/tools/pw.py report  <the 3 worst losses from flags result.losses> --json
```

`result.losses[]` rows carry `episode_id`, not a path: find each directory with
`grep -l '"id": "<episode_id>"' paintbot_pw_lab/episode_data/RUN/*/episode.json` (fetcher
directories are named `<time>_<first 16 characters of the id>`).

- `counts.failed` above 10% of episodes, or a VM error / `vm_disabled_suspect` on our seats →
  that is an ops problem, not gameplay: fix it first (it is always inside the charter).
- With ≥ 8 episodes and no specific suspect, run the miner (`pw.py miner ... --json`, then
  `pw.py mine ...`; with fewer than 8 rows `miner` sets `result.warning` and `mine` fails).
- Write at most three hypotheses, each a mechanism pinned to a module of `policy_file`, with the
  predicted change in the primary metric (score_outcome score) and per-group effects.

## 4. Choose one change

Pick the hypothesis with the best evidence per unit of change. **If it falls outside
`allowed_changes`, stop and propose it to the orchestrator and wait for PROCEED** with its evidence — that is a new strategic
direction, which the human sets. Otherwise make exactly one attributable change to
`policy_file` or an authored skill (tunable numbers go in source Params; mark authored skill constants `' @tune name min max step` so
[paintbot-pw-tune](../paintbot-pw-tune/SKILL.md) can search them later).

## 5. Compile committed strategy source

Every policy edit is in `strategy/STRATEGY.md` or an authored `skills/*/skill.bas`.
Never hand-edit any other BASIC file. Run the documentation audit, commit those inputs,
then compile (use `--from BUILD_ID` to pin the accepted baseline for reuse):

```bash
uv run python paintbot_pw_lab/tools/pw.py strategy compile --agent codex --json
```

Read the immutable build report and G1–G5. Use normal behavior-change compilation, not
`--milestone m1` (reserved for baseline reproduction). G4 checks runtime health; local scores
are not a performance signal and must never veto, park, drop or rank a candidate. Local runs
may check bad seats, activation and mechanisms only. Every candidate that compiles and runs
cleanly proceeds to hosted A/B against real opponents, mostly the current target. Diagnose
compile/runtime failures; after repeated tool failure report to the orchestrator.
Include activation tracing in the source for every new or re-gated behavior.

## 6. Upload (enters no league)

Confirm James Botts is active with `uv run coworld player list`, then:

```bash
uv run coworld upload-policy --file paintbot_pw_lab/strategy/compiled/BUILD_ID/policy.bas --name POLICY_NAME
```

Record the returned version identity, build id and policy hash in
`strategy/compiled/uploads.jsonl`. Never upload a failed build.

## 7. A/B against the field

Follow [paintbot-pw-ab](../paintbot-pw-ab/SKILL.md) with `--design paired` (default) against the
charter opponents, seeds via `--seeds`, both sides. Create, stream, and check the stop rule as
episodes arrive:

```bash
uv run python paintbot_pw_lab/tools/pw.py compare sprt    paintbot_pw_lab/episode_data/RUN --design paired \
  --baseline BASE:vN --candidate CAND:vM --target score_outcome --margin-scale 600 --h0 0 --h1 0.10 --json          # result.decision: accept_h1 | accept_h0 | continue
uv run python paintbot_pw_lab/tools/pw.py compare compare paintbot_pw_lab/episode_data/RUN --design paired \
  --baseline BASE:vN --candidate CAND:vM --requests RUN/requests/manifest.json --target score_outcome --margin-scale 600 --json   # the final comparison
```

Recheck the live ranking margin before comparison. Hosted per-pair SD was about 0.6;
pre-register H1 around +0.08–0.10 and a fixed credit ceiling. This is a design assumption,
not a predicted measured gain. Track spend from request previews in the run ledger: the
ordinary player session receives 403 from the credit endpoint. Budget 0.5 credits/episode.

## 8. Decide and record

| SPRT decision (`compare sprt` → `result.decision`; `compare compare` → `result.sprt.decision`) | Action |
| --- | --- |
| `accept_h1` (candidate better on score_outcome) | the candidate becomes the charter `baseline` in `WORKING_CONTEXT.md`; note the evidence (request ids, estimate, CI) |
| `accept_h0` or a significant regression | keep the baseline; record the refuted hypothesis in `TENTATIVE_LESSONS.md` as a current constraint only if the evidence supports one |
| `continue` at the iteration's credit budget | inconclusive: keep the baseline, record the estimate, and do not claim equality |

Replace superseded context in place (lab doc rules); keep request bodies and ids with the result.

## 9. Stop rules and human gates

Stop the loop and report to the orchestrator and wait for PROCEED when any of these happens:

- `max_iterations` reached, or the daily `credit_budget` would be exceeded;
- two consecutive iterations end `accept_h0` or inconclusive;
- a preflight finds changed rule-bearing engine files;
- a proposed change is outside `allowed_changes`;
- a tool keeps failing after its `next` fix.

Never do these without James's explicit go-ahead, whatever the charter says: **league
submission** (`coworld-policy-lifecycle`), **public forum/wiki writes**, git push/PR, or spending
beyond the credit budget. At a stop boundary, write a short report (what changed, the evidence,
the current baseline, the next proposal) and wait for the orchestrator's PROCEED.

Under the optimizer brief, all stop rules mean write `QUESTION.md`, print
`NEED ORCHESTRATOR`, and wait for PROCEED. Task 0 ends with `REPORT-0.md` and
`TASK 0 DONE`; wait before iteration 1. Later iterations write `REPORT-<n>.md`, print
`ITERATION <n> DONE`, and continue unless a decision is needed. Keep `STATUS.md` current.
Never submit to leagues, write public community content, or push Git from this optimizer.

## Scheduling

To run unattended, schedule this skill with `/loop` (self-paced) or a cron routine pointed at the
repo root with the prompt "Run the paintbot-pw-loop skill for one iteration." Hosted batches take
minutes to hours: while a request streams, the loop should wait on the streaming process (or
reschedule itself) rather than poll the API.
