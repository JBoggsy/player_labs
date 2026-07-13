# Plan: `wowborg` v1 — connect, log into world, idle

**Design:** [`../designs/wowborg-player-design.md`](../designs/wowborg-player-design.md)
**Protocol reference (byte-level, authoritative):** [`../vanilla-wow-protocol.md`](../vanilla-wow-protocol.md)
**Game repo (read-only reference):** `~/coding/coworlds/coworld-vanilla-wow` @ `3e1f1b655`

**Goal:** a pure-Python Player-SDK-style player that connects to Coworld, logs a real character
into the mangosd world (reaches `SMSG_LOGIN_VERIFY_WORLD`), then idles (only `CMSG_PING`
keepalive) until the deadline. Buildable, uploadable, submittable. **No Nim, no subprocess.**

**Execution model:** each step below is a self-contained unit with explicit acceptance criteria.
Codex plans + implements each step in order. Steps 1–6 are pure/unit-testable (no network); steps
7–10 wire in I/O and the image. **Do NOT skip the unit tests on the pure crypto/wire steps** — a
wrong byte there is a silent disconnect that costs an entire eval round to diagnose.

Reference Nim files (in the game repo) to port from, per step, are named inline. The Python
constant oracle to assert against is `src/wow_sdk/protocol_oracles.py`.

---

## Step 0 — Package skeleton

Create `vanilla_wow_lab/wowborg/` with: `__init__.py`, `__main__.py` (`from wowborg.main import
main`), empty module stubs (`main.py`, `config.py`, `wire.py`, `srp6.py`, `crypt.py`,
`opcodes.py`, `realmd.py`, `world.py`, `tunnel.py`, `session.py`, `run.py`), `tests/`, `README.md`
(layout + build/test/run commands), `VERSION_LOG.md` (v1 entry stub), `Dockerfile`,
`.dockerignore`. Mirror `heartleaf_lab/cady/` conventions.

**Acceptance:** `uv run python -c "import wowborg"` works from the repo (add to `pyproject.toml`
dev/workspace as the other lab players are, or ensure `PYTHONPATH` import parity); `python -m
wowborg` reaches a `main()` that currently just prints a not-implemented notice and exits 0.

## Step 1 — `opcodes.py`: constants

Port the opcode/command constants from `protocol_oracles.py` (auth: `AuthProtocolVersion=8`,
`ClientBuild=5875`, `CmdAuthLogonChallenge=0x00`, `CmdAuthLogonProof=0x01`, `CmdRealmList=0x10`;
world: `SMSG_AUTH_CHALLENGE=492`, `CMSG_AUTH_SESSION=493`, `SMSG_AUTH_RESPONSE=494`,
`CMSG_CHAR_ENUM=55`, `SMSG_CHAR_ENUM=59`, `CMSG_PLAYER_LOGIN=61`, `SMSG_LOGIN_VERIFY_WORLD=566`,
`SMSG_CHARACTER_LOGIN_FAILED=65`, `MSG_MOVE_WORLDPORT_ACK=220`, `CMSG_SET_ACTIVE_MOVER=618`,
`CMSG_PING=476`, `SMSG_PONG=477`) and the SRP sizes (`SRP_NUMBER=32`, `SRP_DIGEST=20`,
`SRP_SESSION=40`, `SRP_MULTIPLIER=3`, `SRP_PRIVATE=19`).

**Acceptance:** a unit test asserts each constant equals the value `protocol_oracles.py` expects
(copy the expected values into the test; do not import the game repo at runtime).

## Step 2 — `wire.py`: byte primitives

Reader/writer for: `u8`, `u16 LE`, `u16 BE`, `u32 LE`, `u32 BE`, `u64 LE`, `f32 LE`, C-string
(NUL-terminated ASCII), fixed ASCII (zero-padded), reversed-fourcc (byte-reversed, zero-padded to
4). Match `player/game_client/packets/wire.nim` semantics exactly.

**Acceptance:** round-trip unit tests; explicit tests for reversed-fourcc (`"x86"` → `36 38 78
00`, `"enUS"` → `53 55 6E 65`) and BE vs LE u16.

## Step 3 — `srp6.py`: the SRP6 auth math (pure)

Port `player/game_client/srp.nim` exactly (see protocol doc §SRP6). Implement:
`compute_proof(username, password, *, B, g, N, salt, a=<random 19 bytes, bit0 set>) ->
{A: 32-byte LE, M1: 20 bytes, K: 40 bytes}`, plus `crc_hash(A_32le, platform="Win/x86") -> 20
bytes` (build-5875 Win/x86 integrity hash constant). Little-endian throughout; `k=3`; `x =
int.from_bytes(SHA1(salt_le || SHA1(b"USER:PASS")), "little")`; `S = pow((B - 3v) % N, a + u*x,
N)`; `K` = SHA1-interleave of the 32-byte `S` (with the trailing-zero-strip round-trip quirk
matched to the Nim); `M1 = SHA1((H(N)^H(g)) || H(UPPER(user)) || salt || A || B || K)`. Uppercase
username **and** password.

