# Paintbot analysis tools

## Outcomes and comparison

`tools/event_warehouse.py` reads explicit participant positions and result/config teams. It supports red/blue/green/yellow, labels the winner from result `win` flags, and leaves incomplete outcomes unknown. It does not infer attacker/defender roles. `*_score` columns sum seat scores for diagnostics; they are not the authority for team wins. Rebuild generated warehouses to replace older incorrect outcomes; existing local datasets are not silently rewritten.

```bash
uv run python paintbot_lab/tools/compare.py BASE_DIR CAND_DIR \
  --baseline BASE_POLICY_VERSION_UUID --candidate CAND_POLICY_VERSION_UUID \
  --target win_rate --json /tmp/paintbot-comparison.json
uv run python .claude/skills/coworld-ab/scripts/compare_report.py \
  /tmp/paintbot-comparison.json --out /tmp/paintbot-comparison.html
```

The adapter reads downloaded `episode.json`/`results.json`, selects exact version UUIDs, excludes incomplete outcomes and operational failures, and reports exclusions. One selected team contributes **one observation per episode**, with mean per-seat diagnostics. A selected version on multiple teams or duplicate/shared episodes is rejected. Groups retain game version, variant and team. Establish matching separately: roster, allied policy versions, seat composition, maps/seeds and same-window execution. Do not compare historical batches as proof of current improvement.

## Behavior and replay

The root [tooling guide](../../docs/tooling.md) defines shared artifact and comparison contracts. Keep Paintbot metrics and parsing here.
