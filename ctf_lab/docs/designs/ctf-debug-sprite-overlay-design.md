# Design: player debug-sprite overlays in CTF replays (Sprite-v1 `0x86`)

**Status:** approved design → implementation delegated to Codex (2026-07-14).
**Target repos:** `Metta-AI/bitworld` (PR 0, tiny dependency bump), `Metta-AI/coworld-ctf` (PR 1, the change).
**Author:** beacon lab session, 2026-07-14.

## Problem

We want to visually debug beacon's beliefs (player tracks, danger field, planned paths)
*inside the real replay viewer* — scrubbing the actual game with our overlay on top —
without building a standalone visualizer.

Sprite-v1 already specifies the channel for exactly this: client packet **`0x86` Debug
Sprites** ("player endpoints that render a private observation view and want to record
agent annotations such as planned paths, local labels, or diagnostic text"), whose payload
is ordinary **server-to-client sprite messages** (define sprite / define object / delete
object / clear objects). The replay codec on bitworld master has a matching record type
(**`0x06` ReplayDebugSpriteRecord**) with round-trip tests. The spec instructs: "Games
that support replay recording should store enough debug sprite packets to reconstruct the
player-authored overlay for each replay tick."

Nothing implements the game half. Four gaps (verified 2026-07-14):

1. **coworld-ctf pins bitworld `f5cf0d3`** — tip of `daveey/hd-client-pin`, which diverged
   from master at `5a4bea1` (2026-06-02), *before* the debug-sprite codec commit
   `87724ba` (2026-06-24). The pinned tree has zero debug-sprite symbols.
2. **The CTF server ignores `0x86`.** `applyPlayerViewerMessage` (`src/ctf/global.nim:408`)
   handles chat + input only, and nothing calls `writeDebugSprite`.
3. **No viewer renders `ReplayData.debugSprites`** — anywhere, including bitworld master.
4. (Out of scope here) the Python player SDK can't send `0x86`.

### Why not just repin CTF to bitworld master?

CTF's HD graphics need the **HD web client** (smooth scaling, `HdUiLayerFlag`-aware
layers) that only exists on `daveey/hd-client-pin`. The HD layer *flag constants* live in
CTF's own `src/ctf/hd.nim`, but the client HTML/JS that interprets them is the pin
branch's. Master lacks it; the pin branch lacks debug sprites. Hence PR 0.

## Goals

- A CTF player can send `0x86` debug-sprite packets; the server records them in the
  `.bitreplay`.
- During replay playback, the global viewer renders the recorded overlay for the
  **selected player**, tick-accurate under play/seek/scrub/loop.
- Live spectating gets the same rendering for free (same overlay state, fed live).
- Replay determinism and the tick-hash validation are completely unaffected.
- Old replays (no debug records) parse unchanged; new replays without debug packets are
  byte-identical to today's.

## Non-goals

- Python SDK pack support (`players.player_sdk.sprite_bridge`) — separate coworld-tools
  change, done later in the lab.
- beacon actually emitting overlays — follows the SDK change.
- Rendering overlays in the *player's own* client view.
- League redeploy — overlays appear in hosted replays only after the league runs a CTF
  build containing this change.

## Design

### PR 0 — bitworld: debug-sprite codec onto the pin branch

Cherry-pick `87724ba` ("Add debug sprite replay packets") onto `daveey/hd-client-pin`
(`f5cf0d3`) as a new branch, PR'd against `daveey/hd-client-pin`.

Verified: `src/bitworld/replays.nim` + `tests/test_replays.nim` + `docs/bitreplay_spec.md`
apply **clean**; `src/bitworld/spriteprotocol.nim`, `tests/test_spriteprotocol.nim`,
`docs/sprite_v1.md` have **trivial additive conflicts** (the pick also carries `0x85`
SpriteClientReady and the `SpriteLayer*` constants master added in the same region — take
both sides; all additive, harmless). This brings in:

- `SpriteClientDebugSprite = 0x86` + parse into `SpriteClientDebugSpriteMessage`
- `blobFromSpriteDebugSprites()` (client-side pack helper)
- `ReplayDebugSpriteRecord = 0x06`, `writeDebugSprite()`, `ReplayData.debugSprites`

CTF then bumps `nimby.lock`'s bitworld SHA to the new pin-branch tip.

**Coordination:** the pin branch is daveey's; the PR should tag him. If he prefers
merging master into his branch instead, that also works — CTF just needs a reachable
commit with both HD client and debug-sprite codec.

### PR 1 — coworld-ctf: record + playback + render

#### 1. Receive (`src/ctf/global.nim`, `src/ctf/server.nim`)

`applyPlayerViewerMessage` gains the new case branches (Nim's exhaustive `case` forces
this once the enum grows — a compile error is the checklist):

- `SpriteClientDebugSpriteMessage`: append `item.debugSprites` to a new
  `pendingDebugSprites: seq[seq[uint8]]` out-param (or on `PlayerViewerState`).
- `SpriteClientReadyMessage`: `discard` (CTF doesn't use frame pacing).

Server main loop (`runServerLoop`), in the same `withLock` block that drains input masks:
drain each player's pending debug packets. For each packet, when live (not
`replayLoaded`) and the player has a valid index:

- **Cap:** enforce `MaxDebugSpriteBytesPerTick` (const, 32 KB) per player per tick —
  drop the excess packet(s), `echo` a rate-limit warning once per player per game.
  Player-authored input must not be able to bloat hosted replays unboundedly.
