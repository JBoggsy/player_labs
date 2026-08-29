# Abundance policy

This population policy pursues happiness through material security. It chooses
the destination whose sugar and spice harvest buys the most metabolism-adjusted
survival runway, then breaks ties by total harvest, low pollution, short travel,
canonical welfare, and cell ID.

The synchronous player reads `COWORLD_PLAYER_WS_URL` (or the legacy
`COGAMES_ENGINE_WS_URL`), retries until its first connection succeeds, and exits
when that connected episode ends. It reports decision-reason and non-default
choice counters every 250 decisions and at episode end.

Build from this directory:

```bash
docker build -t sugarscape-abundance .
```
