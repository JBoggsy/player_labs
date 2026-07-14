# Vanilla WoW best practices

Vanilla-WoW-specific practices for the improvement loop — layered on top of the
**game-agnostic** [`../best_practices.md`](../best_practices.md) (read that first;
these are additions, not replacements). Distilled from real work in this lab; treat
as defaults and **warn the human if a request would contravene one** before
proceeding. Add to this file as we learn more about *this game's* failure modes.

The graduation pipeline fills this in: candidate lessons accumulate in
[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md), and `/lessons-review` promotes the
ones that recur across sessions into durable practices here. The live, evolving
game knowledge lives in [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md), [`docs/`](docs/),
and the buffer.

## The RFC round metric is clear-then-speed — XP never reorders a round

Optimize for crossing the **full-clear threshold first**, then for clear speed. The
round leaderboard score (`_rfc_leaderboard_score`, `rfc_commissioner.py:184-192`)
is `max(1.0, 1e6 − clear_seconds)` on a full clear and `bosses_defeated /
bosses_total` (always < 1.0) on a partial — so *every* full clear beats *every*
partial, regardless of anything else. XP appears only in the per-slot raw score
and never changes round ordering. Don't spend design effort on XP maximization
until the party clears reliably.

## RFC bosses are discovered by exploration — authored coordinates verify, they don't route

Do not design a clear route as a hardcoded coordinate path. The dungeon files
(e.g. `dungeons/example-ragefire.dungeon.json`) include boss 3D coordinates, but
`docs/bot-world-state.md:124-126` is explicit: boss entry ids define completion
and discovery order only; they do **not** select authored boss coordinates. A
policy must explore the Detour navmesh frontier and fight what engages it — boss
ids exist to verify kills after the fact.

## Wire protocol: take the byte-level facts from the repo's Nim, never guess or "clean up"

The login and world protocol are fully specified in the game repo's Nim sources
(bare filenames below — `srp.nim`, `crypts.nim`, `packets.nim`, `tcp_proxy.py`,
`protocol_oracles.py`, `rfc_episode_audit.py` — live in `coworld-vanilla-wow`,
cloned at `~/coding/coworlds/coworld-vanilla-wow`; this lab's port is
`wowborg/`). Small deviations fail *silently* (disconnects with no useful
error). Verified facts to rely on rather than rediscover:

- **Hosted players connect via the WS byte-tunnel, not raw TCP — and the episode
  audit enforces it.** The hosted path is `WS /tcp/realmd` + `/tcp/world` on the
  same netloc as `COWORLD_PLAYER_WS_URL` (slot/token query auth, raw WoW bytes as
  unframed binary WS frames — `tcp_proxy.py`, populated by `session.py`).
  `rfc_episode_audit.py` **fails the episode** unless every slot×{realmd,world}
  bridge transferred nonzero bytes. Pure-Python players should open `/tcp/world`
  directly and ignore the realm-list world address (skip the reference player's
  localhost listener + `RealmListRewriter`). A raw-TCP fast path exists only when
  `VMANGOS_PUBLIC_*` is injected; otherwise tunnel.
- **Packet headers:** client header is 6 bytes — u16 **big-endian** size (counting
  opcode+body, i.e. 4+bodylen) + u32 **little-endian** opcode; server header is
  4 bytes — u16 BE size (2+bodylen) + u16 LE opcode (`packets.nim
  buildClientPacket`/`tryReadPacket`). Only the header is encrypted; the body is
  plaintext. An off-by-one here is a silent disconnect.
- **Login handshake:** SRP6 per `srp.nim` (little-endian throughout, a = 19 bytes
  with bit 0 set, k = 3, K = SHA1-interleave of the 32-byte S). Header cipher per
  `crypts.nim`: `enc = ((p ^ key[i]) + prev) & 0xff` with separate send/recv
  index+prev over the 40-byte session key, engaging only **after** the plaintext
  `CMSG_AUTH_SESSION` (whose digest = `SHA1(UPPER(acct) || u32 0 || clientSeed ||
  serverSeed || sessionKey)`). `CMSG_PLAYER_LOGIN` is an 8-byte GUID;
  `SMSG_LOGIN_VERIFY_WORLD` (566) means in-world. Send `CMSG_PING` (476) every
  ~30s — VMaNGOS drops silent sockets. `protocol_oracles.py` is a ready Python
  test oracle for these constants.
- **Preserve the SRP6 byte quirks.** `srp.nim` hashes SRP integers as minimal
  little-endian BigInt bytes (not fixed 32-byte fields), and `hashSessionKey`
  big-int-round-trips the 40-byte interleave, which can strip trailing high zero
  bytes. `wowborg/srp6.py` pins both behaviors with deterministic vectors. A
  mathematically "correct-looking" reimplementation that drops these quirks
  breaks realmd login silently — keep the quirks and the pinning tests.

## Pin all WoW research to Vanilla 1.12 — modern wikis and retail values actively mislead

When web-researching game mechanics for this lab, always pin to Vanilla/1.12
(VMaNGOS) and flag retail-era sources. Concrete traps already hit:
warcraft.wiki.gg gives resurrection sickness as 1 min / 50% durability (retail),
but 1.12 is ~10 min at 60 / 25% durability; Season of Mastery XP rates don't
apply to a 1.12 server; and Ragefire Chasm was rebuilt in Cataclysm, so retail
RFC guides are useless here.
