# Design: `wowborg` — a Python Vanilla WoW player + WoW-TCP bridge

**Date:** 2026-07-13
**Status:** approved design; implementation handed to Codex per the plan in
[`../plans/2026-07-13-wowborg-skeleton.md`](../plans/2026-07-13-wowborg-skeleton.md).
**Author:** coding agent (with James)

## Problem & goal

The Vanilla WoW Coworld game has **no Player-SDK bridge** — unlike the other labs' games
(sprite/text protocols the SDK already speaks), all WoW gameplay lives on the real WoW 1.12.1
binary protocol (realmd auth + mangosd world), which the SDK cannot carry. We are building the
first Python player for it, **`wowborg`**, which requires writing our own **WoW-TCP bridge** in
Python (no Nim, no `king_*` subprocess).

**This-session goal (the v1 milestone):** a player that **connects, logs a real character into
the mangosd world, and then idles** (takes no game actions) until the deadline — buildable,
uploadable, and submittable. "Loaded into the game" means a character genuinely **standing in
mangosd** (`SMSG_LOGIN_VERIFY_WORLD` received), not merely holding the Coworld session open.

**Non-goal (deferred):** decoding world state (`SMSG_UPDATE_OBJECT`), movement, combat, or any
actual play. v1 stands and idles. This is deliberately the "make the lower loop boring before
adding intelligence" first layer (King Nimrod's `plan.md` philosophy).

## Why this is the right foundation

The idle-Coworld-session alternative (hold `/player` open, never touch the WoW servers) is a
valid score-0 submission but a **dead end** — the SDK can't reach gameplay, which is all on the
WoW-TCP plane. A Python WoW-TCP client is the **keel** of a real player: login is layer 1; world
decode, movement, and combat stack on top later. Building it now is not a detour.

