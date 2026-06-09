---
name: coworld-experience-requests
description: "Use to create and monitor Coworld experience requests — hosted batches of episodes you define (target, roster, roles, count) for evaluating agents against a live roster. Triggers: 'run <policy> vs the top opponents', 'make an experience request', 'request N hosted games', 'A/B a policy against the league', 'set up an evaluation battery / matchup'. Game-agnostic; pair with coworld-episode-artifacts to pull the resulting episodes."
---

# Coworld Experience Requests

Create hosted batches of Coworld episodes to measure how agents perform: define a
**target** (game / league / division), a **roster** (which policies, in which seats
and roles), and a **count**; POST it; monitor the `xreq_…` to completion; then pull
the episodes with the `coworld-episode-artifacts` skill and analyze. Game-agnostic:
only the per-slot **role** overrides are game-specific.

**Announce at start:** "Setting up a Coworld experience request. I'll resolve the
live IDs, compose the request to the question, POST it, and monitor to completion."

## The model (compose the body; the tool does the mechanics)

The request body (`V2CreateExperienceRequestRequest`) is where the experiment
lives — and the API now does a lot for you, so prefer its built-ins:

- **target**: a division/league (resolves its Coworld) or a direct `coworld_id`.
- **roster**: your `requester` + named/auto opponents (`top_n` champions), or a
  fully caller-owned `policy_version_ids` roster.
- **roles & seats**: per-slot role overrides (`game_config_overrides`) and seat
  round-robin (`rotate_seats`) — no post-hoc balancing.
- **count**: `num_episodes`, high enough to smooth variance.

You compose that body to the question; the script handles the mechanical parts —
auth, validating keys against the **live** schema (`additionalProperties: false`,
so no stray keys), the POST + readback race, polling, and ID resolution. **Every
field, with the rules and worked examples, is in [`references/api.md`](references/api.md)** —
read it before composing a body, and re-check the live schema when a route 4xxs
(the API drifts).

## Workflow

1. **Resolve live IDs — never reuse cached ones** (they rotate). Get the current
   coworld/league/division and the active memberships you'll draw opponents from
   (`coworld leagues|divisions|results|memberships --json`, or the helper):

   ```bash
   cd ~/coding/player_labs
   # a policy name -> its version id(s)
   uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py \
     resolve --policy crewborg --version 15
   # a division's ranked, active opponents (name + policy_version_id)
   uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py \
     resolve --division div_... --top 7
   ```

2. **Compose the body** per `references/api.md` (target × roster × roles × seats ×
   count — whatever answers the question), e.g. `/tmp/req.json`. Opponents and the
   requester accept `player_name`, and the target accepts a division/league name,
   so you often don't need to resolve every id by hand.

3. **Validate + create.** `--check-schema` validates keys against the live schema
   without posting; drop it to POST. The tool reads the request back (through
   replica lag) and prints the `xreq_…` + resolved summary:

   ```bash
   uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py \
     create /tmp/req.json --check-schema   # dry-run
   uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py \
     create /tmp/req.json                  # for real
   ```
   Verify it resolved as intended (episode_count, slot 0 = requester, opponents).

4. **Monitor to completion**, then pull + analyze. "Created" ≠ "done":

   ```bash
   uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py \
     monitor xreq_...
   ```
   When every child episode is terminal, pull replays/results/logs with the
   **`coworld-episode-artifacts`** skill (`fetch_artifacts.py --xreq xreq_...`) and
   compute the stats the question needs (win rate + score mean/median/quartiles/std,
   broken down by player and role).

## Notes

- Auth comes from `softmax login` (the tool uses `load_current_token`); run inside
  `uv run`. If something fails on `load_current_cogames_token`, it's an older tool.
- For a one-off request you'd rather hand-drive, the `coworld xp-request
  create|list|get|episodes` CLI hits the same routes; this script adds live-schema
  validation, the POST/readback race handling, ID resolution, and polling.
- This skill *creates*; the `coworld-episode-artifacts` skill *downloads* the
  episodes it produces. Two halves of the evaluate/measure loop.
