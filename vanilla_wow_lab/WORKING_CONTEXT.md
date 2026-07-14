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

## Status (2026-07-14, session 3): first hosted smoke PASSED-ish; league exists; partly UNBLOCKED

Session 3 ran `wowborg` v1's first hosted experience requests. What changed since session 2:

- **The Observatory league EXISTS now** (the session-2 "no scored league" claim below is
  stale): league **"Vanilla Wow"** (`league_d7bf3aea-…`), division **"Leveling Ladder"**
  (`div_fe784707-…`), commissioner `vanilla-wow-leveling-commissioner`, weekly rounds
  (`schedule_interval_minutes: 10080`), created 2026-07-12. **Not yet verified**: whether
  the ladder actually scores/retains rounds (the game repo README badge is still
  "coworld verify: not ready" as of the 2026-07-14 pull — the badge and the league's
  existence currently disagree; treat the league's scoring as unconfirmed).
- **Deployed game package is `vanilla_wow` v0.1.6** (session 2 said 0.1.4.post8). The live
  manifest (15 variants, game configs) is fetchable via `GET /v2/coworlds/cow_d4b20fe9-…`;
  trust it over the local checkout.
- **First smoke (xreq_23feebad-…, 4 episodes, `orc-fresh-start`, wowborg:v1 in all 5 seats):
  all 4 episodes completed, score 0.0 each** — the artifact runs hosted episodes end-to-end
  without crashing. Caveats: no per-agent policy logs were retained and no results artifact
  was available (replay only, a custom `CWREPLAY` binary format), so the intended success
  signal (`SMSG_LOGIN_VERIFY_WORLD` in WOWBORG logs + nonzero realmd/world audit bytes)
  **could not be confirmed**. Completion without failure is the only evidence so far.
- **Two operational hard lessons** (also in the lessons buffer): (1) wowborg v1 never
  self-terminates and ignores `deadline_seconds`, so every episode runs to the FULL variant
  deadline — `rfc-five-player-clear` is 10000/0.1 ≈ **27.8 h per episode**; a first attempt
  (xreq_5d4946c2-…) had to be cancelled via `POST /v2/experience-requests/{id}/cancel`
  (route exists; not in the skill docs). Use `orc-fresh-start` (max_ticks=100, ~17 min) or a
  `game_config_overrides` with small `max_ticks` for smokes. (2) Each episode boots an
  all-in-one VMaNGOS container on k8s first — budget ~5+ min infra overhead per episode.

**Next steps:** figure out why policy logs weren't retained (elevated fetch? platform gap?);
decode the `CWREPLAY` replay format to extract the login-success signal; make wowborg v2
honor `deadline_seconds`; verify whether the Leveling Ladder actually scores rounds before
calling the loop unblocked.

---

## Status (2026-07-13, session 2): `wowborg` v1 implemented; loop still BLOCKED

`vanilla_wow_lab` was created from the `heartleaf_lab` template, and the first Python policy
skeleton now exists. What exists:

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
- **`wowborg` v1**: a pure-Python policy under [`wowborg/`](wowborg/) that connects to the
  Coworld `/player` session, authenticates to realmd over `/tcp/realmd`, opens `/tcp/world`,
  logs the seeded `character_name` into mangosd through `SMSG_LOGIN_VERIFY_WORLD`, sends the
  worldport ACK / active mover packets, then idles with periodic `CMSG_PING`. It does not decode
  world state or play yet. Focused validation: `uv run pytest vanilla_wow_lab/wowborg/tests -q`
  passes (14 tests).

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

So uploading `wowborg` may produce a runnable score-0 artifact, but there is still nothing live
to compete in yet, and an experience request may have no scored field to run against. **Do not**
treat this like the crewrift/heartleaf loop until the game is live.

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
2. **If live:** build/upload `wowborg` and run the first hosted integration eval. Expected score
   is 0; success is `SMSG_LOGIN_VERIFY_WORLD` in `WOWBORG` logs plus nonzero `/tcp/realmd` and
   `/tcp/world` audit bytes.
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
