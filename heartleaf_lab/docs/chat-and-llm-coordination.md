# Heartleaf chat + how the villager coordinates its LLM (reference)

Captured 2026-07-06 for when cady gets a chat/coordination layer (deferred until
navigation works). Sources: `coworld-heartleaf/src/heartleaf.nim`,
`players/talking_villager/talking_villager.nim`, the SDK `sprite_bridge`.

## How chat works in the game

**Chat is a text packet, not a controller button.** cady already has the plumbing
(`Command.chat`), it's just never set.

- **Send:** return `(mask, "message")` from `decide`. The SDK bridge packs it as a
  chat packet (`0x81` + u16 len + printable ASCII) and the game accepts it as that
  player's chat (`heartleaf.nim` `playerChatFromMessage` → `isChatPacket`/`blobToChat`).
  **Cap: 48 chars** (`ChatMaxChars`).
- **Receive:** an incoming message appears as a sprite object at `ChatObjectBase +
  playerSlot` (3000+) whose **label is `"chat <text>"`** (`heartleaf.nim:1038`) —
  readable straight from the label (no pixel decode), persists ~5 s
  (`ChatLifetimeTicks = 5*24`). This is how the villager reads chat (`visibleChatText`).

## How the villager coordinates its LLM (the timing answer)

The Bedrock call takes ~3 s; the engine pushes frames at 24 Hz and does not wait for
the player. The villager decouples the two with three pieces:

1. **Non-blocking HTTP (curl-multi), not threads.** `startTalkToBedrock` fires the
   POST via `bedrockCurl.startRequest` (async); `pollTalkToBedrock` checks completion
   each tick (`pollForResponse`). The loop never blocks — it keeps executing the last
   decision while the next is in flight.
2. **Continuous re-decision loop, not on-demand.** `needsFreshDecision` starts a new
   request the instant there's no in-flight one AND the current decision has completed
   or been interrupted. So a fresh-ish decision is (almost) always on hand — a steady
   ~3 s cadence. It does **not** wait for a player to approach before starting a call.
3. **Proximity-gated send — the trick.** The decision is `say_to_person(target,
   message)` — the LLM pre-decides *what* and *to whom* ~3 s ahead. `maybeSendDecisionChat`
   **holds the message and only emits it when the target is actually near**
   (`visiblePlayerNear`). The slow LLM prepares the line; a cheap per-tick proximity
   check fires it at the moment they walk by.

**Takeaway:** don't start an LLM call reactively when a player walks by (too slow).
Keep a message *ready* (continuous async LLM) and *release* it on a fast proximity
check. Crucially, the same proximity-gate works with **templated messages and no LLM**
as a first cut.

## Implications for cady (when we build chat)

- Read chat from `3000+` objects (label `"chat <text>"`); read who-is-who from the
  gnome/name labels (house index), never the username.
- Run any LLM off the decide path — the SDK's `ThreadedStrategyRunner` is the Python
  equivalent of the villager's curl-multi loop (start → poll → apply), so `decide`
  stays fast.
- Gate the actual `chat` output on a deterministic proximity/timing check, exactly
  like `maybeSendDecisionChat`.
- cady has **no LLM wired up today**; it's fully deterministic. Start with templated
  invites (`"Come to my house at 6, I have plenty!"`) + the proximity gate; add an LLM
  later only if richer conversation is worth the cost/complexity.
