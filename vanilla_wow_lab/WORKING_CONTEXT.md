# Vanilla WoW working context

**What this is.** The live, high-signal state of *what we're working on right now* in the
Vanilla WoW lab — the minimal cross-session facts to carry into the next session. Read it on
startup to resume; **update it as you learn** (keep it tight). This is *not* a log: the full
game reference lives in [`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md); this
file is the one-screen "where are we and why."

> Read order for a newcomer: this file → [`README.md`](README.md) →
> [`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md) →
> [`docs/vanilla-wow-player-contract.md`](docs/vanilla-wow-player-contract.md). And the
> lab-wide [`../AGENTS.md`](../AGENTS.md) for the operating model.

---

## Status (2026-07-13, session 1): lab created — docs + scaffolding only, loop BLOCKED

`vanilla_wow_lab` was created this session from the `heartleaf_lab` template (which itself was
a scaffolding-only new lab). What exists:

- **Five docs**, from a deep read of the game repo + web research (with citations):
  [`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md) (the game, accessibly),
  [`docs/vanilla-wow-player-contract.md`](docs/vanilla-wow-player-contract.md) (the Nim wire
  contract, narrative), [`docs/vanilla-wow-protocol.md`](docs/vanilla-wow-protocol.md) (the
  **exhaustive** interface-protocol reference — every message/schema/binary format, field-level),
  [`docs/vanilla-wow-rfc-roles.md`](docs/vanilla-wow-rfc-roles.md) (the 5 RFC roles + round
  scoring), and [`docs/vanilla-wow-strategy-guide.md`](docs/vanilla-wow-strategy-guide.md)
  (how to *play* WoW well: beginner's guide + leveling/group/RFC strategy + pro tips, blending
  cited real-Vanilla-WoW knowledge with engine-grounded facts).
- **Standard lab scaffolding**: README, AGENTS, near-empty best_practices, this file, the
  lessons buffer + hooks (`tools/rotate_lessons.sh`, `tools/lessons_stop_nudge.sh`, registered
  in the root `.claude/settings.json`), and the `/lessons-review` skill.
- **No player policy.** No `vanilla_wow_lab/<policy>/` dir, no Nim build path, no `versions.env`
  yet — those come when a first policy is chosen (a human-direction call; see build paths in
  [`AGENTS.md`](AGENTS.md#player-build-paths)).

**The loop is BLOCKED** and cannot run yet — this is the single most important fact:

- The game package is **`vanilla_wow:0.1.4.post8`** (policy id `cow_0466d25f-…`, built from
  pinned Coworld commit `754ff27c…`). It **passed all ten executable certification steps** and
  a local isolated-RFC snapshot smoke (176 live RFC frames, clean all-left, no identity leak),
  **but** the README badge is **"coworld verify: not ready"**.
- The badge is gated on **one retained hosted commissioner round + one retained XP-request
  episode on Kubernetes** proving snapshot import / results / replay upload+load — **neither
  has been authorized or created** (`docs/coworld-readiness.md`).
- There is a **live persistent *practice* realm** (Tailscale), but its runs are unscored
  (`scope=persistent_realm_session`). There is **no live scored Observatory league** for this
  game, and the persistent-tournament commissioner / account-mapping / hosted leaderboard are
  **designed but not implemented** (`docs/persistent-tournament.md:273-284`).

So uploading a policy has nothing to compete in yet, and an experience request has no live
field to run against. **Do not** treat this like the crewrift/heartleaf loop until the game is
live.

## Key facts (the hard-won ones — full detail in the docs)

- **Two game shapes** (docs/vanilla-wow-gameplay.md "Two game shapes"): a **persistent realm**
  (ranked by an account's highest-XP character, `highest_character_total_xp`) and **isolated
  scored episodes** (disposable servers from a signed `CWROSTER` 5-character snapshot; nothing
  writes back). Keep them distinct.
- **The scored benchmark is `rfc-five-player-clear`**: one policy fills **all five slots**
  (`self_play=True`), a level-30 Horde party (warrior tank / priest healer / shaman / rogue /
  mage) clears Ragefire Chasm (map 389), four bosses (Oggleflint 11517, Taragaman 11520,
  Jergosh 11518, Bazzalan 11519).
- **Round score = clear-then-speed:** full clear → `max(1.0, 1_000_000 − clear_seconds)`;
  partial → `bosses_defeated / bosses_total` (< 1.0). Every clear beats every partial; among
  clears, fastest wins. **Cross the full-clear threshold before optimizing time.**
- **7200 is NOT the episode deadline** — it's `DUNGEON_LAB_RESPAWN_SECONDS`, the boss-respawn
  timer that keeps a killed boss readable as dead. The episode budget is `max_ticks/tick_rate`
  (RFC: 10000/0.1). Be precise when writing about time.
- **The player is Nim, packet-level** (King Nimrod, headless `-d:noGui`), connects via a
  WebSocket→TCP bridge (`wsproxy`), and must obey **"sent is not accepted"** (confirm every
  action from `action-results.jsonl` / typed state transition; no teleport / injection /
  synthetic state / DB repair after login).
- **Only 7 of 9 classes are seedable** (Horde-only seeding; **paladin** Alliance-unreachable,
  **druid** unseeded). Class rotations exist for those same 7 (`player/bots/rotations.nim`).
- **No `-100` failure sentinel** (that's Crewrift). Detect player failure via episode status;
  read a low completed-episode score as a gameplay signal.

## Open threads (next steps — all human-gated)

1. **Verify the game's live state** before anything else: has a scored league / XP-request path
   opened since 2026-07-13? Is `vanilla_wow` submittable to a real competition yet? This
   determines whether the loop can even start. (`git -C ~/coding/coworlds/coworld-vanilla-wow
   pull` and re-read `docs/coworld-readiness.md` + the README badge.)
2. **If live:** pick a build path (AGENTS.md#player-build-paths) — human-direction call — and
   vendor the first policy under `vanilla_wow_lab/<policy>/` with a Nim build path.
3. **Tooling gap:** a Vanilla-WoW survey/report skill (on the reporter's recap/events/stats +
   diagnoser findings) is the top investment once real episodes exist — analogous to
   `crewrift-survey`.

## Reference

- Game repo (reference only): `~/coding/coworlds/coworld-vanilla-wow` — Python adapter
  `src/vanilla_wow_coworld/`, Nim player `player/`, dungeons `dungeons/`, manifest
  `coworld_manifest_template.json`. **Read-only for us; pull before relying on it.**
- Design doc for this lab's creation: `../docs/superpowers/specs/2026-07-13-vanilla-wow-lab-design.md`.

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness gate.
**Propose-and-pause.** Change one component per iteration. Uploading is routine/ungated;
**league submission is the human's gate** (public, champion-making, hard to roll back) — and
here, doubly gated behind the game even being live.
