# CTF tentative lessons — session buffer

**Session started:** 2026-07-14 10:39. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### CTF movement clamps velocity PER AXIS — use Chebyshev, not Euclidean, for reachability

Evidence: sim.nim clamps velX and velY independently to MaxSpeed(704)/MotionScale(256)
= 2.75 px/tick each, so diagonal movement reaches ~3.9 px/tick. Any "could the enemy
have reached X since we saw them" gate (track association, danger diffusion) must use
max(|dx|,|dy|), not hypot — Euclidean undershoots diagonals by sqrt(2) and would
fragment tracks of diagonal movers into spurious new tracks.

### Trace new belief structures in the same snapshot event the warehouse already ingests

Evidence: adding tracks + a danger heatmap to the existing `snapshot` payload (decide.py
`_payload`) needed zero warehouse changes — `event_warehouse.py` stores `data` as-is per
event row. Downsample grids before tracing (full 155x83 float grid ≈ 13k values; block-max
4x + 0..255 quantization ≈ 3.6 KB inc. tracks) and prefer block-MAX over mean for danger:
the pessimistic read is the honest one after quantization.

### Sprite-v1 has a designed-in replay overlay channel (0x86 debug sprites) but NOTHING implements it end-to-end yet

Evidence: bitworld master (87724ba, 2026-06-24) added client packet 0x86 "Debug Sprites"
(sprite_v1.md: "planned paths, local labels, diagnostic text"; payload = server-to-client
sprite messages) + ReplayDebugSpriteRecord 0x06 in the replay codec, with codec tests. But
(a) coworld-ctf pins bitworld f5cf0d3 (branch daveey/hd-client-pin, diverged BEFORE the
debug-sprite commit — 0 occurrences of the symbols), (b) the CTF server's
applyPlayerViewerMessage never parses 0x86 and never calls writeDebugSprite, (c) no viewer
anywhere (bitworld master included) renders ReplayData.debugSprites — the global client's
"debugSprites" panel is an unrelated sprite-inspector UI, and (d) the Python SDK bridge only
packs 0x84 input + 0x81 chat. Overlay-in-replay needs all four wired + the LEAGUE redeploy
for hosted replays to carry it.

### Nim/nimby CTF builds: no nimble; pass every ~/.nimby/pkgs dir as --path (src/ if present)

Evidence: `nim c tests/test_replay.nim` fails with "cannot open file: flatty" — CTF resolves
deps via nimby's global checkout dir, not nimble. Working recipe (used by dev_test.sh in the
PR worktree): `--path:$HOME/.nimby/pkgs/<pkg>/src` for each package (bare pkg dir when no
src/). To build against a PATCHED dependency, put its `--path` FIRST. Also: `nimby sync -g`
checks out bitworld at the nimby.lock SHA into ~/.nimby/pkgs/bitworld.

### Validate player-authored data at the boundary it ENTERS, not where it's consumed

Evidence: bitworld's `parseSpritePacket` stores compressedPixels WITHOUT decompressing;
CTF's overlay render calls supersnappy `uncompress` much later, outside any try/except in
the server loop. A structurally-valid packet with garbage pixels would have crashed the
live server at render time and poisoned the replay permanently. Fix pattern: authoritative
validation at drain (decompress + length == w*h*4 before recording), plus a lenient render
guard for hand-crafted replay files that bypass the server.

### uv run <tool> can fail to spawn even when the tool is in .venv/bin — use python -m

Evidence: `uv run pytest` failed with "Failed to spawn: No such file or directory" while
`.venv/bin/pytest` existed and `uv sync` was clean; `uv run python -m pytest` worked
immediately. Suspect a stale entry-point shim; python -m sidesteps it.
