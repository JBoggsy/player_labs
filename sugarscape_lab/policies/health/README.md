# Health policy

This population policy treats clean ground as its primary happiness strategy.
It selects the lowest-pollution destination that preserves a projected safety
floor for both sugar and spice. If no legal move preserves that floor, it repairs
the weaker resource runway first and uses pollution as the next tie-breaker.

Sick agents accept a smaller, still explicit runway floor, allowing them to give
up more resource utility to escape pollution. Periodic and end-of-episode summary
logs count each decision branch, sick activations, departures from the supplied
greedy move, and choices cleaner than that greedy move.

Build from this directory:

```bash
docker build -t sugarscape-health:dev .
```

The image reads `COWORLD_PLAYER_WS_URL` (or the legacy
`COGAMES_ENGINE_WS_URL`), retries until its first connection, uses the synchronous
WebSocket client, and exits when that connected episode ends.
