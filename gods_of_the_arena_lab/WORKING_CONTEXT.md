# gods_of_the_arena_lab working context

Use the current user request to establish the objective, scope and next decision.
Resolve the active game configuration, policy identity and roster through the platform
before evaluating or changing live participation. Source code and current API responses
define behavior; this file must not substitute for a live-state query.

Maintain only the active objective, unresolved constraints and next action here.
Replace completed or superseded context in place.

## Objective

Current direction (James, 2026-09-17): improve with Claude via `agent-collab`.
Win while earning strictly more XP than every teammate. Track that joint outcome,
team win rate, team XP rank/margin, and XP per 1,000 ticks separately. Farm until
teammates initiate fights, take finishing kills, and return to farm; rely on teammates
to end the match. No solo aggression or pushing. Further league submission, commits
and pushes require James's explicit permission. This direction supersedes the older
farm-only objective and proposed pushing/dueling increments below.

**PAUSED by James, 2026-09-18.** Review findings only. No further gameplay changes,
uploads, evaluations, commits, pushes or league submissions without fresh direction.
No accepted gameplay improvement in this campaign; v13 remains the accepted baseline.
Local modules and diagnostic v20 (`6f3fce4b-1199-4982-a791-7e9e93561bab`) contain
v13 gameplay plus sparse KT traces (`cfgKsTrace=1`),252globals/32arrays. No new
league submission was made. Rejected retreat-cast code and lane-follow code are removed.

The16-game diagnostic request `xreq_1c2f1807-8f6a-4afa-9dfa-6b3683f5e6c0` is
complete: all16replaysverified, no VMerrors, no operationalfailures. Records in
`tmp/collab/xp-team/trace/`. Do not repeat it. Completed dashboard:localhost8817.

v18 lane-follow was rejected: XP/1,000 ticks fell 168.24 to 112.78 and farm 5.50 to
3.56 in 48 games per arm; its code is removed. v19 cast-and-retreat's exploratory
XP gain (169.02 to 188.57, 48/arm) did not replicate in fresh96/arm: 171.99 to163.72,
kills1.98 to1.77, deaths2.06 to2.26; joint win/strictXPlead0/96 both. Differences
are inconclusive, not proof of equality or harm; there is no adoption evidence.
All192confirmation replays verified. One v13 Lich hit the BASIC instruction limit;
this subject remains in the comparison. No v19 VM errors or operational failures.

Evidence: `tmp/collab/xp-team/cast-confirm/summary.json` and `comparison.md`;
exploratory results in `cast/`, rejected lane rule in `repair/`. Requests completed:
baseline `xreq_91cee40e-2001-49de-99d4-14203b172341`, candidate
`xreq_a68adf17-db43-4d11-96f5-bcfa119e64db`. Do not duplicate them.
Dashboard http://localhost:8817 shows request progress; its score parser does not
accept these game results. Exact replay metrics now join into compare/miner tools.

Review: `tmp/collab/xp-team/FINDINGS.md` is the root-reviewed summary;
`trace/trace-rows.json` is the raw trace evidence. Claude's TRACE-VERDICT counts and
conversion claims are exploratory and not reconciled; see the summary's limits. Raw1891KTrows are not independent failedfinishers: priority
overrides dominate. There were60openings without retreat/punish override,58basic
and2spell; at least35basic used approach calculation. Equalhorizon cases do not prove
in-range status. This suggests inspecting approach timing if James resumes; it does
not prove zerochase or any forecasting rule improves the objective. Spell identity
cannot be inferred from drop size. The earlier horizon-shrink explanation was withdrawn.
Claude tmux `claude-gota-xp` completed the read-only review and is standing down.
Across v19 exploration and confirmation, each arm achieved only1jointwin/strict
teamXPlead in144games. Closing the gap to the leading teammate remains unsolved.

