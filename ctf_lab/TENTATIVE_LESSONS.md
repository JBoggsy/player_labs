# CTF tentative lessons — session buffer

**Session started:** 2026-07-23 13:46. This is THIS SESSION's lesson buffer. Write candidate
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

### Both teams' total lives remaining ARE readable from the player POV stream — beacon ignores them
Evidence: `global.nim buildSpriteProtocolPlayerUpdates` (player websocket stream, server.nim:1202/1291)
emits (a) own `"lives <hp>hp x<lives>"` HUD label (own remaining respawns) and (b) the
`addTeamScoreboard` labels `"team score RED <kills>/<deaths>"` / `"team score BLUE …"` every Playing
frame. Team lives remaining = 24 − team deaths (8 players × 3 lives; exact while nobody disconnects).
`perception.py` parses neither label today. Per-player permadeath of teammates is NOT observable
in-round (dead teammates render nothing to a live viewer; per-player lives only appear in the
spectator scoreboard and the GameOver interstitial). CORRECTION (James caught this): the lives
TIEBREAK is gone — fac8704 (0.7.6x era, 2026-07-14) made timeout a scoreless draw, and GV21
(a768a0e) makes a timeout draw -1 for EVERY player. So lives-lead has no endgame-tiebreak value;
the remaining uses are (a) enemy team lives (24 − enemy deaths) to gauge wipe feasibility and
(b) own remaining respawns for risk calibration. docs/ctf-gameplay.md is stale on tiebreak,
scoring (+100→+1/-1/-1), maxTicks (10000→5000), and spawn protect (removed GV20) — needs reconcile.

### The trace pipeline was silently dead for ~9 versions — the warehouse read the fallback transport, not the default
Evidence: every warehouse build since v18 printed "0 trace events" and nobody noticed until the
squad-tactics investigation needed traces. Beacon wrote traces to `jsonl@artifact` (the default)
but `_load_trace_events` only parsed the stderr-fallback `CTF_DIAG` log lines. Two lessons:
(a) when a pipeline has a default transport and a fallback, the reader must cover the DEFAULT
first; (b) "0 rows" from a component that should always produce rows is an error, not a skip —
the build log line even showed it every time. Also: recon fetches used --no-artifacts, which
discards the trace zips — episodes fetched for behavioral analysis need artifacts.

### Trace ticks are per-bot frame counters, not engine ticks — align via first-spawn ↔ phase=Playing
Evidence: first alive=true trace ticks for the same episode's spawn varied 122-179 across seats
(connect-order dependent) while the replay's Playing tick was 230 — offsets of 51-108 ticks that
would smear any cross-bot analysis keyed on raw tick. Warehouse now stamps eng_tick per
(episode, slot) using the shared spawn moment. Any future per-tick trace consumer must use
eng_tick for cross-bot or trace-vs-replay joins.

### The player-binding trap fired a THIRD time — check `coworld player list` before UPLOAD, not submit
Evidence: a leftover `coworld player use seedtest-loop1-newcomer` session (likely from unrelated
seedtest work) silently bound the v26 upload to the seedtest player — caught only because the A/B
episodes' participants showed `seedtest-base-veteran`. v22 had the same failure. The pre-submit
binding check is too late: the UPLOAD is what binds. New reflex: `coworld player unset` (or verify
no ● active marker) immediately before every `upload-policy`, then a 1-ep probe xreq to confirm
`player_name` before submitting.

