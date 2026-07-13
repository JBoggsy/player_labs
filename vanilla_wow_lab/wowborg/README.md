# wowborg

`wowborg` is a minimal Python Vanilla WoW Coworld player. v1 logs into realmd,
enters the seeded character on the world server, then idles with `CMSG_PING`.

## Layout

- `wire.py`, `srp6.py`, `crypt.py`: pure byte/crypto protocol core.
- `realmd.py`: SRP6 realmd login and realm-list request.
- `world.py`: mangosd auth, character selection, login verify, idle pings.
- `tunnel.py`: `/tcp/realmd` and `/tcp/world` WebSocket byte tunnels.
- `session.py`, `run.py`, `main.py`: Coworld `/player` orchestration.

## Commands

```bash
uv run pytest vanilla_wow_lab/wowborg/tests -q
uv run python -c "import wowborg"
uv run python -m wowborg
```

Build context is this directory:

```bash
docker build --platform=linux/amd64 -t wowborg vanilla_wow_lab/wowborg
```
