# Cady Version Log

## v1 — 2026-07-06

Deterministic gather-and-host baseline on the SDK SpriteV1 bridge.

- Connects through `players.player_sdk.run_sprite_bridge`.
- Reads labels and positions only; no pixel decoding.
- Navigates to visible food gardens before the gather cutoff.
- Returns to the recorded home anchor and holds there for dinner hosting.
- Sends no chat and uses no LLM.

This is the connect/gather/navigate/host/exit baseline. Coordination through
chat invitations is planned for v2.

## v17 — 2026-07-07 (guest-finding: baked occupancy heatmap guides the invite patrol)

v16's 3 zero-score games had low/zero chats: Cady never got in front of a crowd. Her seek logic
only knew about ON-SCREEN gnomes and blindly walked to map-center when her screen was empty.
Fix: a **per-game-hour occupancy heatmap** learned offline from **178 replays / 16.2M
other-player position samples** (`tools/build_occupancy_heatmap.py` → `mapdata/occupancy.npz`,
14 hours × 59×47 coarse cells). Invite `_seek_goal` now BLENDS: live visible-gnome centroid when
anyone's on screen; else the empirically-hottest cell for the current game-hour; else (no heatmap)
map-center. `cady/occupancy.py` is the runtime lookup (graceful None if unbaked). Verified hot
spots are walkable and shift by hour (morning gardens → house doors near dinner). 76 tests.
NOTE: near dinner villagers disperse to their OWN houses, so the single hottest cell sits at one
house — a follow-up is to prefer a spot central to MANY houses, hit early before they lock home.
## v20 — 2026-07-08 (comprehensive tracing + SUBMIT candidate)

Robust diagnostics before submitting. `CADY_DIAG` now emits (a) periodic full-state snapshots
enriched with belief + nav + social fields (own_house_index, directive_reason, circuit_index,
nav_goal/cursor/path_len/stuck_ticks, invited_houses, committed_party_house, villagers_in_view,
n_gnomes_visible) and (b) immediate TRANSITION lines whenever mode, strategy directive, map
context, inventory, invite-tour progress, party commitment, or a chat changes — so nothing
fires silently between snapshots. The SDK trace_sink (jsonl@artifact) also carries
mode_entered/strategy_evaluated/fallback events. Same play code as v19 (15/15 scored, mean ~141,
harvest floor fixed); this adds observability only. Built + uploaded + SUBMITTED with tracing on.

**SUBMITTED 2026-07-08** to Heartleaf league `league_f831ba75-e81b-4796-b8c6-cd10be18c0bf`
(`sub_ed58259d-57b4-499f-8c8e-36dbfc062ffa`, `--auto-champion always`, status pending →
placement async). Policy version `69d4490b-5181-4963-90c2-3956cbbe8cdc`. First Heartleaf
submission. cady:v20 = same play as v19 (15/15 scored, mean ~141) + full tracing.

**QUALIFIED → 👑 CHAMPION (2026-07-08).** Placed → qualified → moved into the Competition
division, membership `lpm_1ba945b3-b079-4cef-a0a3-733307a6c634`, status `competing`, champion.
Cady's first league championship — the deterministic gather→invite(door-to-door)→host build.
## v19 — 2026-07-07 (gather reliability: navigator stuck-detection → re-plan)

**RESULT — harvest floor FIXED.** 15/15 scored; harvest min 27→113, ZERO collapse games (was 2),
mean harvest 113→135. Score mean flat (145→141) — NOT a regression: with gather+nav solid,
score variance is now ENTIRELY guest-count driven. Proof: 31e63 (130 food, 15 guests) scored
248 while 0c540 (135 food, 1 guest) scored 54 — same food, 4.5x score. Low-score games had
full harvests + many chats but few villagers COMMITTED. Recruiting *conversion* is the next
lever (deterministic floor may be near its ceiling; the LLM layer targets exactly this).

v18 scored 15/15 but 2 games cratered to ~27 food (vs ~130 usual). Traced with the replay
tools: NOT competition or slow movement — a **navigation dead-stall**. From ~day 3 she froze
at one spot (~900 ticks, harvesting ~1/day): a STALE cached waypoint sat behind a wall relative
to her actual position, she held movement toward it (mask into the wall), and the arrival-only
cursor could never skip an unreachable waypoint → stuck until the day flipped. Root cause: the
navigator had no no-progress recovery. Fix: track per-frame progress (`nav_last_xy`,
`nav_stuck_ticks`); after `NAV_STUCK_TICKS` (~0.8s) of <`NAV_PROGRESS_EPS` movement, force a
re-plan from the CURRENT position (fresh find_path curves around the wall). 80 tests.
## v18 — 2026-07-07 (guest-finding: door-to-door invite rush + broadcast threshold 1)

