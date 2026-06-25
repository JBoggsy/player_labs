# player_labs — deferred tasks

Tasks intentionally parked to handle later. Add items here when you defer something
mid-session; check them back at the start of focused work.

## Open

- **Move the Coworld websocket transport/bridge into the player SDK** (flagged by James,
  2026-06-24). Today each player carries its own transport: crewborg's lives in
  `crewrift_lab/crewrift/crewborg/coworld/policy_player.py` (`run_bridge` — connects to the
  engine `/player` ws, drives the per-tick loop), and the SDK's `message_bridge.py` /
  `cogweb_bridge.py` are separate, neither with reconnect. The Coworld transport (Sprite-v1
  binary ws, the runner's `COWORLD_PLAYER_WS_URL` contract, the abrupt-close=game-over
  semantics, and now reconnect) is a *shared* concern: it should be ONE importable module in
  the multiplayer SDK that any Coworld-style player builds on, so future players inherit a
  transport we know works. Scope: factor crewborg's `run_bridge` + the aggressive-reconnect
  logic (added 2026-06-24, see below) into `players.player_sdk`, leaving the game-specific
  scene decode / action encode as injected callbacks. Deferred because it's a cross-cutting
  SDK refactor (the SDK is a pinned git dep — needs an upstream change + relock), distinct
  from the immediate crewborg reconnect fix. The reconnect code added to crewborg now is the
  reference implementation to lift.

- **Investigate turn-end signalling added to Crewrift for game speed** (flagged by James,
  2026-06-24). Crewrift has reportedly added a turn-end / ready signal (a way for a player
  to declare it's done acting this tick) to speed games up. Look into what it is in the
  game source (`~/coding/coworlds/coworld-crewrift`, currently at `42fed21` for arena 0.1.54
  — check newer master), whether crewborg should emit it, and the expected speedup / any
  contract change to the Sprite-v1 transport. Not yet scoped.

- **LLM-based meeting chat for crewborg** (flagged by James, 2026-06-25; "for later/
  tomorrow"). Today crewborg's meeting chat is templated/cue-filled (`CHAT_NLP` produces
  ~62 distinct strings like "purple sus: they were tailing me"). Andre's `truecrew` bots
  use genuine **LLM-generated** chat (Bedrock) — 81/83 imposter and 378/383 crew messages
  are *unique*, natural-language, and contextual ("Body in Science Bay. Red called it fast
  - suspicious timing."; "Blue is super sus for following so much."). The goal: add LLM
  chat **in addition to** the current templated path (not replacing it), for both roles —
  imposter deflection/investigator-posing and crew behavioral-cue accusations. Bedrock is
  verified working from the tournament pod (see cue_n_woo_lab notes). Pairs with the
  near-term **crew-side "suss the aggressive imposter"** work (cite the following/proximity
  tell, the way Andre's crew does). Not yet scoped.

## Done

_None yet._
