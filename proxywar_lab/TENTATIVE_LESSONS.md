# Proxywar tentative lessons — session buffer

**Session started:** 2026-08-11. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`proxywar_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Proxywar-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### "Proxywar" existed nowhere in this repo despite the clone being named for it
Evidence: grep over all files, commits, and branches found zero mentions; only the checkout
directory name (`personal_labs_proxywar`) carried the intent. The game IS live on the platform
(proxywar 0.1.35 canonical, league_cb60d526-ecfd-4836-ab3a-81fc6cf7dc42) and the repos are under
0xNad on GitHub (`ProxyWar`, `proxywar-coworld-starter`, `ProxyWar-starter-agent`).
Status: when a lab is "missing", check the platform (`coworld list`, `coworld leagues`) and GitHub
before concluding the work doesn't exist.

### coworld CLI wants FULL cow_/league_ IDs — table output truncates them
Evidence: `coworld download cow_1ce44ce9` → 422; the tables print `cow_1ce44ce9-…`. Widening with
`export COLUMNS=250` (or 300) makes `coworld list`/`leagues` print complete IDs. Also:
`download` takes `--output-dir` (not `--output`), and `results <div_id>` takes the DIVISION id
directly (no `--division` flag; passing the league id shows the division ladder instead).

### The starter README's "100-minute budget" is the EPISODE wall clock; the per-decision budget is 15s
Evidence: manifest `episode_timeout_minutes: 100` and per-variant `episode_timeout_seconds`
1200-5400, but every league variant sets `max_decision_ms: 15000`. An agent blocking >15s on a
model call per decision falls back; the starter's plan-in-background design exists precisely
because of this split.
Status: design any policy around the 15s decision deadline first, wall clock second.

### A "James Botts" entrant already sits in the Proxy War Competition division at score 0.0000 over 1066 rounds
Evidence: division standings for div_b54268ee-6b2f-4156-9c2a-8542645e31bc rank 23; but
`coworld memberships | grep Botts` shows no Proxy War policy (only stencil/beacon/wowborg/
sugarscape). Possibly an auto-mirror like beacon's CTF→Paintbot mirror.
Status: OPEN — resolve what policy backs that entrant before submitting anything, so a new
submission replaces rather than duplicates it.

### The Proxy War league's seat rung follows the champion count and the map pool rotates by round
Evidence: commissioner description in the 0.1.35 manifest — each Competition round counts real
distinct champions and routes to the largest declared rung (2/4/8/12/16) that fits, then rotates
that rung's deadline-proven map pool by round number. 16p added 2026-08-10/11 for ~25 entrants;
12p Europe is quarantined (repeated hosted artifact timeouts). Scoring: winner=1 else normalized
territory share; ladder rating is OpenSkill MMR since match sizes vary.
Status: evaluation batches should mirror the CURRENT rung (16 seats at 25 champions), not 1v1s.

### The recon's league facts aged out overnight; the game contract did not
Evidence: 24h after the founding recon (0.1.35), canonical was 0.1.39. `config_schema`,
`variants`, and game env were byte-identical — every delta was commissioner-side: (a)
World/Britannia/NorthAmerica quarantined at 12p AND 16p for multi-hour round wall-times
(effective 16p pool now Pangaea/Asia/BlackSea/EastAsia/Oceania), (b) Competition seating
windows shuffled per round (repo e3c04bd) after live measurement showed mid-list entrants
got 86-100% episode exposure vs ~7-14% at the ends, distorting EWMA ranks.
Status: split freshness checks in two: the WIRE contract (schema/variants/env — stable) vs
the LEAGUE contract (commissioner desc, map pools, seating — churns daily). Diff the
downloaded manifest's commissioner description on every session start.

### Standings are currently NOT a clean skill signal — a seating-exposure bug just got fixed
Evidence: e3c04bd measured rounds 1270-1365: rolling_window over a per-round-stable entrant
order pinned exposure to list position (the house seat decayed rank 1 -> 10 on exposure
alone). Post-fix, overnight: daveey 21.67->16.54, 0d1novizzz 14.69->9.10 (3rd->8th),
Jordan 13.71->15.54 (5th->2nd), James Botts 0.0000->0.5714.
Status: don't scout "who's good" from the pre-2026-08-12 table; let ~24 rounds (one EWMA
half-life, ~12h) of shuffled seating accumulate before trusting relative ranks.
