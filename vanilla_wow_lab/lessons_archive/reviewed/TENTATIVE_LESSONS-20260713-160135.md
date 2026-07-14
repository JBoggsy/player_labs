# Vanilla WoW tentative lessons — session buffer

**Session started:** (seeded at lab creation; the SessionStart hook stamps this on the next
session). This is THIS SESSION's lesson buffer. Write candidate lessons here **as you go** —
eagerly and noisily; most will be noise and that's fine. At the next session start, a hook
archives this file automatically to [`lessons_archive/`](lessons_archive/) and creates a fresh
one — nothing you write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`vanilla_wow_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Vanilla-WoW-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### 7200 in the WoW game repo is the boss-respawn timer, NOT the episode deadline
Evidence: `DUNGEON_LAB_RESPAWN_SECONDS = 7200` (`dungeon.py:1076`) keeps a killed boss
readable-as-dead via the `creature_respawn` table; the episode's real wall-clock budget is
`max_ticks/tick_rate` (RFC 10000/0.1). `docs/bot-world-state.md:136-137` loosely calls 7200
"the single time-based termination boundary" for exploration *control*, which misled the
first-pass understanding. Be precise about which "time boundary" you mean when writing docs.

### The RFC round metric is clear-then-speed; XP does not change round ordering
Evidence: `_rfc_leaderboard_score` (`rfc_commissioner.py:184-192`) = full clear →
`max(1.0, 1e6 − clear_seconds)`, partial → `bosses_defeated/bosses_total` (<1.0). Every clear
beats every partial; XP only appears in the per-slot raw score, not the round score. So a
player's first job is crossing the full-clear threshold, not maximizing XP.

### Vanilla WoW is the odd lab out: Nim packet-level player, not a Python SDK policy
Evidence: unlike crewborg/cady/mentalist (Python `players.player_sdk` on sprite/text), the
submittable player is headless King Nimrod compiled Nim `-d:noGui` (`player/Dockerfile`),
connecting via a WS→TCP bridge (`wsproxy`), obeying "sent is not accepted." Any player we build
needs a Nim build path + (if forking the engine) a pinned game commit — heavier than a prompt swap.

### Game not live yet — lab loop is blocked; verify readiness before assuming a league exists
Evidence: `vanilla_wow:0.1.4.post8` passed executable cert + local RFC smoke but README badge is
"coworld verify: not ready"; the badge gates on a retained hosted round + XP-request episode that
haven't been created (`docs/coworld-readiness.md`). Only a persistent *practice* realm exists (no
scored league). Always `git pull` the game repo + re-read readiness before claiming the loop can run.

### RFC bosses are DISCOVERED by graph exploration — coordinates are verification-only, not a path
Evidence: `dungeons/example-ragefire.dungeon.json` gives boss 3D coords, but
`docs/bot-world-state.md:124-126` is emphatic: "Boss entry ids define completion and discovery
order only. They do not select authored boss coordinates." A policy must explore the Detour
navmesh frontier and fight what engages it; boss ids verify a kill. So RFC strategy CANNOT
hardcode a coordinate path — this constrains any clear-route design.

### Vanilla WoW facts are version-sensitive: use 1.12 values, not modern-wiki/retail or SoM
Evidence: warcraft.wiki.gg lists resurrection sickness as 1min/50% durability (retail 10.0), but
Vanilla 1.12 = ~10min-at-60 / 25% durability. Season of Mastery raised leveling XP rates — don't
apply to a 1.12 VMaNGOS server. RFC was rebuilt in Cataclysm — ignore retail RFC entirely. When
web-researching WoW for this lab, always pin to Vanilla/1.12 and flag where sources are retail-era.

### Engine already encodes the survival math; a policy tunes thresholds + supplies coordination
Evidence: bundled leveling policy caps grind targets at level-1, skips mobs with a hostile within
18yd (add radius), heals at 65% combat/90% out, gates pulls on 85% mana, models corpse-run vs
spirit-healer (creature 6491, aura 15007) — all in `player/bots/{leveling/planner.nim,rotations.nim}`.
So the leveling/combat competence is largely present; the highest-leverage policy work is RFC PARTY
COORDINATION (threat-ramp delay, focus-fire, pull sizing, boss positioning) which the engine does NOT supply.

### Split doc set: narrative "contract" + exhaustive "reference" is the right shape for a complex protocol
Evidence: player-contract.md (narrative "how to think about being a player") + protocol.md
(field-level spec: every message, 64-byte byte layout, full TelemetrySnapshot, CWREPLAY format)
serve different readers without bloating either; cross-link both ways. Mirrors crewrift's
gameplay-vs-protocol split. When a protocol is complex, don't cram the spec into the narrative doc.

### Extract exact schemas via a dedicated source-reading agent before writing a reference doc
Evidence: the protocol reference needed verbatim field names/types/byte offsets from
protocol.py/actions.nim/tensor_frame.nim. A focused Explore agent tasked to extract EXACT
field-level detail (not paraphrase) with file:line citations produced a spec-grade dump. It
surfaced things the narrative doc had only summarized (the WS /tcp tunnel, the full telemetry
schema, the action-record byte layout, a Python-vs-Nim "successful movement kinds" asymmetry).

### Unicode chars in doc prose break Edit old_string matching — anchor on plain ASCII
Evidence: multiple Edit calls failed to match strings containing arrow glyphs even when visually
identical. Fix: choose an old_string anchor that avoids the unicode char, or re-Read and copy exact bytes.

### Hosted WoW players connect via the WS byte-tunnel, NOT raw TCP — and the audit enforces it
Evidence: session.py always populates `tcp_proxies`; the hosted path is `WS /tcp/realmd` + `/tcp/world` on the same netloc as COWORLD_PLAYER_WS_URL, slot/token query auth, raw WoW bytes as UNFRAMED binary WS frames (tcp_proxy.py). rfc_episode_audit.py FAILS the episode unless every slot×{realmd,world} bridge transferred nonzero bytes. Pure-Python players skip the reference player's localhost-listener + RealmListRewriter entirely and open /tcp/world directly (ignore the realm-list world address). Optional raw-TCP fast-path if VMANGOS_PUBLIC_* is injected, else fall back to tunnel.

### The WoW login port is fully specified byte-for-byte from the repo Nim — do NOT guess
Evidence: srp.nim (SRP6: LE everywhere, a=19 bytes bit0 set, k=3, K=SHA1-interleave of 32-byte S, M1 formula), protocol.nim (realmd packets), crypts.nim (header cipher: enc=((p^key[i])+prev)&0xff, separate send/recv index+prev, 40-byte session key, engages AFTER plaintext CMSG_AUTH_SESSION), world_sessions.nim/packets.nim (world handshake, CMSG_AUTH_SESSION digest = SHA1(UPPER(acct)||u32 0||clientSeed||serverSeed||sessionKey), CMSG_PLAYER_LOGIN=8-byte GUID, SMSG_LOGIN_VERIFY_WORLD=566 means in-world). Keepalive = CMSG_PING(476) every 30s (VMaNGOS drops silent sockets). protocol_oracles.py is a ready Python test oracle for the constants.

### Client header 6B (u16 BE size + u32 LE opcode); server header 4B (u16 BE size + u16 LE opcode)
Evidence: packets.nim buildClientPacket/tryReadPacket. Client size = 4+bodylen (counts opcode+body); server size = 2+bodylen. Only the header is encrypted; body is plaintext. Off-by-one here = silent disconnect.

### SRP6 port has historical Nim byte quirks; preserve them in tests
Evidence: `srp.nim` hashes SRP integers using minimal little-endian BigInt bytes, not fixed
32-byte fields, and `hashSessionKey` big-int-round-trips the 40-byte interleave, which can strip
trailing high zero bytes. `wowborg/srp6.py` pins these behaviors with deterministic vectors. A
"cleaned up" SRP implementation could silently break realmd login even if the formula looks right.