**RESULT — scored 15/15 games (was 12/15), mean 145 (was 109, +33%), total 2179 (was 1637).**
Zero-chat/zero-score games ELIMINATED (0, was 3). Chats 6.5->9.5/game; guests appear at
nearly every dinner (1-3 each). The 2 lowest games (27,35) were HARVEST failures (27/29 food
vs ~130 usual), not recruiting — she still chatted+got guests. Door-to-door recruiting works.

v16 scored 12/15 but 3 zero-chat games showed she rarely got villagers in view while gathering
(measured: >=1 in view only 18% of gather frames, >=2 only 2%). Two changes:
(1) **Broadcast threshold 2 -> 1** — a lone in-view villager both hears and can accept, and
requiring 2 discarded ~9x the opportunities.
(2) **Door-to-door invite tour** — from 3 PM (gather stops), rush the 8 OTHER houses in a
greedy-nearest order (skip our own), broadcasting to anyone in view en route; peel home at
4:45. Villagers stand at their doors 3-5 PM and their souls only start hosting/double-booking
at 4 PM, so hitting them early catches them "free" (first invite heard wins — they won't
promise two dinners). No invite-tracking this round — just rush + blanket-invite. 78 tests.
## v16 — 2026-07-07 (ROOT-CAUSE FIX: clock was unreadable — all clock-gated phases were dead)

**RESULT — FIRST POINTS ON THE BOARD.** 15-ep hosted eval: Cady scored in **12/15 games**
(was 0/15 every prior version), mean **109/game** (max 239, total 1637), broadcasting invites
in 14/15. The full chain fires: clock reads → invite phase (seek crowd, broadcast) → villagers
commit + attend → host at own house at the 6:55 resolve → score = food × guests. Multi-guest
dinners appear (e.g. 2 guests × 96 food = 192). 3 zero-score games had low/zero chats (0,2,5)
— the recruiting-reliability tail is the next lever.

The bug behind every 0-score social eval, found via a new `time_minutes` diagnostic that read
**None on every frame, all game**. `SocialStrategy` is clock-gated (gather<420, invite 420-540,
host>=540), so a dead clock meant she NEVER left gather/exit_house — no invite, no real host.
This also means the earlier "host floor verified" was a false positive: she was only inside her
home at the day-reset teleport, never hosting at the actual 6:55 PM dinner (her inventory never
cleared, the tell of a host with a dinner).

Root cause: the game emits the clock as **"<Weekday> H:MMpm"** (e.g. "Monday 3:00pm"), one glyph
object per char. `read_clock_string` joined ALL glyphs -> "Monday 3:00pm", and `parse_clock_minutes`
(regex ^H:MMam/pm$) rejected the weekday prefix -> None, every frame. Fix: return only the final
whitespace-separated token (the time). Regression test added with the real weekday-prefixed format
(the old test used a bare "3:00pm" that never exercised the prefix). v15 was the diagnostic build;
v16 carries the fix. 73 tests.

## v14 — 2026-07-07 (invite: chat audience = in-view viewport box, not a radial guess)

Correctness fix on the seek-crowd invite: a gnome hears our chat iff our bubble lands in
their 320x200 viewport (cameras are self-centered), and perception only ever returns gnomes
already on OUR screen — so "in view of us" == "will see our chat". v13 used a radial <=150px
check, which is the wrong shape AND smaller than the 160px horizontal viewport reach, so it
skipped gnomes who were in view and would have heard us. v14 counts audience with the
rectangular in-view box (+-150 W / +-90 H, inset from the viewport half-extents). Strategic
gate unchanged (still wait for >=INVITE_MIN_AUDIENCE in view before broadcasting). The radial
v13 eval was killed unanalyzed (box strictly reaches >= radial). 72 tests.

## v13 — 2026-07-07 (invite: seek the crowd — passive door-stand got 0 guests)

