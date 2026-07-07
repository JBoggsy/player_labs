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
