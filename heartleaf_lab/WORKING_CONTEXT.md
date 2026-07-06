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

## Status (2026-07-06, session 1): lab created — scaffolding only, no player yet

This session **created the Heartleaf sub-lab** from the crewrift/cue-n-woo template. What
exists now: the orientation docs (this file, `README.md`, `AGENTS.md`), the self-contained
game reference (`docs/heartleaf-gameplay.md`), the lessons-lifecycle infra (`tools/` hooks +
`/lessons-review` skill, registered in root `.claude/settings.json`), and a near-empty
`best_practices.md`. **No player policy has been built, uploaded, or submitted.**

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

1. **NEXT (human direction, loop step 3): pick a build path** — (a) soul.md, (b)
   deterministic layer, or (c) raw Sprite-v1 — and stand up the first policy under
   `heartleaf_lab/<policy>/`. Do **not** pre-commit; surface the fork. Propose-and-pause.
2. **Verify the league exists and get its id / game version** (the task premise; not yet
   confirmed via the Observatory API this session). Needed before the first experience
   request.
3. **Confirm how a non-Nim / custom player uploads** against this game (the manifest's
   player `run` is `/bin/<name>` — check the players-SDK/build path for a Python or forked
   image, mirroring how crewrift/cue-n-woo handle it via `../player-build.md`).
4. **First eval + a Heartleaf survey skill** — once a policy is uploaded, run an experience
   request against the bundled field and build the per-day host/guest/score report
   (AGENTS.md → Skills).

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness gate.
**Propose-and-pause.** Change one component per iteration. Uploading is routine/ungated;
**league submission is the human's gate** (public, champion-making, hard to roll back).