v12's passive door-broadcast produced **0 chats / 0 guests / 0 score across 15 games** —
nobody wandered within earshot of her door in the 3-5 PM window. But crowds DO form near her
elsewhere (27% of her main-map frames had >=1 other gnome within 150px, up to 4). So v13 makes
invite ACTIVE: move toward the centroid of visible gnomes (or the map center when none are
visible), broadcast only once >=INVITE_MIN_AUDIENCE gnomes are in hearing range at once
(bubble lands on several viewers, not the first passer-by; relaxes to 1 as the window closes),
and return to our own door before the 5 PM host-enter cutoff. Still deterministic (LLM off).
Baseline to beat: v12 = 0 score. 72 tests.

## v12 — 2026-07-07 (social increment 2: invite guests — broadcast at our door)

The scoring lever: only hosts score (`food × guests`), and v11 hosted with 0 guests.
Increment 2 adds the deterministic **invite** phase (LLM still off). New `InviteMode` +
phase order: gather → **invite (3–5 PM)** → host (enter at 5 PM). During invite, Cady stands
at her OWN house door and, whenever another gnome is within hearing range
(`INVITE_HEARING_RADIUS`), broadcasts a ≤48-char line naming her own house by owner name —
`"Party at <PLAYER_NAMES[own_house_index]>'s house at 6! ..."`. That's the exact form a
villager's hearing→LLM→`inferSocialCommitment` path can parse into a commitment to attend us
([[heartleaf-villager-exploits]]): a heard invite naming a house can lock a villager there.
Standing at our door means hearers also SEE the party forming (crowd-snowball).

Also wires chat end-to-end (was dropped): `Intent.chat` → `Command.chat` → `decide` returns
`(mask, chat)`; broadcasts rate-limited by `INVITE_MIN_INTERVAL_TICKS` (no spam). Inviting is
inherently a pre-dinner, OUTSIDE-the-house action, so it precedes host in the schedule. 70
tests pass; chat flow verified. Invites only fire past 3 PM, so this needs a hosted eval.

## v11 — 2026-07-07 (social increment 1: deterministic host floor + press-and-verify A cadence)

> Uploaded version **v11** (`d27c4dc2`). Bundles two committed changes — the
> press-and-verify A-cadence refactor and social increment 1 — because the cadence
> refactor was committed but never uploaded on its own.

**Social increment 1 (the headline):** first step of the social/LLM controller
(`docs/designs/cady-social-llm-controller.md`), LLM OFF. Replaces `ClockStrategy` with
`SocialStrategy`: gather → (food-rich by 3 PM → prep) → **host through dinner**, on the
villager's phase skeleton. The scoring insight: to score you must be INSIDE your own home
map at dinner with ≥1 guest (heartleaf `startDinnerParties` skips a host whose
`mapIndex != mapIndex`). So `HostMode` now routes to our own house and ENTERS it (A on the
house footprint = enter; house index == gnome index == perception's `own_house_index`,
verified in `addPlayer`), then holds inside — instead of v1's "hold at the morning anchor
on the main map" which scored nothing. Anti-oscillation: host directives carry `ttl_ticks`
so a brief strategy/LLM hiccup can't yank us off hosting and back. Belief now folds visible
`gnomes` + a `committed_party_house` for the coming attend/invite work. Deterministic floor
only — the LLM layer and invite/attend modes come next. NOTE: the local cert fixture stops
before 6 PM, so hosting only exercises in a full hosted game.

**Press-and-verify A cadence (also in this upload):**

v10's hosted eval was clean (15/15 present 100%, harvest 193–240, enter/exit exactly
10/9 — nav + gather + actions rock solid). v11 is not a bug fix but a robustness change:
replace per-frame A-pulsing with a deliberate **press-and-verify cadence**. `_actuate_a`
presses A once, then releases for `A_PRESS_PERIOD` frames to observe whether the desired
result happened (a pickup / a door transition) before pressing again; the requesting mode
stops issuing the interact intent as soon as its result lands, so we press just enough to
get the result. Non-interact intents clear the cooldown. The house-footprint guard moved
from `action.py` into `gather.py` (it's a harvest decision: step off the house, then
harvest). Behavior preserved locally (enters 1 each, harvest intact); the win is we never
spam buttons. Same principle will govern the future invite/host A-presses.

## v10 — 2026-07-07 (fix: stop house oscillation — only press A at real food, never on a house)

