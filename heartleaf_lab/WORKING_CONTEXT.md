# Heartleaf working context

**What this is.** The live, high-signal state of *what we're working on right now* in the
Heartleaf lab — the minimal cross-session facts to carry into the next session. Read it on
startup to resume; **update it as you learn** (keep it tight). This is *not* a log: the full
game reference lives in [`docs/heartleaf-gameplay.md`](docs/heartleaf-gameplay.md); this file
is the one-screen "where are we and why."

> Read order for a newcomer: this file → [`README.md`](README.md) →
> [`docs/heartleaf-gameplay.md`](docs/heartleaf-gameplay.md). And the lab-wide
> [`../AGENTS.md`](../AGENTS.md) for the operating model.

---

## Status (2026-07-06, session 1): lab created AND cady v1 built — not yet uploaded

This session created the Heartleaf sub-lab (orientation docs, `docs/heartleaf-gameplay.md`,
lessons infra) **and built the first player, `cady` v1**, end to end from a design
(`docs/designs/cady-player-design.md`) + high-level plan (`docs/plans/2026-07-06-cady-player.md`).
cady is a deterministic cyborg Player-SDK policy on the **SDK's new SpriteV1 bridge**
(`run_sprite_bridge`; the pinned SDK was bumped `6dcd022→e8921a6` to get it — shared with
crewborg, whose 636 tests still pass). Built in 6 phases: Phase 1 (pin bump + scaffold) by
Claude; Phases 2–6 (capture probe, perception+types, action, modes+strategy+runtime+decide,
entry+packaging) delegated to **Codex** (plan→review→implement→verify→commit each). **31 tests
pass** (`uv run pytest heartleaf_lab/cady/tests`); `python -m cady` wires to the bridge.
Player index + summary: [`AGENTS.md`](AGENTS.md#player-policies).

**NOT yet done (the human-gated lab loop):** docker build, upload a version, first hosted eval.
See Open threads.

The game repo is cloned at **`~/coding/coworld-heartleaf`** (reference only — not part of
this repo). The game reference doc was distilled from that repo's `docs/`, `coworld_manifest.json`,
and the `talking_villager` player framework.

## Key facts established this session

- **Game shape:** 9-gnome Sprite-v1 gridworld; score = `hosted food × guests`; only hosts
  score; social coordination over chat is the meta-game. (Full detail in the gameplay doc.)
- **The big architectural fact:** the game ships a working `talking_villager` Nim engine
  (perception → pathfinding → 8-verb semantic actions → Bedrock LLM → chat); the 4 league
  players are that engine + different `soul.md` prompts. LLM call is mockable via
  `TALKING_VILLAGER_MOCK_REPLY`. → Cheapest player build paths are (a) new soul.md or
  (b) deterministic decision layer; (c) raw Sprite-v1 is the fallback. See AGENTS.md.
- **Repo status caveat:** `Metta-AI/coworld-heartleaf` is topic `coworld-incomplete` —
  `coworld certify` has NOT passed (README badge "verify: failed"). A live Observatory
  league is reported to exist, but **verify the game version + league state before relying
  on them.**
- **League variant config:** 9 compressed days (100s each), `maxTicks: 23760`, `num_agents: 9`.

## First eval done (2026-07-06): cady RUNS clean but is BLIND TO GARDENS — never gathers

`xreq_101eed6b`, 15 eps, cady vs 8 chatty-villagers on heartleaf 0.1.10. **Ops: 15/15 completed,
zero failures** — the SpriteV1 bridge + perception + entry point all work hosted (cady ran 762
decision ticks/game). **Score: cady 0/15** (field also near-0: 5/120 seats nonzero, max 13 — a
low-scoring env, likely villagers on the mock `keep_gathering_plants` reply).
**Root cause (from cady's telemetry artifact):** cady perceived **ZERO food gardens all game** →
strategy skipped Gather → went straight to **Host at tick 7 and `hold`ed with `held_mask=0`
forever** (never moved, never pressed A, never gathered → empty inventory → can't score). It DID
reach Host (not stuck Idle), so **camera/self resolve OK — it's GARDEN perception that's broken.**
Almost certainly the label/object-id mismatch we flagged: `perception.py` uses `"garden marker"`
/ base-4000 from the **0.1.0** clone, but the deployed game is **0.1.10**.

## cady v2 (2026-07-06): baked navigation — CODE-COMPLETE, not yet built/evaled

Fixes v1's zero-score cause (only gathered when a garden was *perceived*; never at spawn).
v2 navigates the FIXED baked map to known gardens. Shipped (46 tests pass):
- `mapdata/` — baked from `map.aseprite`+`map.resource`: 748×941 walk grid, 39 garden
  approach points, 9 house targets, a pre-computed circuit. `mapdata.py` loader + `bake_map.py`.
- `nav.py` — **hierarchical A*** router (`find_path`): coarse 4× grid for long hops (validated
  to preserve connectivity), fine A* for short + local wall-clip repair. **Arbitrary-point
  routing median ~3ms / max ~21ms, fully followable** (was 220ms full-grid A* — James's
  condition). NOTE: true JPS deferred — no-corner-cut JPS forced-neighbor rules are a known-hard
  variant; both Codex's and a hand-rolled JPS had reachability bugs; A* gives identical paths.
- `frame.py` (to_map/to_world via `WORLD_TO_MAP=(0,0)`), `navigator.py` (cached waypoint follower),
  `modes/gather.py` rewritten as a **circuit follower** (walk GARDEN_CIRCUIT → press A within 40px
  of each garden rect → advance), strategy Gather-before-cutoff, Host routes home via navigator.

**THE make-or-break caveat:** `WORLD_TO_MAP=(0,0)` assumes cady's perceived world frame == the
baked map-asset frame. If there's an offset, cady routes to the wrong pixels. The first v2 eval
(telemetry: does it move + harvest, inventory>0) confirms/sets it — it's the one calibration knob.

## Open threads (next steps)

1. **NEXT — fix garden perception vs 0.1.10 (the bug that zeroed cady).** Confirm the real
   0.1.10 garden vocabulary: run the capture probe against a live stream, OR decode a replay
   frame (we have `replay.json` per episode in the eval artifacts — raw BitWorld sprite bytes;
   the SDK `SpriteWorld.apply_frame` decodes them). Check the actual garden label + object-id
   base (and re-confirm gnome/clock while at it). Then fix `cady/perception.py`, rebuild, upload
   cady:v2, re-eval. This is the calibration step, now with a concrete target.
2. **Also verify** self/home geometry: cady `hold`s at its tick-1 home_anchor — confirm that's
   actually inside its house (else it can't host even with food). And the `SELF_OFFSET`(0,0)/seat.
3. **Heartleaf survey skill** — per-day host/guest/score report (AGENTS.md → Skills).
4. **v2 = coordination** — chat-based guest recruitment (the real scoring lever). Seam in place.

## Eval how-to (learned this session)
- Field: Competition div `div_396961a3…`, league `league_f831ba75…`; champion
  `heartleaf-fatherly-villager:v2`. Roster = 9 seats (cady + 8 random). **No -100 here** — detect
  failures via episode status/`failed_policy_index`, NOT score≤0 (see gameplay doc §Results).
- cady's traces go to the **policy-artifact zip** (jsonl@artifact), not stderr; fetch via
  `/jobs/{job}/policy-artifact/{seat}` with header `X-Use-Elevated-Privileges: true`. Its stderr
  policy-log is nearly empty. Artifact events: perception/belief/strategy/action_intent/act_command
  per tick + mode_entered/exited (generic — no data values, so read intent/command strings).

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness gate.
**Propose-and-pause.** Change one component per iteration. Uploading is routine/ungated;
**league submission is the human's gate** (public, champion-making, hard to roll back).
