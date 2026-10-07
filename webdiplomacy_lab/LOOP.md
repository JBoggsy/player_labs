# Overnight self-play loop (runbook)

**Status: wound down on 2026-10-07** at James's request (crons deleted, `evolve.py` stopped
at generation 53). This runbook stays as the recipe for restarting an unattended loop.
The lessons it produced are in `best_practices.md`.

James's standing instruction (2026-10-06): drive the optimization loop autonomously,
overnight, without asking permission. Submit, upload and change league fillers at will.
When an agent stalls, start a new one from a different perspective. Ask for advice via
Discord or Asana only when truly blocked. A cron re-invokes the session about every 30
minutes with "follow LOOP.md". Each tick runs the checklist below and must leave
**something running** on the machine before it ends.

All commands run from the repo root `~/coding/personal_labs/personal_labs_webdip`. Use
`HOME=$SCRATCH/home` for every softmax/coworld CLI call (see AGENTS.md "Identity
hygiene").

## Always-on engine: evolutionary self-play

`tools/evolve.py` runs generation after generation unattended.
- Each generation, 6 SearchBot config genomes plus the Calhamer anchor play 12 games, every agent in every game.
- Fitness is power-adjusted score, averaged across the generations a genome survives (exponential moving average).
- The top 3 survive; the rest are refilled with mutants and crossovers.

State lives in `experiments/evolve_state.json` and the run resumes from it after a restart.
Each generation appends a line to `experiments/ledger.jsonl`, and `local_runs/evolve.log`
shows progress. Every tick checks that it is alive and restarts it if not:
`nohup uv run python webdiplomacy_lab/tools/evolve.py --image <tag> --games 12 --parallel 2 >
webdiplomacy_lab/local_runs/evolve.log 2>&1 & disown`. When a genome stays the top elite
for 3+ generations with fitness above +0.05, it is promoted. Promotion means: add it as a
named personality, re-validate it in the arena against the DumbBot field, upload it, and
submit it if it beats the champion.

## Tick checklist

1. **Health.**
   - `pgrep -fl "wd.py (tourney|arena)"` shows what is running.
   - `tail -3 webdiplomacy_lab/local_runs/*.log` shows recent output.
   - `docker ps | grep -c coworld-run-game` counts live games.
   - `df -h ~` checks disk. If it is above 90%, delete old `local_runs/*/g-*/replay` files, keeping results and logs.
   - Exceptions: `grep -l '"exception"' webdiplomacy_lab/local_runs/<run>/*/logs/*.log`
2. **Harvest finished work.**
   - `wd.py ratings <tourney dirs>` for the population.
   - `wd.py versus A B` for a two-arm A/B.
   - `wd.py metrics <dir> --slot 0` for an arena.
   - Append one JSON line per finished experiment to `experiments/ledger.jsonl` with these fields: `{date, run, question, image, agents, games, result, verdict}`.
3. **Promote.**
   - Promotion bar: the agent tops the population ratings with power-adjusted score at least 2 standard errors above the current league champion's personality, over at least 40 games.
   - Build its image (`--build-arg POLICY=<name>`), upload it (lineage `webdip-dumbbot` for the main line, or `webdip-<personality>` for others), then submit with `--auto-champion always`.
   - Run a 7-episode hosted check against the league's current fillers.
4. **Fillers.** Keep a diverse, named filler roster in the league (`POST
   /v2/leagues/{id}/filler-policies`, body `{"expected_filler_policies": [...current],
   "filler_policies": [{"policy_version_id": ..., "display_name": "<Personality>"}]}`).
   Fillers must be uploaded policy versions.
5. **Start the next experiment.** Never leave the machine idle.
   - Take the top item from the idea queue below, implement it (one change), and build a NEW image tag.
   - Launch a tourney or arena with `nohup ... &` + `disown`, logging to `local_runs/<run>.log`.
   - Running about 7–8 games in parallel in total is the safe limit for this machine.
6. **Commit** at each checkpoint (`git add -A webdiplomacy_lab && git commit`). Push when a
   meaningful milestone lands (allowed).
7. **Update** WORKING_CONTEXT.md (current champion, population leaderboard, queue state).

## Idea queue (top = next; edit freely, strike what's done)

0. When the leaguesim-blucher and leaguesim-machiavelli runs finish, submit the winner as the next
   `webdip-dumbbot` version if it beats the champion. Then run a **Kissinger league-sim**:
   `wd.py tourney --fixed kissinger --agents random,calhamer,machiavelli,bismarck,metternich,talleyrand,napoleon
   --games 24 --parallel 2 --image webdip-bot:v6c --out local_runs/leaguesim-kissinger`.
   Its level-1 opponent model was wrong against DumbBots (0.38) but matches a field of search
   bots.
1. Measure pop1 (all 7 personalities). Freeze the winner as `field/<name>_vN` and make it the new arena field.
2. Retreat and build search: choose builds and retreats by evaluating next-phase outcomes with fastadj.
3. Opponent model upgrade: sample opponents from the SEARCH policy (cheap now), not only DumbBot. This is the iterated best-response / self-play step.
4. Learned evaluation: regress final score on mid-game features from tourney logs; use it as the search's static evaluation.
5. Deeper lookahead with fastadj: a two-season rollout for all candidates, not just a re-rank.
6. New perspectives if stuck:
   - CFR-style regret matching over a few candidate order sets per power (an equilibrium bot, "Nash").
   - A "kingmaker" that targets the leader.
   - A coalition bot that never attacks the two weakest neighbours ("Talleyrand II").
   - An LLM-flavoured agent for press variants.

## Stuck protocol

If three consecutive experiments are null or negative on the same agent, stop tuning it.
Freeze it, write one line in `TENTATIVE_LESSONS.md`, and start a new agent from the
"new perspectives" list. If infrastructure blocks progress (rate limits, Docker), switch to
offline work (adjudicator speed, analysis tools, new agent code) and retry later.
