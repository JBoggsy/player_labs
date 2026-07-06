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

## Open threads (next steps — human-directed)

1. **NEXT: build cady's image + upload a version.** `heartleaf_lab/cady/Dockerfile` is written
   (context = `heartleaf_lab/cady/`, `--platform=linux/amd64`) but **not yet built** — do a
   `docker build` sanity check, then upload via the `build-and-upload` / `player-build.md` flow.
   Confirm the Python-image upload path works for this game (manifest player `run` = `/bin/<name>`).
2. **Verify the league exists + its id / game version** via the Observatory API before the first
   experience request (still not confirmed).
3. **First hosted eval → CALIBRATE.** Run an experience request vs the bundled villager field,
   pull artifacts + logs, and use them to calibrate the deferred unknowns cady flagged as
   `# CALIBRATION`: the self-position offset (`perception.SELF_OFFSET`, currently (0,0) — cancels
   for relative nav but confirm), our **seat identity** (which `"gnome <i>"` is ours), and the
   garden/house **trigger geometry** (`action.GATHER_RANGE`). The capture probe
   (`python -m cady.tools.capture_scene`) is the tool for this once pointed at a real stream.
4. **Then a Heartleaf survey skill** — per-day host/guest/score report (AGENTS.md → Skills).
5. **v2 = coordination** — chat-based guest recruitment (the real scoring lever), the reserved
   next iteration. The `decide`/`Command` seam for chat is already in place.

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness gate.
**Propose-and-pause.** Change one component per iteration. Uploading is routine/ungated;
**league submission is the human's gate** (public, champion-making, hard to roll back).