- `replayWriter.writeDebugSprite(tickTime(sim.tickCount), playerIndex, packet)`
- Fold into the live overlay state (below) so spectators see it in real time.

#### 2. Overlay state (`src/ctf/global.nim`)

```nim
DebugOverlay* = object
  sprites*: Table[int, SpritePacketSpriteDef]   # payload sprite id -> def
  objects*: Table[int, SpritePacketObject]      # payload object id -> placement
```

`proc applyDebugSpritePacket*(overlay: var DebugOverlay, packet: openArray[uint8])`
folds one packet using bitworld's existing `parseSpritePacket`:

- `spkSprite` → upsert sprite def; `spkObject` → upsert object;
- `spkDeleteObject` → remove object; `spkClearObjects` → clear objects (keep sprite defs);
- `spkViewport` / `spkLayer` → ignore (overlays live on the map layer only).

One `DebugOverlay` per player index, owned by the server loop (live) and by the replay
player (playback).

#### 3. Replay playback (`src/ctf/replays.nim`)

`ReplayPlayer` gains:

- `debugSpriteIndex: int` — cursor into `data.debugSprites`, advanced in
  `applyReplayEvents` exactly like the chat/input cursors: while
  `debugSprites[cursor].time <= time`, fold the packet into
  `overlays[player]` and advance.
- `overlays*: seq[DebugOverlay]` — indexed by replay player index; grown on join like
  the mask tables.

**Seek correctness:** keyframes (`ReplayKeyframe`) store `debugSpriteIndex` like the
other cursors. On `restoreReplayKeyframe`, reset `overlays` to empty and **re-fold
records `0 ..< keyframe.debugSpriteIndex`** — overlay state is a pure fold of the packet
prefix, so rescanning is exact; packets are small and parse is cheap, so this is simpler
and safer than snapshotting tables into every keyframe. (If profiling ever shows this
matters at 100-tick keyframe spacing, snapshot instead; not expected.)

`resetReplay` clears the cursor and overlays.

#### 4. Render (`src/ctf/global.nim`, `buildSpriteProtocolUpdates`)

Render the overlay of the **selected player only** (`selectedJoinOrder` — selection
already exists via scoreboard/map click). All 16 at once is visual chaos; selection is
also how you'd naturally inspect one agent. No selection → no overlay.

- New id namespaces, documented alongside the existing bases:
  `DebugSpriteBase = 40000`, `DebugObjectBase = 40000`, `DebugPlayerIdStride = 1024`
  (sprite ids are u16 on the wire; 40000 + 16×1024 = 56384 < 65535, clear of the
  36000s HD icon range). Rendered id = `base + playerIndex*stride + (payloadId mod stride)`.
- Emit sprite defs through the viewer's existing `spriteDefs` de-dup cache
  (`addSpriteDefinition`), objects via `addWorldObject` on `MapLayerId` at
  `DebugOverlayZ = 29000` (above gameplay sprites, below the protocol-text UI at 30010;
  payload z is ignored — overlays must not interleave with UI).
- Register emitted object ids in `currentIds`/`nextState.objectIds` so the existing
  differ deletes them on deselect, seek, or object removal. Re-upsert of a changed
  sprite id must re-send the def (drop it from the cache on upsert with different
  dimensions/pixels).
- Live and replay share this render path; the only difference is which `DebugOverlay`
  seq is passed in (server's live fold vs `replayPlayer.overlays`).

#### 5. Format & determinism

- Replay record `0x06` is **additive**; `CtfReplayFormatVersion` stays **1**. New code
  reads old replays; old tools fail on new replays only if debug records are present —
  acceptable because replay tooling (`expand_replay`) is already strictly
  version-matched via the tick hash.
- Debug packets never touch `sim`, inputs, or `gameHash()`. The existing
  `tests/replays/ctf.bitreplay` must still validate hash-clean.

#### 6. Tests (mirror `tests/test_replay_controls.nim` style)

- Round-trip: write a replay with interleaved input + debug records; parse; assert
  `debugSprites` contents and ordering.
- Fold: `applyDebugSpritePacket` over define/upsert/delete/clear sequences.
- Playback cursor: step a replay with debug records; assert overlays populate at the
  right ticks; `seekReplay` backward and assert the overlay matches the prefix fold.
- Namespacing: two players using the same payload ids don't collide after mapping.
- Regression: existing replay tests (hash validation on `tests/replays/ctf.bitreplay`)
  unchanged.
- Cap: an oversized packet is dropped, small ones still recorded.

## Risks / open questions

- **Pin-branch coordination.** PR 0 lands on daveey's active branch; he may prefer a
  different route (merge master in). Small, additive, and reviewable either way.
- **Replay size.** Capped per tick, but a chatty player can still add ~MBs over a
  10k-tick game. Mitigation: cap + spec-encouraged diff-style authoring (define sprites
  once, move objects). If needed later: per-game byte budget.
- **HD-graphics churn.** `global.nim` was just heavily reworked (HD PR #1/#2); implement
  against current `main` (`634f6aa`) and keep the render hook minimal to dodge conflicts.
- **Which players' overlays in live mode?** v1: selected player only, same as replay.

## Follow-ups (not this PR)

1. coworld-tools SDK: `pack_debug_sprites_packet()` + a `debug_sprites` return channel in
   `run_sprite_bridge`'s decide result.
2. beacon: emit danger-field heatmap sprite (38×20 RGBA, `cell_px` scaled) + track
   markers + nav path polyline each snapshot tick.
3. League redeploy picks up the new CTF build → hosted replays carry overlays.