**Acceptance:** unit tests: (a) a deterministic vector — fixed `a`, `N`, `g`, `salt`, `B`,
credentials → assert `A`, `M1`, `K` byte-for-byte (compute the expected once against the Nim
semantics and pin it); (b) `crc_hash` matches the known build-5875 constant path; (c) round-trip
`x`/`v` sanity. This is the highest-risk module — test it hard.

## Step 4 — `crypt.py`: world header cipher (pure)

Port `player/game_client/crypts.nim` exactly (protocol doc §header crypt). `class HeaderCrypt`
init with the 40-byte session key; `encrypt_send(buf: bytearray)` and `decrypt_recv(buf:
bytearray)` mutate in place; **separate** `send_index/send_prev` and `recv_index/recv_prev`;
index wraps mod `len(key)`. Formulas exactly:
`enc = ((p ^ key[i]) + prev) & 0xFF`, then `i=(i+1)%40`, `prev=enc`; decrypt is the inverse
`p = ((enc + 256 - prev) & 0xFF) ^ key[i]`, then `i=(i+1)%40`, `prev=enc`.

**Acceptance:** unit test: `decrypt_recv(encrypt_send(x))` is **not** identity (separate state) —
instead assert against a hand-computed vector for a few bytes with a known key, and assert that a
header encrypted by a `HeaderCrypt(k)` send side decrypts correctly on a *matching* recv side
seeded the same way (simulating the two endpoints). Pin exact expected bytes.

## Step 5 — packet framing helpers (in `wire.py` or a small `frame.py`)

`build_client_packet(opcode: int, body: bytes, crypt, encrypted: bool) -> bytes`: header = `u16
BE (4 + len(body))` + `u32 LE opcode`; encrypt the 6-byte header if `encrypted`; append plaintext
body. `read_server_packet(buf, crypt, encrypted)`: decrypt the 4-byte header if `encrypted`, parse
`u16 BE size` + `u16 LE opcode`, `body_len = size - 2`. Match `packets.nim`
`buildClientPacket`/`tryReadPacket`.

**Acceptance:** unit tests for both directions with encryption on and off; assert the size-field
arithmetic (client counts opcode+body; server `body_len = size - 2`).

## Step 6 — `tunnel.py`: WS byte-tunnel transport

`class WowTunnel`: `async connect(base_ws_url, service, slot, token)` opens `WS
<host>/tcp/<service>?slot=&token=` (derive host/scheme from `base_ws_url`, mapping `ws→ws`,
`wss→wss`); `async send(data: bytes)` sends one binary frame; `async recv_exact(n) -> bytes`
accumulates payloads across binary frames into an internal buffer and returns exactly `n` bytes
(WoW packets do **not** align to WS frames). Disable library keepalive (`ping_interval=None`).
Clean close → raise a typed EOF the callers treat as game-over.

**Acceptance:** a unit test with a fake in-memory websocket (feed multi-frame byte streams; assert
`recv_exact` reassembles across frame boundaries and blocks correctly). No live network needed.

## Step 7 — `realmd.py`: the realmd leg

`async def authenticate(tunnel, username, password) -> bytes` (returns `K`): build + send
`AUTH_LOGON_CHALLENGE`, read the challenge (extract `B, g, N, salt`), run `srp6.compute_proof`,
send `AUTH_LOGON_PROOF` (A ‖ M1 ‖ crc ‖ 0 ‖ 0), read the proof response (gate on status bytes;
M2 ignored), send `REALM_LIST`, read the realm list (parse but **ignore** the world address).
Use `wire.py` for all byte layouts (protocol doc §realmd tables).

**Acceptance:** a unit test driving `authenticate` against a **scripted fake tunnel** that replays
a canned server challenge/proof/realm-list byte sequence; assert the client emits the correct
challenge + proof bytes and returns the expected `K`. (Integration against the real server is the
eval.)

## Step 8 — `world.py`: world handshake → in-world → idle

