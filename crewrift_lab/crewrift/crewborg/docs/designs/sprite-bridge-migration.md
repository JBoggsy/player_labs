# Migrate crewborg's transport onto `players.player_sdk.sprite_bridge`

**Status:** proposed, 2026-07-06. Investigation done; no code changed yet.

## Why

Crewborg currently **vendors its own Sprite-v1 transport layer** — a full websocket
connect/reconnect loop, raw binary frame parsing, and input/chat packet encoding —
predating a **generic BitWorld/SpriteV1 bridge** that has since landed in the
players SDK (`coworld-tools` `players/players/player_sdk/sprite_bridge.py`, merged
2026-07-06 as PR #20, commit `e8921a6`). That bridge exists specifically so games
like Crewrift don't have to hand-roll this: "a game may import
[the bridge] ... to do it" (its own docstring). We should stop vendoring the parts
it now owns.

**Our current pin predates it.** `pyproject.toml`'s `players` source SHA is
`6dcd022e013febffb0043b5f625f853c5cc36e0f` — one commit *before* `cb1f963`
(`feat(player_sdk): port BitWorld/SpriteV1 bridge...`). `sprite_bridge.py` isn't
importable at all until we bump the pin.

## What the new bridge is

`players.player_sdk.sprite_bridge`:

- `SpriteWorld` — accumulates the raw `/sprite_player` binary stream into
  `sprites: dict[int, SpriteDef]` / `objects: dict[int, SpriteObject]`. Deliberately
  does **not** decode pixels, palette, or game semantics — "a game may import
  mettagrid's `snappy_decompress`... to do it" (i.e. semantic decoding is explicitly
  the game's job, not the bridge's).
- `pack_input_packet(mask)` / `pack_chat_packet(text)` — the two outbound packet
  encoders.
- `run_sprite_bridge(url, decide, ...)` — the full per-connection loop: connect,
  accumulate frames into a `SpriteWorld`, call `decide(world, ctx)` once per
  world-changing frame, pack and send the result. Built on the engine-agnostic
  `run_message_bridge` (peer to a `cogweb` and a `mettagrid` bridge).
- Record kinds it understands: `0x01` sprite def, `0x02` object upsert, `0x03`
  object remove, `0x04` clear, `0x05`/`0x06` — both treated as **opaque skips**
  (5 and 3 bytes respectively; "timing/keepalive").

## What maps onto crewborg's current vendored code

| Crewborg file | Currently does | SDK equivalent |
|---|---|---|
| `perception/decoder.py` (`apply_message`, 193 lines) | Raw record-parse loop: `MSG_DEFINE_SPRITE`(`0x01`)/`_OBJECT`(`0x02`)/`DELETE_OBJECT`(`0x03`)/`CLEAR_OBJECTS`(`0x04`)/`SET_VIEWPORT`(`0x05`, 5-byte skip)/`DEFINE_LAYER`(`0x06`, 3 bytes) | `SpriteWorld.apply_frame` — same wire format, same record kinds. `SET_VIEWPORT`(`0x05`) and `DEFINE_LAYER`(`0x06`) map exactly onto the bridge's `_RECORD_SKIP5`/`_RECORD_SKIP3`. |
| `action.py` (`encode_input`, `encode_chat`) | `0x84`+mask / `0x81`+u16 len+ascii — hand-rolled, functionally identical | `pack_input_packet` / `pack_chat_packet` (the SDK version raises on invalid input rather than silently truncating/ignoring — a **behavior tightening**, not a loosening) |
| `coworld/policy_player.py` (`run_bridge`, `_connect_with_retry`, `_run_session`) | Full connect/reconnect loop + per-tick session drive | `run_message_bridge`/`run_sprite_bridge` provide the **generic per-connection session runner only** — see the gap below |

## What must NOT move — game semantics, by the bridge's own design

`SpriteWorld` is intentionally raw. Crewborg's `perception/decoder.py` also
decodes, on top of the same raw records:

- **walkability** — snappy-decompresses the `"walkability map"`-labeled sprite's
  pixel data into a bool grid (nav).
- **shadow** (line-of-sight) — same, for the vision-overlay sprite.
- **camera** — recovers world-origin from a specific object id/sprite id pair.
- **server tick** — parses the `"tick <N>"` labeled sprite.
- **layer defs** — decodes `DEFINE_LAYER`'s type+flags into `LayerDef`, stored in
  `scene.layers`.

None of this exists in or belongs in the generic bridge — it's Crewrift-specific,
exactly the "game's player package" responsibility the bridge's docstring
describes. It all needs to keep living in `crewrift_lab`, just **re-based to read
off a `SpriteWorld` instead of re-parsing raw bytes itself.**

**One simplification the investigation surfaced:** `scene.layers`/`LayerDef` is
captured but **never consumed anywhere in the runtime** (`grep` across
`crewrift/crewborg` outside decoder/tables/tests: zero hits). Since the generic
bridge treats `DEFINE_LAYER` as an opaque skip, migrating naturally drops layer
capture — that's a safe deletion of dead data, not a feature loss. No need to
petition upstream for layer-decode support.

## The one real gap: reconnect robustness

