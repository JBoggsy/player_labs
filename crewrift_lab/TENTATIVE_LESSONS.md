# Crewrift tentative lessons — session buffer

**Session started:** 2026-07-21 13:01. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`crewrift_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Crewrift-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### fetch_artifacts.py `--round` is NOT repeatable — only the last one wins
Evidence: passed ten `--round` flags in one invocation; got exactly 20 episodes (one round). Looped per-round invocations into the same `--out` dir instead (incremental, safe). Note build_warehouse.py's `--round` IS repeatable — the two scripts differ.

### tools/bin expand_replay binaries embed a build-time absolute path that broke when the repo moved
Evidence: all `tools/bin/expand_replay-*` die with `No such file or directory: …/personal_labs/crewrift_lab/.cache/crewrift-src/<ref>` — the repo now lives at `personal_labs/personal_labs_crewrift/`. Fixed with `ln -sfn …/personal_labs_crewrift/crewrift_lab …/personal_labs/crewrift_lab`. Durable fix: rebuild the binaries.

### expand_replay-34a97a3 is still the correct expander for live league replays (crewrift 0.4.68, 2026-07-21)
Evidence: 182/199 trace-complete on the latest 10 rounds; `expand_replay-d9f6b30` (versions.env's CREWRIFT_REF) hash-fails on the same replays. versions.env is the *player-build* pin, not the replay-expander pin.

### survey.py `--reasons` keys must be the exact episode DIR names, not full ereq ids
Evidence: first reasons.json keyed by full `ereq_…` id produced sidecar `reason` count 0, silently — no warning. Keys are the truncated dirs like `20260721T193356_ereq_94c9f0fc-1b`.

### Bedrock throttling persists in LIVE league rounds — the LLM layer fires ~38%
Evidence: crewborg league telemetry over 58 episodes: 154 `meeting_llm_decision` vs 248 `meeting_llm_fallback`, 236 "Too many tokens" throttle lines, 40 `meeting_llm_budget_exhausted`. The social rework is still mostly untested in production, matching the A/B story.

### ROOT CAUSE of self-suss (and likely the whole v107 slump): the slot→color seed table is STALE — the deployed game renamed its 16 colors
Evidence: crewborg's `PLAYER_COLOR_NAMES` (perception/constants.py:86, "palette order (global.nim PlayerColorNames)") = red, orange, yellow, light blue, pink, lime, blue, pale blue… — matches crewrift `d9f6b30`/`42fed21` (0.1.x). The DEPLOYED game (34a97a3 / 0.4.68, sim.nim:145) uses red, blue, green, pink, orange, yellow, purple, cyan…. The `?slot=` seed (policy_player.py:384) is marked `self_color_from_marker=True` (authoritative, never corrected), so 6/8 seats latch a WRONG self color for the whole game: slot 1 believes "orange" while actually blue, slot 4 believes "pink" while actually orange, etc. Every downstream self-exclusion (kill pool, suspicion, top_suspect, accusation, census self-death) then guards the wrong color. Telemetry confirms: 12/58 episodes have crewborg's ACTUAL color inside its own `teammate_colors` (reveal ingest failed to drop self), and the self-accusation episodes are exactly the seats whose actual color ("orange", "green") differs from the seeded one ("pink", "yellow"). Only slot 0 (red) is accidentally correct. Fix: sync PLAYER_COLOR_NAMES with the deployed game's table (and add a runtime cross-check marker-vs-seed).

### v107 league weakness decomposes into three mechanistic signals in one warehouse pass
Evidence: (1) imposter ejected 9/17 = 53% (field median ~31%) with kills/seat 1.29 and isolated-kill conversion 19% vs 34-50% for the top; (2) crew votes-received/seat 1.37 (2nd-worst) with 6/41 crew ejections; (3) SMOKING GUN: crewborg chat literally accuses its own color — 5 messages across 2 episodes of "orange sus: … vote orange" / "green sus … vote green" (self-suss in the accusation template while `fabricate/report` pipeline picks self as target). Also opponents' detectors ("X was tailing me") fire on crewborg's tail-heavy movement in BOTH roles.
