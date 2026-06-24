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
- **roster**: one list, **exactly one participant per seat** — each
  `{"player": <selector>, "slot": <int>}`. The selector is `policy_ref`
  (`"name:vN"` or a UUID — any runnable policy, yours or not), `top_n: N`
  (champion pool), or `random: true`.
- **seats**: per-participant `slot` — `-1` (the default) round-robins through the
  open seats each episode; `0..N-1` pins that seat. Pin yours + leave the rest at
  `-1` to hold your seat (and role) while the field rotates.
- **roles**: per-slot role overrides (`game_config_overrides`) — roles are fixed
  *by seat*, so pinned seat = pinned role. **Crewrift roles:**
  `game_config_overrides.slots` is an **array of objects**, one per slot, e.g.
  `{"slots": [{"role": "imposter"}, {"role": "crew"}, ...]}` (`role` ∈
  `{"crew","imposter"}`; supply the full array — it replaces the
  whole key). *Not* bare strings. `create` validates this against the live game schema
  before POSTing; full schema in
  [`crewrift-gameplay.md`](../../../crewrift_lab/docs/crewrift-gameplay.md).
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
   cd /path/to/player_labs   # the repo root
   # a policy name -> its version id(s)
   uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py \
     resolve --policy crewborg --version <N>
   # a division's ranked, active opponents (name + policy_version_id)
   uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py \
     resolve --division div_... --top 7
   ```

2. **Compose the body** per `references/api.md` (target × roster × roles × seats ×
   count — whatever answers the question), e.g. `/tmp/req.json`. `policy_ref`
   accepts the `name:vN` label and the target accepts a division/league name, so
   you often don't need to resolve UUIDs at all — `resolve` is mainly for ranking
   the field and confirming versions.

3. **Validate + create.** `--check-schema` validates keys against the live schema
   without posting; drop it to POST. The tool reads the request back (through
   replica lag) and prints the `xreq_…` + resolved summary:

   ```bash
   uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py \
     create /tmp/req.json --check-schema   # dry-run
   uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py \
     create /tmp/req.json                  # for real
   ```
   Verify it resolved as intended (episode_count; the first episodes' participants
   seat the policies/versions you pinned, with the expected champion spread).

4. **Monitor to completion**, then pull + analyze. "Created" ≠ "done":

   ```bash
   uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py \
     monitor xreq_...
   ```
   When every child episode is terminal, pull replays/results/logs with the
   **`coworld-episode-artifacts`** skill (`fetch_artifacts.py --xreq xreq_...`) and
   compute the stats the question needs (win rate + score mean/median/quartiles/std,
   broken down by player and role).

   **Live dashboard (one or more requests).** For a richer view than `monitor` —
   especially when running several requests at once (a sweep, a multi-role eval) —
   `scripts/xp_dashboard.py` serves a self-contained browser dashboard that fills in
   as completions roll in: completion progress + throughput/ETA, a win-rate
   leaderboard (overall / crew / imposter), a win-rate heatmap, and per-player
   score-distribution strips. It polls the API in the background and pulls each
   completed episode's per-seat `results.json` once; stats are attributed by seat
   (from `participants` + `game_config.slots`) and ops-filtered (connect/disconnect
   -timeout episodes dropped — watch the "ops-filtered" count, a big number means
   your effective n is far below `num_episodes`). Win coloring uses the authoritative
   per-seat win flag (a win is the +100 objective bonus, not score > 0).

   ```bash
   uv run python .claude/skills/coworld-experience-requests/scripts/xp_dashboard.py \
     xreq_... [xreq_... ...]            # then open http://localhost:8808
   # --port N or XP_DASH_PORT=N to override; serves immediately and back-fills.
   ```

## Notes

- Auth comes from `softmax login` (the tool uses `load_current_token`); run inside
  `uv run`. If something fails on `load_current_cogames_token`, it's an older tool.
- For a one-off request you'd rather hand-drive, the `coworld xp-request
  create|list|get|episodes` CLI hits the same routes; this script adds live-schema
  validation, the POST/readback race handling, ID resolution, and polling.
- This skill *creates*; the `coworld-episode-artifacts` skill *downloads* the
  episodes it produces. Two halves of the evaluate/measure loop.