`async def login_and_idle(tunnel, account, character_name, session_key, *, config,
stop_event)`: read `SMSG_AUTH_CHALLENGE` (u32 seed) → send **plaintext** `CMSG_AUTH_SESSION`
(build, 0, CString UPPER(account), clientSeed, 20-byte digest = `SHA1(UPPER(account) || u32 0 ||
clientSeed || serverSeed || session_key)`) → **turn header crypt on** (`HeaderCrypt(session_key)`)
→ read `SMSG_AUTH_RESPONSE` (gate on OK) → send `CMSG_CHAR_ENUM` → read `SMSG_CHAR_ENUM`, parse
records (skip the full per-record layout incl. `20×(u32+u8)` equipment) to find the GUID whose
name case-insensitively equals `character_name` → send `CMSG_PLAYER_LOGIN` (8-byte GUID) → read
packets until `SMSG_LOGIN_VERIFY_WORLD(566)` (success → log "in world" + spawn position) or
`SMSG_CHARACTER_LOGIN_FAILED(65)` (raise) → send `MSG_MOVE_WORLDPORT_ACK` + `CMSG_SET_ACTIVE_MOVER`
(GUID) → **idle loop:** every `config.ping_interval_s` (default 15) send `CMSG_PING` (`u32 seq
from 1 || u32 0`); continuously drain+discard inbound packets; exit when `stop_event` is set.

**Acceptance:** a unit test driving the handshake against a scripted fake tunnel through
`LOGIN_VERIFY_WORLD` (assert the emitted `CMSG_AUTH_SESSION` digest bytes for a fixed
seed/key/account, and that char-enum parsing selects the right GUID). Assert the ping loop emits a
correctly-framed `CMSG_PING` on the timer (use a fake clock / short interval).

## Step 9 — `session.py` + `run.py`: Coworld control plane + orchestration

`session.py`: connect `COWORLD_PLAYER_WS_URL` (from `env_ws_url()`), read the `wow_session` JSON
(capture `account_username`, `account_password`, `character_name`, `slot`; `token` from the URL
query), answer `ping`→`pong`, detect session end (`final` / close / deadline) and set a shared
`stop_event`; on stop send `done` (`success=true`, detail e.g. "loaded into world and idled").
`run.py`: orchestrate — connect `/player`, read session, open `/tcp/realmd` → `authenticate` →
`K`, open `/tcp/world` → `login_and_idle(..., stop_event)`, run the session supervisor + world idle
concurrently (asyncio task group); exit 0 on any close (Coworld contract).

**Acceptance:** an integration-style unit test with all three planes backed by scripted fake
websockets: assert the full happy path runs end-to-end (session read → realmd K → world login →
ping loop → stop on `final` → `done` sent → exit 0). No real network.

## Step 10 — `main.py` + `Dockerfile`: buildable artifact

`main.py`: `env_ws_url()` → `TraceOutputs.from_env(prefix="WOWBORG", default="jsonl@artifact")`
with stderr fallback (mirror `cady/main.py`) → `asyncio.run(run.run(url, trace_outputs=outputs))`.
`Dockerfile`: pure-Python, copy `cady/Dockerfile` pattern (`python:3.12-slim`, `pip install
players[bedrock] @ <pinned coworld-tools tarball>`, `COPY . /app/wowborg`, `CMD ["python", "-m",
"wowborg"]`); pin `PLAYERS_SDK_REF` to the same SHA the other labs use. `.dockerignore` excludes
tests/caches.

**Acceptance:** `uv run pytest vanilla_wow_lab/wowborg/tests` passes; `docker build
--platform=linux/amd64 -t wowborg vanilla_wow_lab/wowborg` succeeds; `python -m wowborg` with a
dummy `COWORLD_PLAYER_WS_URL` fails gracefully (can't connect) rather than crashing on import.

---

## After the plan (loop, not part of Codex's steps)

1. **Build + upload** `wowborg` as a policy version (`build-and-upload` skill).
2. **Experience request** against the eval path (verify a live scored surface exists first per the
   readiness gap). **Success = `SMSG_LOGIN_VERIFY_WORLD` in our logs + episode completes clean +
   the `/tcp` bridges show nonzero bytes** (the audit's requirement). Expected score: 0 (idle).
3. **Diagnose** via episode status + our `WOWBORG` trace, not score. If it can't connect/login,
   that's the debugging target for the next iteration (the hosted eval is the test — don't
   pre-verify with local runs beyond the unit suite).
4. Record the version→outcome in `VERSION_LOG.md` and update `WORKING_CONTEXT.md`.

## Guardrails for Codex

- **Port, don't invent.** Every byte layout is specified in `../vanilla-wow-protocol.md` and the
  cited Nim. When in doubt, read the Nim file named in the step — do not guess a field size or
  endianness.
- **Pure modules stay pure** (`srp6`, `crypt`, `wire`, framing) — no I/O, fully unit-tested.
- **Little-endian everywhere** in SRP/WoW numbers except the two `u16 BE` size fields in headers.
- **Exit 0 on any close** (Coworld scores a nonzero exit as failure).
- **Our own `CMSG_PING` is the keepalive**; disable the `websockets` library ping.
- Keep tunable values (ping interval, timeouts, client seed, log verbosity) in `config.py`,
  separate from logic, so the next iteration is attributable.