We are **porting a version-exact, deployed reference** (the repo's Nim client), not inventing a
protocol — every byte is specified in the protocol research (below), and there is a Python
constant oracle (`src/wow_sdk/protocol_oracles.py` in the game repo) to test against.

## What the research established (the load-bearing facts)

Three port-grade specs were extracted from the freshly-pulled game repo
(`~/coding/coworlds/coworld-vanilla-wow` @ `3e1f1b655`). Full byte-level detail lives in
[`../vanilla-wow-protocol.md`](../vanilla-wow-protocol.md); the design-critical facts:

### Transport — **WS byte-tunnel, not raw TCP** (decisive)

- The `/player` session handshake **always** advertises `tcp_proxies`: `WS /tcp/realmd` and
  `WS /tcp/world`, on the **same host:port** as `COWORLD_PLAYER_WS_URL`, authed by the **same
  `slot` + `token`** query params. Each binary WS frame's payload **is raw WoW TCP bytes,
  unframed** (`tcp_proxy.py`).
- The hosted episode **audit fails the episode unless every slot × {realmd, world} tunnel
  transferred nonzero bytes** (`rfc_episode_audit.py:129-153`). So the tunnel is not just the
  fallback — it is the **expected** hosted path, and going raw-TCP would fail the audit.
- **v1 is tunnel-only.** We skip the reference player's localhost-listener + `RealmListRewriter`
  machinery entirely (that exists only so unmodified TCP clients can be pointed at localhost);
  a pure-Python client **ignores the realm-list world address and opens `/tcp/world`
  directly**. (A raw-TCP fast-path is a possible later optimization; not in v1.)

### WoW login — fully specified, byte-for-byte (do not guess)

- **realmd (SRP6):** `AUTH_LOGON_CHALLENGE` → `AUTH_LOGON_PROOF` → `REALM_LIST`. SRP6 is
  little-endian throughout, `a` = 19 random bytes with bit0 set, `k=3`, session key `K` = the
  SHA1-interleave of the 32-byte `S`, `M1 = SHA1((H(N)^H(g)) || H(UPPER(user)) || salt || A || B
  || K)`. Username **and** password uppercased. The proof packet's `crc_hash` is a real
  `SHA1(A_32le || platform_integrity_hash)` (build-5875 Win/x86 hash is a known constant).
- **world (mangosd):** `SMSG_AUTH_CHALLENGE(492)` gives a u32 seed → we send **plaintext**
  `CMSG_AUTH_SESSION(493)` = `u32 build(5875) || u32 0 || CString UPPER(account) || u32
  clientSeed || 20-byte digest`, where `digest = SHA1(UPPER(account) || u32 0 || clientSeed ||
  serverSeed || sessionKey)` → **enable header encryption immediately after** → read
  `SMSG_AUTH_RESPONSE(494)` → `CMSG_CHAR_ENUM(55)` → `SMSG_CHAR_ENUM(59)` (parse to find the
  seeded character's 8-byte GUID by name) → `CMSG_PLAYER_LOGIN(61)` (8-byte GUID) → wait for
  **`SMSG_LOGIN_VERIFY_WORLD(566)` = "standing in the world"** → send `MSG_MOVE_WORLDPORT_ACK
  (220)` then `CMSG_SET_ACTIVE_MOVER(618)` (8-byte GUID).
- **Header framing:** client header = 6 bytes (`u16 BE size` counting opcode+body, + `u32 LE
  opcode`); server header = 4 bytes (`u16 BE size` counting opcode+body, + `u16 LE opcode`).
  **Only the header is encrypted; the body is plaintext.**
- **Header cipher (engages after the plaintext AUTH_SESSION):** send:
  `enc[i] = ((plain[i] ^ key[sendIdx]) + sendPrev) & 0xFF; sendIdx = (sendIdx+1) % 40; sendPrev
  = enc[i]`. recv is the exact inverse: `plain[i] = ((enc[i] + 256 - recvPrev) & 0xFF) ^
  key[recvIdx]; recvIdx = (recvIdx+1) % 40; recvPrev = enc[i]`. Send and recv keep **separate**
  index/prev counters over the shared 40-byte session key.
- **Keepalive (required):** VMaNGOS drops silent sockets — send `CMSG_PING(476)` = `u32 seq
  (from 1) || u32 latency(0)` **every 30 s**. This is what makes "idle" survive to the deadline.

### The Coworld session plane (SDK-reusable)

- The `/player` WS is control-only: `wow_session` handshake, then `ping`/`pong`, `done`,
  `final`. `players.player_sdk.run_message_bridge` owns exactly this transport (connect,
  iterate, exit-0-on-close). We *could* ride it, but v1's control loop is simple enough (and
  must run concurrently with the two WoW tunnels) that owning a small async supervisor is
  cleaner. We reuse the SDK's `env_ws_url()`, `TraceOutputs`, and the exit-0 close contract.

## Architecture

`wowborg` is a Python asyncio program. Three concurrent WebSocket connections to the **same
host** (from `COWORLD_PLAYER_WS_URL`), all authed by the same `slot`+`token`:

```
                        COWORLD_PLAYER_WS_URL host
   ┌───────────────────────────┬───────────────────────────┬────────────────────────┐
   │  WS /player               │  WS /tcp/realmd            │  WS /tcp/world          │
   │  (Coworld control plane)  │  (raw realmd bytes)        │  (raw mangosd bytes)    │
   └───────────┬───────────────┴─────────────┬─────────────┴───────────┬────────────┘
               │                              │                         │
        session supervisor            realmd client (SRP6)       world client (login+idle)
        - recv wow_session       ───▶ - challenge/proof     ──K──▶ - AUTH_SESSION (K digest)
        - ping/pong / hold             - REALM_LIST                - header crypt on
        - on world "in-world"          - yields session key K       - CHAR_ENUM → pick GUID
          → keep session alive         + world host:port            - PLAYER_LOGIN
        - on deadline/close: done        (ignored; use tunnel)      - wait LOGIN_VERIFY_WORLD
                                                                    - worldport ack + set mover
                                                                    - CMSG_PING every 30s (idle)
```

**Flow:** connect `/player` → read `wow_session` (creds, account name/password, character_name,
slot/token already known) → open `/tcp/realmd` tunnel, run SRP6, obtain the **40-byte session
key `K`** → open `/tcp/world` tunnel, run the world handshake using `K` (auth digest + header
cipher) → select the seeded `character_name` from the char enum → `PLAYER_LOGIN` → on
`SMSG_LOGIN_VERIFY_WORLD`, we are **in the world**; log it, send worldport-ack + set-active-mover
→ enter the **idle loop**: send `CMSG_PING` every 30 s, drain/ignore inbound world packets, do
nothing else → when the Coworld `/player` session ends (deadline/`final`), send `done` and exit 0.

### Package layout (mirrors `cady`/`crewborg`, WoW-specific modules)

```
vanilla_wow_lab/wowborg/
  __init__.py, __main__.py          package + `python -m wowborg` entry
  main.py                           entrypoint: env_ws_url, TraceOutputs, asyncio.run(run())
  config.py                         tunable knobs (ping interval, timeouts, client seed, logging)
  session.py                        Coworld /player control-plane supervisor
  tunnel.py                         WS-byte-tunnel transport: a duplex bytes channel over a WS
  wire.py                           byte read/write primitives (LE/BE ints, CString, fourcc)
  srp6.py                           the SRP6 math (port of srp.nim) — pure, unit-testable
  realmd.py                         realmd client: challenge/proof/realm-list → session key K
  crypt.py                          the world header cipher (port of crypts.nim) — pure
  world.py                          world client: auth/char-enum/login → in-world → idle
  opcodes.py                        opcode + command constants (from protocol_oracles.py)
  run.py                            top-level orchestration: wire the three planes together
  Dockerfile, .dockerignore         pure-Python image (players[bedrock] from pinned tarball)
  README.md                         internal doc (layout, build/test/run, protocol pointers)
  VERSION_LOG.md                    per-version change history
  tests/                            unit tests for srp6/crypt/wire against protocol_oracles
```

**Design-for-testability:** `srp6.py`, `crypt.py`, and `wire.py` are **pure functions** with no
I/O — they are the correctness-critical parts (a wrong byte = silent disconnect), so they get
real unit tests validated against known vectors + the game repo's `protocol_oracles.py` constants.
Everything with I/O (`tunnel`, `realmd`, `world`, `session`) is thin orchestration over them.

### Key interfaces

- **`tunnel.py`** — `class WowTunnel`: opens `WS <host>/tcp/<service>?slot=&token=`, exposes
  `async recv_exact(n) -> bytes` (accumulates across binary frames — WoW packets don't align to
  WS frames) and `async send(data: bytes)`. This is the raw-bytes duplex the realmd/world clients
  read/write against, indistinguishable from a TCP socket to them.
- **`srp6.py`** — `compute_proof(username, password, B, g, N, salt) -> SrpResult(A, M1, K)`;
  pure. Plus the `crc_hash` helper (build-5875 platform integrity hash).
- **`realmd.py`** — `async def authenticate(tunnel, username, password) -> bytes` (returns `K`),
  running challenge→proof→realm-list. Realm-list world address is parsed but **ignored** (we use
  the `/tcp/world` tunnel).
- **`crypt.py`** — `class HeaderCrypt(key: bytes)` with `encrypt_send(header)` / `decrypt_recv
  (header)`, separate send/recv state; pure byte transforms.
- **`world.py`** — `async def login_and_idle(tunnel, account, character_name, session_key,
  *, ping_interval, deadline_signal)`; runs the world handshake to `LOGIN_VERIFY_WORLD`, then the
  ping-only idle loop until told to stop.
- **`session.py`** — owns `/player`: reads `wow_session`, answers `ping`, and on session end
  sends `done` and signals the world idle loop to stop. Honors the SDK exit-0-on-close contract.

### Concurrency & lifecycle

`run.py` uses `asyncio` with a small task group: (1) the session supervisor, (2) the world idle
loop's ping timer. The realmd + world *handshakes* run sequentially at startup (realmd yields `K`,
then world uses it); once in-world, the ping timer and the session supervisor run concurrently
until the session ends. On any unclean close we exit 0 (Coworld contract — a nonzero exit scores
the episode failed). `websockets` library keepalive is **disabled** (`ping_interval=None`) — our
own `CMSG_PING` is the liveness signal, mirroring cady's lesson about library pings tearing down
a busy connection.