`message_bridge.py`/`run_sprite_bridge` do **a single `connect()` call, no
retry** — `on_close` only classifies whether the eventual close was clean, it
doesn't reconnect. Crewborg's vendored loop has two retry mechanisms **added
after real production incidents**, documented at length in `policy_player.py`:

1. **Aggressive initial-connect retry** (`RECONNECT_DEADLINE_SECONDS`, flat
   0.1s interval) — fixes a real, previously-observed failure mode: hosted
   episodes dying at a high rate with `-100 connect_timeout` because the player
   container raced the engine's socket coming up.
2. **Mid-game reconnect tolerance** (`MIDGAME_RECONNECT_ATTEMPTS`) — an abrupt
   drop is ambiguous between "game over" (the engine's actual close signal) and
   a transient network blip; crewborg tries a few reconnects before concluding
   game-over.

**Migrating naively (swap in `run_sprite_bridge` wholesale) would silently drop
both** — a real reliability regression on a lever this lab has already paid to
fix once. The safe design: **keep crewborg's outer retry loop**
(`_connect_with_retry`'s state machine, `_BridgeState` for cross-reconnect
continuity) and swap only what runs **inside one connection attempt** — replace
`scene.apply(message)`'s raw byte-parse with `SpriteWorld.apply_frame`, and
`encode_input`/`encode_chat` with `pack_input_packet`/`pack_chat_packet`. Do
**not** call `run_sprite_bridge` itself (it owns exactly the connect-loop we need
to keep bypassing).

A bigger, separate-follow-up option: contribute a reconnecting `Connect` wrapper
upstream to `message_bridge.py` so every SDK-bridge game gets this for free — real
value, but a different-scoped PR against `coworld-tools`, not part of this
migration.

## Proposed migration steps

1. **Bump the pin.** `pyproject.toml`'s `players` tarball SHA `6dcd022...` →
   `e8921a6` (current `coworld-tools` main tip, includes the merged bridge PR).
   Update `crewrift_lab/tools/versions.env`'s comment accordingly. `uv lock`.
2. **Rebase `perception/decoder.py` onto `SpriteWorld`.** Replace the raw
   record-parse loop with a call to `SpriteWorld.apply_frame(message)`, then walk
   `world.sprites`/`world.objects` to do the SAME semantic decode (walkability,
   shadow, camera, tick) crewborg does today — reading from the SDK's tables
   instead of `scene`'s own. Drop layer-def capture (dead data, see above).
   `SceneState` likely collapses into a thin wrapper around a `SpriteWorld` plus
   the decoded walkability/shadow/camera/tick fields, or those become properties
   computed from `SpriteWorld` on access — the exact shape is an implementation
   decision, not settled here.
3. **Replace `action.py`'s packers** with `pack_input_packet`/`pack_chat_packet`
   (or keep thin re-exports for call-site stability) — note the SDK versions
   validate/raise rather than silently dropping bad input; decide whether
   `encode_chat`'s current "ignore non-ASCII" behavior needs to be preserved
   upstream of the call (pre-filter) or whether raising is actually preferable
   (surfaces a bug instead of silently mangling chat).
4. **Keep `policy_player.py`'s outer loop**, swap its inner per-message handling
   to delegate to the rebased decoder/`SpriteWorld` instead of `scene.apply`.
5. **Update tests** — `perception/decoder.py`'s tests need to construct/inspect
   `SpriteWorld` state instead of the old raw scene tables; add a test asserting
   the reconnect loop still works with the new inner frame-handling (the SDK's own
   338-line `test_sprite_bridge.py` already covers `SpriteWorld`/packers in
   isolation — no need to re-test that logic, only the integration point).
6. **Update docs** — `AGENTS.md` §Transport, `design.md` §3, and
   `docs/crewrift-protocol.md`'s framing (currently describes crewborg's own
   from-scratch decoder as the reference implementation) to say "transport via
   `players.player_sdk.sprite_bridge`; game semantics (walkability/shadow/camera/
   tick) decoded locally on top of it."

## Risks

- **Reconnect regression** if step 4 is done carelessly (calling
  `run_sprite_bridge` instead of keeping the outer loop) — the main risk, fully
  mitigated by the design above if followed.
- **Version-pin bump scope** — `6dcd022` → `e8921a6` pulls in whatever else
  landed in between (worth a quick `git log 6dcd022..e8921a6 --oneline` diff
  review before bumping, to confirm nothing else changes behavior unexpectedly).
- **`encode_chat` behavior tightening** — SDK's `pack_chat_packet` raises on
  non-ASCII/empty/oversized input where crewborg's current version silently
  drops/ignores; decide the desired behavior explicitly rather than let it be an
  accidental side effect of the swap.

## Non-goals

- Not migrating notsus/suspectra (Nim players, unrelated — they vendor their own
  Nim-side `protocols.nim` against `bitworld/spriteprotocol.nim` directly and
  aren't touched by a Python SDK change).
- Not contributing the reconnect wrapper upstream in this pass (noted as a
  separate future option above).
- Not changing any gameplay/strategy logic — this is a transport-layer-only
  refactor; `runtime.step` and everything downstream of `Observation` is
  unaffected.