Make the James Botts policy (`ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce`, the account
default) take as many footman last hits as possible, as a module a larger policy can wrap.
Uploaded versions (2026-09-17): `james-botts-gota:v1` (`91f92e55-1146-43b0-b324-8c2e2bf62d6c`,
first working build), `v2` (hero-threat retreat, safe lane front), `v3` (ally-avoid rule off,
idle-at-standoff for Vanguard Knight, Druid Warden, Death Knight, Warlock), `v4` (the current
`policy/dist/james_botts.bas`: v3 plus a footman's hit history reset after any sighting gap).
Same-window A/B v3 `xreq_6aeb6c4a-75ce-4fed-a3c8-d89478d39942` versus v4
`xreq_409c5c64-579a-47ab-8eb9-bcbf80f03286` (16 episodes each): 4.40 versus 4.54 last hits per
hero per 1,000 ticks, inconclusive; v3's rate reproduced its earlier batch exactly. Source and module contract in
[policy/README.md](policy/README.md), design in
[docs/designs/2026-09-17-lasthit-policy.md](docs/designs/2026-09-17-lasthit-policy.md).
Local mirror matches (the policy in all ten seats) take about 1,000 of the 1,080 enemy
footmen per team per match; hosted measurements (five candidate seats plus five random champions, seats rotated by
the platform so allies are other entrants' policies): v1 `xreq_97d3e4db-8edb-4477-9e9e-9eaf2e8febb1`
(8 episodes: 3.9 last hits per hero per 1,000 ticks, 3.45 deaths per hero-match), v2
`xreq_7e289d01-71c1-4ecf-a12b-9bca550c4030` and `xreq_04643879-e9d4-4d72-bad7-c37978dcffa9`
(16 episodes: 3.7 per 1,000 ticks, 1.40 deaths), v3 `xreq_4c820655-9c06-4a51-9568-506496f98a5c`
(16 episodes; result in policy/README.md). Games against the field last 4,000 to 15,000
ticks; every opponent policy out-earns ours in XP per 1,000 ticks because they take hero
and tower kills, which this module does not attempt. Codex collaborated through the local harness and a review
(`tools/lasthit_eval.py`; experiments in `policy/experiments/codex/`).

## Identity and environment

- James Botts is the account's default player (`uv run softmax player list` marks it),
  so uploads and experience requests made with the user credential (`uv run softmax status`
  shows `subject_type: user`) attribute to it; `james-botts-gota` v1 to v16 were uploaded
  this way on 2026-09-17. `softmax player use` selects another player when needed.
- The account's other player, Games Bond, owns the `games-bond-gota` policy; its private
  logs are not readable under the James Botts session.
- Deployed polyworld commit `f2ab9598` (coworld `cow_126f2fcb-80a0-4b6e-8166-eb6163576db5`,
  2026.9.16.5, seen 2026-09-17). The mechanics documents are verified at `7365e4e9`; the
  diff (`examples/gods_of_the_arena/`) adds `attackMove(x, y)` to BASIC (800 work units),
  two god-guard gate towers per god that must both fall before the god takes damage
  (exposed once any lane is cleared), footmen that path to the next enemy building after
  their lane waypoints, and barracks ids assigned by map order. Re-verification is in
  `TODO.md`. Run `tools/deployed_ref.py` at the start of a session.
- Local runs: `uv run coworld run-episode <manifest> <ten .bas paths> --variant competition`
  simulates a full match in about five seconds with per-seat PRINT logs; the harness
  `tools/lasthit_eval.py` wraps it. Seeds 2026 and 2028 produced identical games locally.
- The four rendered HTML reports under `../docs/reports/gota-*-2026-09-15.html` still carry
  the pre-`7365e4e9` prose (scaling's embedded figures are regenerated); the Markdown
  sources are current.

## Public discussion

- The hero-role proposal is public: `post_f177c436-fd32-4923-bac9-56595a5142f9` in the
  Gods of the Arena forum, posted as the James Botts player. A launchd job
  (`com.jamesboggs.forum-agent.gota`, every 30 minutes) runs the standing forum agent
  (`tools/forum_agent/`, brief in `forum_agent/brief.md`); it records what the thread
  produces in [docs/roles.md](docs/roles.md) and flags items for James in
  `forum_agent/state.json` under `attention`.

## Unresolved constraints

- Damage and heal attribution is not recoverable from replays; `damage` is a stub in the
  expander design until [requested change 14](docs/requested-game-changes.md) lands (still
  open on `main`).
- The burst-killer and siege rules can use `selfTarget`, `objectTarget`,
  `selfAttackCooldown`, and the spell list. The role model in [docs/roles.md](docs/roles.md)
  was re-checked against the Red buffs and the 480-tick wave cadence on 2026-09-16; no
  assignment changed, and barracks are a new, untested siege hypothesis there.
- Mono-team versus mixed-team rosters are a platform setting; confirm which the target
  league or experience request uses before reasoning about allies.
- All six public wiki pages were republished from `docs/wiki/` on 2026-09-16 (verified at
  `7365e4e9`). `game-guide`, `hero-statistics`, and `player-standings` are also written by
  Andre's Polyworld Buff sync job, which appends report tables; our write kept his header
  and appended sections, but his next sync may overwrite ours. Ownership of those three
  pages is not agreed with him yet.

## Where the policy stands against the field (2026-09-17)

Exact per-seat last hits from 72 re-simulated hosted replays (`tools/expand_replay.nim`,
hashes verified): our seats rank a mean 3.1 of 5 within their team by footman last hits
(19% share, top of team 19% of the time) and 11th of the 16 policies seen, at 4.3 last hits
per hero per 1,000 ticks; the unmodified starter gets 6.5 and the top farmers 6 to 7. The
policies above us attack continuously rather than waiting for kill windows. `v5`
(`james-botts-gota:v5`, every class idles at the standoff point and lets the engine attack)
beat `v4` in a same-window A/B (`xreq_33a01eeb-3812-4533-9d74-595a431a29b2` v4,
`xreq_197d8abc-3fec-492c-b195-35bff30df56b` v5, 32 episodes each): 4.88 versus 4.31 last hits per
hero per 1,000 ticks by exact replay counts, fewer deaths, rank within team unchanged at 3.1; the
other seats in those games average 5.3. Then, with ONE copy of our policy per game (James's rule for
all hosted requests from now on), the punish module (`25_punish.bas`, attack the enemy hero an
allied tower is firing at) was A/B'd as `v7` against `v5`: `xreq_54a88302-9ae8-4a2e-8d81-17998069d643`
(v5, 48 episodes) and `xreq_4aef8f5b-f98c-4859-98ab-36ffd9a8abfd` (v7, 48): last hits per 1,000
ticks 5.80 to 6.49, hero kills per match 0.20 to 1.04 (adapter verdict improved), deaths down,
rank within team 2.5 to 2.2 of 5, and the other seats average 4.5. `v7` is the best measured version. A background agent's time-budget analysis
([docs/designs/2026-09-17-time-budget-analysis.md](docs/designs/2026-09-17-time-budget-analysis.md))
found presence at parity with the field and conversion the deficit for melee and low-damage
classes; its `v8` (chase-attack for classes 0, 3, 4, 5, 8, 9, built on v5) measured 5.91 versus
5.82 with deaths down a third (`xreq_8cd07e44-239a-4f66-a7c3-6eb5b8b29f2b` v5,
`xreq_a25ad678-22d7-4af8-a5a6-e19422a3e332` v8). `v9` = v7 plus that change is what
`policy/modules` build now; `v10` adds farming beside enemy towers that are busy with footmen (or idle with two allied
footmen in reach) and a chase-cost rule for punish (keep chasing past tower cover only while
expected time to kill from the target's HP over our DPS plus an adjacent teammate's is at most
5 s, we are not slower unless already in range, and within 15 tiles). Three-arm same-window
A/B, one copy per game, 48 each: `xreq_dc1053fd-9f0e-4927-9d6c-bb8048a585f7` (v7),
`xreq_67ec3c24-de16-49d9-a334-5593c7d7d7f6` (v9), `xreq_bb87ef5d-765a-42ae-b544-95f38ac1b937`
(v10). Result: 5.97 / 6.28 / 6.04 last hits per hero per 1,000 ticks (other seats 4.5), rank 2.2 / 2.2 /
2.4, hero kills 0.94 / 1.10 / 0.79 per match, deaths per 1,000 ticks 0.35 / 0.30 / 0.27; all inside
noise. `v9` stays the best build; v10's two additions are in the modules behind knobs, off.

## Analysis instruments

The replay expander (`tools/expand_replay.nim`, built by `tools/build_expand_replay.sh` at
the deployed commit into `tools/bin/`) re-simulates a replay, verifies every tick hash, and
writes per-seat exact last hits, kills, building kills, deaths and levels for all ten seats.
Codex is completing it to the full contract in [docs/replay-format.md](docs/replay-format.md)
section 4 (actions, casts, items, buildings, `replay_stats.py`, `viz_replay.py`).

Hosted batches are scored with the lab adapters in `tools/`: `compare.py` (coworld-ab: one
observation per episode per group, `--target last_hits_per_1k_ticks`), `miner_rows.py` plus
`features.py` (coworld-hypothesis-miner), and `gota_episodes.py` (reader for downloaded
episodes, our seats' `LH` telemetry). The v3 miner pass flagged unspent gold (the best-farming
seats end with about 380 gold): `shBuy` stops buying gear once one inventory slot is left, so
income stops converting into damage. A candidate for the next single-change experiment.

## Next decision

James's direction (2026-09-17): maximize XP; no solo aggression; join teammates' fights to
take the kill; return to farm. The kill-steal module (`22_ksteal.bas`) shipped as `v13` and
beat `v12` in a one-copy A/B (`xreq_2059453c-116c-4de3-b0c1-31e6ee981e70` v12,
`xreq_c5645f5f-564f-40d9-a152-9e88d8039b3e` v13, 48 each): XP per 1,000 ticks 146 to 183, hero
kills per match 0.62 to 2.48, share of nearby enemy deaths taken 8% to 30%, deaths 2.67 to
1.90, level lead -1.1 to -0.1, farm 5.6 to 6.2. `v13` is the current build and was **submitted to the league on James's instruction**
(2026-09-17): submission `sub_38be3038-d8d1-4275-91da-557ee52ba109`, policy version
`40d72eea-ac61-44b0-aaf4-7828fbf30170`, auto-champion on; qualification and standings via
`policy_lifecycle.py monitor --name james-botts-gota`. League standing after placement: rank 11, score 1500, 0 rounds. `v14` (walk in for structure
finishing hits) changed nothing: the window never opened. `v15` (approach engaged enemy heroes up to 12 tiles) was rejected: hero kills 2.65 to 1.58 and
deaths 1.73 to 2.42 (`xreq_f7fccb7e-3bee-4bd7-8328-467a64d94035` v13, `xreq_debac4d4-d918-4308-b986-934202ee3c04`
v15). The structure stand-ready rule never fired in 48 games and stays gated. `v16` (area and
ring ultimates on still targets) was rejected: casts 16 to 44 but hero kills 2.10 to 1.54, XP
159 to 161 (`xreq_395ccc99-19e2-48af-9716-acd8750b4fe6` v13, `xreq_dd2f2d2d-42e1-4fa2-a704-1727f15d6c72`
v16); the delayed casts land after the kill or miss, and pre-empt the basic hit. Off by knob
(`cfgKsAreaSpells`). `v13` remains the best measured version and the league entry; the modules
build its behavior plus two inert gated rules. Note the v13 baseline arm itself varies between
runs (XP 159 to 172, hero kills 1.7 to 2.65 per match), so 48-game arms resolve only large effects. Next candidates after that: the
ultimates left out of the strike table (ring, line and capsule footprints), the hold-spells radius,
and joining teammates' pushes across the river. Further submissions stay gated on James.