### Division opponents iterate daily — recon the CURRENT field before every submit/measure
Evidence (2026-07-27): three days after the v26 A/B, focusfire went v1→v56 (stopped feeding kills;
our 10W/0D became 4W/6D), h006 was REPLACED by h035 (rank 2, beats us 6L/10 by mid-lane attrition +
23 steals/10 games), and a brand-new `swarm` sits rank 3. Any tuning targeted at last week's
opponent (e.g. our convert threshold tuned on focusfire v1's over-extension) may be stale on
arrival. Matched same-window A/Bs remain the only valid comparison; opponent-specific tuning needs
a freshness check first.

### v26 convert A/B: reading the global scoreboard converted every focusfire draw to a win
Evidence: v26 (enemy_lives ≤ 6 → all squads order T at freshest enemy fix) vs v25 matched A/B:
focusfire 5W/5D/0L → 10W/0D/0L (p<0.001), zero losses, stacking still fixed. Vs h006 the trigger
fires (4/10 episodes crossed ≤6 lives; v25 never did) but the fight trades 1:1 (21-22 kills each)
and the clock ends it — the remaining h006 gap is fight quality/captures, not doctrine. Pattern:
fog-independent GLOBAL signals (scoreboard, pedestal state, tick) are the coordination currency in
this game — they need no comms and every agent reads the same value.

### xreq 404s right after create are INDEXING LAG, not deletion — wait before re-firing
Evidence: 5 "vanished" v25 arms (404 on GET seconds-to-minutes after create, one still 404 at
t+30s) ALL later showed completed — burning ~6 duplicate xreqs and an hour of refires. The
fetcher's --watch also dies on the 404 (crash, not retry). Rule: on a fresh xreq 404, wait several
minutes and re-check before re-creating; consider a fetcher retry patch.

### v25 spread A/B: the mechanism can work and the outcome still regress — measure the outcome
Evidence: stacked-ticks collapsed (67→5.6/appearance vs h006) and losses went to ZERO in both
matchups, but wins fell (7→5 vs focusfire, 2→0 vs h006) and draws exploded — every focusfire draw
had beacon at 21-23 kills, 1-2 short of the 24-kill wipe, with spread holders never collapsing to
finish. Under GV21 (draw = -1) "safer" without "converts" is a strict regression. The spread needs
a finisher: when the wipe is within reach (enemy lives low / long since enemy contact), collapse
and hunt. Also: team kills were only ~0.4/game in v24 — the visible stacking was real but its TK
cost was small; the draw problem dominates everything.

### The league redeployed AGAIN mid-session (0.7.69→0.7.70) — matched arms saved the A/B
Evidence: yesterday's v24 measurement (0W/9D/1L vs focusfire) vs today's v24 arm (7W/0D/3L vs the
SAME opponent) — wildly different, because the game moved under us overnight. Only the same-window
matched pair is interpretable. Reflex confirmed: never diff against a stale batch.

### A shared order point + per-member A* = a stacked squad; spread must be structural, not a force
Evidence: v22-v24 orders send every squad member to the SAME cell; the v19 separation force never
applied to order-driven movement, and a HOLDING agent emits no movement at all — so squads stacked
permanently at hold anchors (9,006 pair-snapshots <25px in the v24 batches; 3/5 beacon TKs at
≤14px). Fix shape (v25): rank-offset the shared point (pure seat math, like aim sectors) + a
separation-only nudge as the hold state's one permitted movement. Reactive forces can't fix a
converged-target problem — the targets themselves must differ.

### The league runs the manifest VARIANT game_config, which overrides config.json — visionConeDeg is 45, not 60
Evidence: repo config.json says visionConeDeg 60 (commit 15856d8 widened it), but the manifest's
Default-variant game_config still says 45 — and a fresh v24 episode.json's game_config confirms 45
live at 0.7.69. beacon's VISION_CONE_HALF_DEG had been 60 (from config.json) since ~v13; fixed to 45
in this audit (affects items._in_view negative-confirmation and squad sector-coverage math). Rule:
the deployed truth is episode.json's game_config, not any file in the game repo.

### A timeout draw is -1 for BOTH sides (GV21), not scoreless — session-7's premise was wrong
Evidence: deployed sim (`72fb1b1`) TimeoutReward = -1 applied to every player; empirically every
drawn v24 episode's results.json scores all 16 players -1. WORKING_CONTEXT/user_preferences/
VERSION_LOG all said "timeout = scoreless draw, tie costs 0". Corrected everywhere this audit.
Strategic consequence: v24's 14 draws each PAID -1; draws only beat losses by denying the enemy +1.
The convert trigger matters more than session 7 thought.

### docs/ctf-gameplay.md is stale vs the deployed game — verify rules against the repo before citing
Evidence: answered a rules question from the doc (lives tiebreak, +100 win-only scoring) and both
were wrong vs coworld-ctf origin/main (fac8704: no tiebreak; WinReward +1 / LossReward -1 /
TimeoutReward -1 GV21; maxTicks 5000; spawn protect removed GV20). WORKING_CONTEXT.md already knew
("0.7.69: timeout = SCORELESS DRAW (no lives tiebreak)"). Also: ctf_lab/tools/versions.env CTF_REF
(761c098, 2026-07-10) predates these league redeploys.
