# CTF tentative lessons — session buffer

**Session started:** 2026-07-21 15:19. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---
### The deployed game ref lives in the coworld manifest — `coworld show <cow_id> --json` → `game.runnable.source_url`
Evidence: replay expansion hash-failed on all fresh league replays (league moved 0.7.4 → 0.7.49 silently). The episode's `tags.coworld_id` → `coworld show` gave the exact source ref (c76e0c75) on the first try; no guessing commits. Faster and surer than "try newer commits until a fresh replay expands".

### League episodes carry identity as `policy_results` (agents[].agent_id = slot), not xreq-style `participants`
Evidence: warehouse built 0 participants from league fetches until `_load_episode_meta` learned the `policy_results` shape. Any tool written against xreq episode.json will silently produce empty identity tables on league data.

### Enrich replay events with sim state at emission time — position-less events can't answer strategy questions
Evidence: rewrote expand_replay_json to run its own re-sim loop and attach x/y/aim to kills/shots/steals plus periodic pos/flag_pos snapshots. Every load-bearing recon experiment (phase profiles, escort distance, enemies-alive-at-steal, kill depth) needed those fields; the upstream human-timeline API doesn't expose them, and re-fetching later costs a full rebuild anyway. When re-simming, emit state-of-the-world rows (periodic snapshots), not just deltas.

### Fetching the same league episodes under multiple policies' batches duplicates rows — dedup by episode_id before any aggregate
Evidence: 144 fetched episode dirs → 95 unique episodes (focusfire-vs-Picasso games arrived under both policies' fetches). Raw GROUP BYs double-counted until q.py added ROW_NUMBER()-dedup views (eps/parts/ev).

### High-level stat pairs can invert under mechanism queries — always decompose before narrating
Evidence: Picasso "steals a lot" (88, most in field) reads as strong flag offense; the carry anatomy shows median carry = 23 ticks, 0px progress, 5.7% conversion — its steals are near-worthless. Conversely focusfire's low steal count hides a hard gate (0 steals before tick 3000) that is the *strategy*, not a weakness. Correlation checks need the reverse-causality control (steal↔win vanished once pre-steal kill margin was conditioned on).

### A "focus fire" claim is testable from replay events alone: count distinct same-team shooters whose aim ray intersects the victim within a lookback window
Evidence: ray-attribution (bearing vs aim ≤7 brads, 72-tick window) separated focusfire (28% multi-shooter kills) from Picasso (18%) on the same episodes with the same estimator. No policy internals needed.
