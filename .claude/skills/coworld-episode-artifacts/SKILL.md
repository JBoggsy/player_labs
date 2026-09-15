---
name: coworld-episode-artifacts
description: Download or stream Coworld episode metadata, results, replays and accessible diagnostics for analysis.
---

# Download episode evidence

Use normal participant access to fetch the artifacts needed for the current question. Read the game's adapter guide before assuming a replay/result format. Access to private opponent logs is not required or authorized by a field study.

```bash
S=.claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py
uv run python "$S" --xreq xreq_ID --watch --out /tmp/evaluation
uv run python "$S" --ereq ereq_ID --out /tmp/episode
uv run python "$S" --round round_ID --out /tmp/round
uv run python "$S" --policy POLICY --version VERSION -n 20 --out /tmp/policy
```

Replace IDs/placeholders. Stream immediately after creating the request so downloading overlaps execution. `--watch` supports `--xreq`; multiple `--ereq`, `--round` or `--episode` flags combine within their selection mode. `--division` discovers its rounds. Pool discovery is retired.

Use `--no-replay`, `--no-results`, `--no-logs` or `--no-artifacts` only when the question doesn't require that evidence. `--force` refetches existing data. Watch retries are bounded by `--max-attempts`; exhausted episodes yield a nonzero status and remain in the index. Rerunning resumes from disk; an exhausted request needs its attempt state inspected/reset deliberately to retry.

## Inspect before analyzing

Each directory contains the raw `episode.json`, requested results/replay, accessible per-seat `logs/` and `artifacts/`, coverage markers, and a download summary. Optional combined game logs and error information may be present. See [endpoint and coverage reference](references/endpoint-map.md).

- Join policy-version UUIDs to **explicit participant positions**, never array order or policy-deduplicated scores.
- Inspect missing evidence and ops failures before judging gameplay. Do not turn a missing outcome into a loss, draw or zero.
- Diagnose with game tools; shared transport does not interpret game mechanics.
- A 403 stays a reported coverage limit. `--elevated` is rejected for lab analysis.