## Risks & mitigations

1. **Header-cipher / digest exactness** (the classic silent breaker). *Mitigation:* pure
   `crypt.py`/`srp6.py` with unit tests; the CMSG_AUTH_SESSION digest and cipher formulas are
   quoted byte-for-byte from the Nim in the protocol doc. The hosted eval is the integration test.
2. **Tunnel framing** — WoW packets span/subdivide WS frames arbitrarily. *Mitigation:*
   `WowTunnel.recv_exact` buffers across frames; never assume one frame = one packet.
3. **Char enum parsing misalignment** — the per-character record has a mandatory trailing
   `20×(u32+u8)` equipment block; miss it and the next record misaligns. *Mitigation:* the record
   layout is fully specified; we only need GUID+name but must skip the whole record correctly.
4. **Keepalive gap** — miss the 30 s ping and VMaNGOS drops us, failing the "stayed in world"
   goal silently. *Mitigation:* ping timer is a first-class task; interval in `config.py` set
   comfortably under 30 s (e.g. 15 s).
5. **Transport assumption wrong** (raw TCP after all). *Mitigation:* the audit evidence is
   strong that tunnel is required; if a hosted eval shows otherwise we add the raw-TCP fast-path.
   The `WowTunnel`/socket seam is designed so swapping transports is localized.
6. **Nim image expectation** — the game's default player Dockerfile builds Nim, but **our** image
   is pure Python (we are the SDK-style player, not the reference). No Nim toolchain needed.

## Build / upload / submit

- **Image:** pure-Python, mirroring `cady/Dockerfile` — `python:3.12-slim`, `pip install
  players[bedrock] @ <pinned coworld-tools tarball>`, `COPY . /app/wowborg`, `CMD ["python", "-m",
  "wowborg"]`. No `versions.env` needed (no Nim compiled against a pinned game commit; we only
  *read* the game repo as a protocol reference, we don't link against it).
- **Upload/submit:** the game-agnostic root skills (`build-and-upload`, `coworld-policy-lifecycle`).
  Per the readiness gap, the game may not have a live scored league yet — verify before submitting;
  an experience request against whatever eval path exists is the integration test for "did it load
  into the world and idle."

## Validation

- **Unit:** `srp6`, `crypt`, `wire` against `protocol_oracles.py` constants + known vectors
  (`uv run pytest vanilla_wow_lab/wowborg/tests`).
- **Integration (the real test):** build → upload → experience request; success =
  `SMSG_LOGIN_VERIFY_WORLD` observed in our logs and the episode completes without a
  `player_error` / failed audit; a completed score of 0 is the *expected* v1 outcome (loaded and
  idled, no XP). Detect our own failures via episode status, not score.

## Handoff

Implementation is decomposed into ordered steps in
[`../plans/2026-07-13-wowborg-skeleton.md`](../plans/2026-07-13-wowborg-skeleton.md) and handed to
Codex (per the human's instruction) to plan and execute each step, against the byte-level spec in
[`../vanilla-wow-protocol.md`](../vanilla-wow-protocol.md).