v9's reliable harvesting worked (15/15 games, 118–245 food) but exposed a bad actions bug:
Cady entered/exited houses 267–1038× per game. The game overloads the A button
(harvest / enter-house / exit-home), so her aggressive A-pulsing entered a house whenever
she pressed A while standing on a house footprint. Confirmed in a replay: her circuit sends
her onto house 7's rect to "harvest" garden 30 (whose 40px radius overlaps the house) where
`gardens=0` (no food); she pressed A, entered the house, got kicked out, repeated — the
retry state reset each time so it never timed out.

Fix: (1) `gather.py` only presses A when a **visible food marker** is actually in range
(`MARKER_SIGHT_RADIUS`) — markers only appear with food, so this skips empty/absent gardens
and the house-overlap spot; (2) `action.py` never includes the harvest A while the foot is
inside a house rect. Local self-play: house entries dropped from hundreds to ~1 each;
harvesting preserved.

## v9 — 2026-07-07 (fix: reliable harvesting — press A in real range, retry until picked up)

v8 finally stayed connected and gathered, but only harvested in 13/15 games and converted
just ~60% of its garden approaches to food. Cause: a threshold/target mismatch. `gather.py`
fired `gather_at` (and advanced the circuit) within 40px of the garden **rect** — matching
the game's `InteractionRadius` — but `action.py` only pressed A within a stale
`GATHER_RANGE=12` of the **approach point**, otherwise it emitted a *movement* mask. So in
the 12–40px band `gather_at` walked instead of pressing A, and the circuit had already
advanced, losing that garden. Confirmed in the logs: the held mask at every `gather_at`
tick was a movement bit, never A (`1<<5`).

Fix: (1) `gather_at` now presses A every frame (and nudges toward the approach point to
settle a small perception offset) — `action.py`; (2) `gather.py` stays on the garden and
retries until a pickup is confirmed (inventory rose) or a short timeout (`MAX_GATHER_TICKS`),
instead of firing once and moving on. Local self-play (9 clones colliding on one circuit)
went from 0 harvests to real pickups; hosted eval to confirm.

## v8 — 2026-07-07 (fix: disable websocket keepalive — Cady stayed connected only ~33s)

**The bug that made every prior version score 0.** Cady disconnected ~20–48s into
*every* game (tick ~456–1152) and was absent for ~97% of it — not a navigation bug, a
connection bug. Root cause: the SDK bridge connects with the `websockets` default
keepalive (ping 20s / timeout 20s), and Cady's per-frame `decide` runs synchronously in
the async loop, delaying pong handling past the timeout → `websockets` tears down the
connection (reported as "server closed the connection"). Reproduced locally: all 9 self-play
instances dropped at tick ~800; with `ping_interval=None` all 9 survived to game end.

Fix: pass `ping_interval=None` to `run_sprite_bridge` (`main.py`) — the game's continuous
frame stream is the liveness signal, so library pings aren't needed. Diagnosed with the
replay expander + `viz_replay` and `coworld-local-run` (see `../docs/replay-tools.md`).

## v2–v6 — 2026-07-06/07 (nav foundation + coordinate-system fixes)

The navigation build-out and the self-position bug hunt. See `git log -- heartleaf_lab/cady`
for the per-commit detail; the arc:

- **v2** — baked map + A*-based router (`bf700ff`).
- **v3** — hierarchical router for fast arbitrary-point nav (`f3fefd5`); baked house
  interior + in/out-of-house detection + exit mode + diagnostics; circuit-following
  gather on the baked nav (`63d15e5`, `97db00f`).
- **v4–v6** — the coordinate-system fixes: self = own gnome **foot** (the root cause of
  every zero score, `6a6db67`), then + camera offset because the main map scrolls
  (`8e91650`). After these, Cady moves on the main map and exits the house — but still
  harvests nothing (inventory stays 0); she routes toward gardens but never lands within
  the 40px harvest radius. v7 + the replay tooling exist to diagnose exactly that.

## v7 — 2026-07-07 (announce username 'Cady')

Announce the display name **Cady** via a `?username=Cady` query param on the connection
URL (`76131f5`), so Cady is identifiable in replays. This is the enabling change for
debugging navigation with the replay expander + `viz_replay --player Cady` (see
`../docs/replay-tools.md`): without a stable name we can't spotlight her path. No behaviour
change beyond the announced name.
