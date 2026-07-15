# wowborg version log

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
