# wowborg version log

## v2 - shim adoption: random-point navigator

- Version UUID: `eb6aa13e-4fcd-4037-a443-42fc7ae676d0` (uploaded 2026-07-15,
  `players-wowborg:dev` linux/amd64, tag `purpose=v2-shim-random-walk`).

- Architecture change: our policy now drives the game's bundled Nim client
  (`king_richard --scenario=nim-control`, autonomous planner off) through its file
  bridge, layered on the DEPLOYED reference player image (vanilla_wow 0.1.19 player
  image, pinned by digest in `tools/versions.env`). No Python WoW protocol code in the
  hosted path. Design: `docs/designs/wowborg-v2-shim-adoption.md`.
- New: `shim.py` (supervisor), `bridge.py` (typed seam), `types.py`,
  `policies/random_walk.py` (T0: random 10–20 yd legs with typed movement settlements).
- Observability, three redundant channels: `trace.py` (JSONL + `WOWBORG-TRACE` stdout of
  every observation/intent/typed outcome), `artifact.py` (session-end evidence zip PUT to
  `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL`), and rate-limited `/say` breadcrumbs
  (`ShimBridge.say`) that land inside the CWREPLAY itself.
- Honors the duration budget (`WOWBORG_DURATION_SECONDS`, default 120 s) — the v1
  "never self-terminates" defect is gone by construction (the shim stops the Nim client
  and exits; the base wrapper sends `done`).
- Validated locally: 45 unit tests; image builds amd64; end-to-end container smoke with
  a scripted fake king_richard (12 s, 12 legs, all `reached_target`).
- v1 login-stack modules retained for debugging; no longer the image entrypoint.

## v1 - idle login skeleton

- Version UUID: `6d3b00e5-512b-4c62-95c5-2a83367867b7` (uploaded 2026-07-13, `players-wowborg:dev` linux/amd64).
- Pure Python WoW realmd/world login client.
- Enters the seeded `wow_session.character_name`.
- Idles with periodic `CMSG_PING`.
- Does not decode world state or take gameplay actions.
- Does NOT honor the session's `deadline_seconds` — never self-terminates, so hosted
  episodes always run to the full variant deadline (fix in v2).
- First hosted smoke 2026-07-14: `xreq_23feebad-…`, 4 episodes on `orc-fresh-start`
  (5× self-play), all completed, score 0.0, no crash. Policy logs not retained; login
  success not yet confirmed from artifacts.
