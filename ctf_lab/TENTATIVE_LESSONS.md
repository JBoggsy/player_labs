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
### The player observation wire is back to 1x map pixels since ctf 0.7.8 — the "3x render scale" era is over
Evidence: v6-v9 perception divided coords by 3 (correct for 0.6-0.7.7); at 0.7.49+ the POV stream is 1x (global.nim: boardScale=1 for player streams; RenderScale=2 is spectator-only), the aim-dot indicator is retired (self sprite id 5100+rot IS the aim readback, 16-step), and flags are labeled `<color> flag [planted]` not hearts. beacon v6 was effectively blind on the live game and sank to rank 6. Wire-format regressions across redeploys are silent — a policy that connects and idles looks "alive"; check the RULES.md + global.nim POV branch at the deployed ref after EVERY redeploy.

### The deployed game version moves mid-session — pin the replay reader per batch, read the ref from each xreq's coworld
Evidence: 0.7.49 → 0.7.51 between the recon fetch and the v10 measurement (2 hours). Each xreq reports its `coworld`; `coworld show <cow_id> --json` → manifest game.runnable.source_url gives the exact ref for expand_replay.

### Accuracy is a fire-discipline metric, not an aim metric: gate on range before improving prediction
Evidence: v10 lead-aim alone left acc at 0.234 because beacon fired 7,804 shots (~5x opponents' volume) — most beyond where the 5-brad aim quantization can hit the 14px corridor. A hold-fire gate at 350px (v11) moved acc to 0.333 with no aim change and IMPROVED wins (first-ever 7-3 Picasso, 8-2 autoresearch). Shot-volume parity matters more than per-shot cleverness.

### The fire windup releases from the shooter's CURRENT position — strafing through it displaces your own shot
Evidence: sim.nim applyFire uses the shooter's position at release (5 ticks after pull) with the ANGLE locked at the pull; a strafing shooter moves ~2.75px/tick → ~14px lateral displacement = one full hit-corridor. v12 freezes movement for FIRE_WINDUP_TICKS after each trigger pull (carrier exempt).

### Items activate via deterministic seat-claims with zero radio: assignment as a pure function of (seat) is enough
Evidence: v10's single-claimant table (seat 2→shield, 3/4→corner grenades) produced 20% shield alive-time (89% on the assigned seat) and real grenade throws in the first measured batch, with no coordination protocol — every agent computes the same table, so no two rush one pickup.
### Glass windows (GameVersion 15/16) break the "visible = shootable" assumption — fire gates need a bullet-LoS check
Evidence: windows pass vision but block bullets/plasma. beacon fired through them at guaranteed-miss rate until v14 added `mapdata.ray_clear` to the fire gate (windows stay in the wall mask since it models the BULLET question). Combined with boundary-crossing aim calibration this took acc 0.312 → 0.657 in one step.

### The 16-step aim readback yields an exact fix at step boundaries — calibrate on the CHANGE tick, not the value
Evidence: the self sprite's rotation quantizes aim to ±8 brads, too coarse to resync against directly; but the tick the observed step CHANGES while rotating, the true aim is at the boundary between steps (±rate/2 = ±2.5 brads). v14's boundary-crossing calibration was the biggest single accuracy lever.

### An A/B regression can be a MAP-truth signal, not a code signal — check the arena/geometry pins before reverting
Evidence: v12 (mechanically sound windup freeze) REGRESSED vs v11; the real cause was the arena changing under us (GameVersion 16 moved/removed obstacles; nav.npz was stale, agents pathed into ghosts). Reverting v12 would have been wrong; rebaking nav (v13) then v14 vindicated it. When a clean change regresses, verify the baked world model against the deployed ref first.
### "1v1" is James's standing term for the uniform-sides 8v8 eval — documented in ctf_lab/user_preferences.md
Evidence: the shape (16 pinned slots alternating beacon/opponent by parity, 10 eps) existed only in gitignored scratch bodies; James asked whether it was stored long-term and it wasn't. Now canonical in user_preferences.md (the XP-request skill checks that file before composing) + agent memory.

### Rank-1 newcomers can invert the field's known metas — profile them before tuning against the old #1
Evidence: ctf-h006 (appeared overnight, rank 1) plays the OPPOSITE of focusfire: tick-0 blitz instead of turtle, arc-forward kit instead of shield/grenade, mid-game steals. A counter tuned for focusfire's phase machine (defensive early game) is exactly what h006's blitz would also punish least — but faster conversion (the anti-focusfire lever) walks into h006's blitz. Opposite postures; check both matchups before shipping either.
### Hearing works as perception (95 events/agent folded) but duck-on-heard-fire barely fires (0.5 ticks/agent) — the gate is too narrow, not the signal
Evidence: v16 traces show the pipeline is healthy end-to-end (rings perceived, deduped, danger stamped), but the behavior consumer required gun-down + ≤180px + fresh + off-aim-ray simultaneously, which almost never co-occurs. The perception layer is the durable win; consumers likely need to gate on the danger field (which hearing now feeds) rather than on raw events. Also: focusfire series moved 0-10 → 4-10-ish draws-not-counted, needs a proper A/B read before crediting hearing.
### Hearing A/B vs focusfire: NULL — the v15→v16 "hearing win" was noise; a 10-episode delta is not attribution
Evidence: pre-registered A/B (40 eps/arm, 1v1 vs ctf-focusfire:v36, identical v16 image, only BEACON_HEARING flipped via --secret-env → beacon:v17): ON 7/40 (17.5%) vs OFF 8/40 (20.0%), Fisher p=1.0, diff −2.5pp CI [−19.7, +14.8]; accuracy 0.619 vs 0.621, deaths/agent 2.56 vs 2.67. Manipulation check passed hard (OFF: 0 heard_events across 48 sampled agents; ON: 4062, all 48 agents). The motivating 0-10 → 4-6 jump did not replicate — BOTH arms beat old v15's 0/10, so the improvement lives elsewhere in v16 (or in the map/opponent context), not in hearing. Confirms the earlier trace read: duck-on-heard-fire barely fires (19 heard-duck ticks / 48 agent-games); hearing feeds the danger field but no consumer converts it to wins yet. Full report: ctf_lab/scratch/ab_hearing/AB_REPORT.md.
### The full chat loop (send → bubble → parse → decode → belief → behavior) verified live in one iteration
Evidence: v18 smoke (20 eps): 2,013 shouts sent across 5 kinds (E 1090 / U 735 / G 123 / C 50 / T 15), 4,488 same-team decodes heard, 1,050 enemy-bubble position fixes, and all three consumers fired (intercept_thief_heard 11, clear_grenade 13, escort_carrier_heard 2). Per-kind cumulative counters in snapshots made this a five-minute readout. Note E/U dominate the send budget — priority arbitration may need tuning when C/T matter more (carrier alive-time is just rarer).
### Fog hides your own squadmates: buddy-SENSING coordination deadlocks — synchronize on tick instead
Evidence: v19's rally gate ("hold until N teammates visible nearby") never released — everyone at the rally aims enemy-ward, the 60° cone + 90px bubble miss a mate 60px behind, buddies_near reads 0, and every attacker burned the full 150t timeout every push (153 wait-ticks/agent). v20 replaced sensing with tick-windows (commit only in the first 36t of each 120t period): a pure function of tick every agent computes identically — the one squad signal fog can't hide. Same principle as seat-deterministic membership: in low-observability games, coordinate on shared clocks/tables, not on perception.

### Platform churn is now the dominant iteration hazard — xreqs can be deleted server-side mid-flight
Evidence (2026-07-22 evening): league redeployed 0.7.51→0.7.66 mid-iteration (maxTicks 10000→5000, spawnProtectTicks removed — invalidates cross-version baselines), then two consecutive focusfire xreqs 404'd server-side minutes after creation, and the division memberships list went empty (restructure in progress). When an xreq 404s, check platform state before re-posting; when standings look weird, check whether the field itself is mid-migration.
### Nameplate identity == seat: alpha-theta is slot-order-within-team, exactly beacon's seat notion
Evidence: 0.7.69 slotIdentityIndex assigns identities by rank among same-team slots — identical to beacon's seat = slot//2 derivation. So a badge read IS a seat read: squad membership checks reduce to `identity in squad_seats`. No mapping table needed.

### A second map ("arena-large", 1606x858) now exists in the game — check mapPath on every redeploy
Evidence: 0.7.69 refactored CtfMap to carry per-map geometry (incl. gunRange 1300→1690 on large) and added ArenaLargeLeftObstacles. Deployed config still selects "arena", but a flip would invalidate nav.npz, PEDESTAL, HOME_DEEP, CHOKE_X, rally lines, and item spawn formulas simultaneously. The bake and config constants all assume 1235x659.
### v22 squad command shifted the outcome DISTRIBUTION exactly as lives>captures predicts — wins traded for draws
Evidence: v22 vs focusfire went 0W/6D/4L (v21: 0W/0D/10L) — back-off + rejoin discipline stopped the feed (draws = preserved lives to the clock) but also stopped converting. vs h006: 0W/3D/7L. The command layer is fully live (2.3k orders sent/heard, 4.9k/14.8k pings sent/heard, 227 backoff events, 214 rejoin ticks/agent). The missing half of the principle: "hold when weak" works; "convert when strong" has no trigger yet — no leader rule re-orders a PUSH when presence recovers/enemy weakens, so squads that back off stay backed off. Draw-heavy is strictly better than loss-heavy but needs the convert trigger to win.
### Uploads can silently bind to a non-default player with NO active session — verify binding before submitting
Evidence: v22 uploaded via the bare coworld tool bound to the secondary player 'seedtest-base-newcomer' despite get_active_player_id() returning None in both credential stores; submit then 409'd ("already assigned to player ply_…"). Fix: re-upload (v23) after clearing sessions and confirm via /stats/policy-versions?player_id=<default_ply> that the new version appears there BEFORE submitting. The plain version row always shows player_id=null — only the filter reveals the binding.

### Side-lane anchored holds nearly stalemate-proof focusfire's phase machine
Evidence: v24 defaults (A holds top lane, B bottom at the choke, C pushes mid) took the focusfire series from 0W/6D/4L (v22) to 0W/9D/1L. The turtle→push→late-capture pattern needs a lane to break through; two anchored 3-person squads with sector coverage deny it. h006 also improved (1W/5D/4L from 0/3/7).

### The hold-half of "lives > captures" is saturated — 14/20 draws with zero conversion attempts is the ceiling
Evidence: v24's 20-game batch produced 14 draws; several with banked lives leads (11-5, 8-5) and no push. Every marginal gain now sits in the convert trigger (leader rule: presence recovered / enemy weak → escalate H→P/F), not in more discipline.
