# Stencil native Nim port

## Status

Complete locally as of 2026-08-03. The native policy is the deployable
implementation; the Python policy remains an executable behavioral oracle and
the source of the tuning-registry CLI. No policy version has been uploaded or
submitted.

## Contract

The port preserves the externally observable policy behavior for a given
Sprite-v1 byte stream and `STENCIL_*` environment: the ordered controller masks
and chat payloads must be identical. It also preserves all 91 policy environment
variables, their parsing and validation, the connection lifecycle, and the
default JSONL trace/artifact contract. Host scheduling time and performance
counters are not deterministic and are outside byte equivalence.

The production process is native from socket to decision. It connects with
`whisky`, decodes Sprite-v1 packets and snappy sprite payloads directly, runs
the policy, and emits controller/chat packets without a Python interpreter or
Player SDK in the image.

## Module map

The native implementation lives in `paintbot/stencil_nim/` and follows the
policy's existing responsibilities:

- `protocols.nim`, `perception.nim`: wire state and observations.
- `worldmap.nim`, `nav.nim`: summed-area footprint erosion, cover, A*, and lazy
  goal distance fields.
- `belief_state.nim`, `belief_update.nim`: episode state and track updates.
- `roles.nim`, `squads.nim`, `strategy.nim`: assignments and intent selection.
- `fight.nim`, `items.nim`, `action.nim`: combat scoring and final controls.
- `chat.nim`, `trace.nim`: team protocol and operational evidence.
- `policy.nim`, `stencil.nim`: orchestration and native process lifecycle.
- `config.nim`, `types.nim`: the complete 91-variable configuration contract
  and shared domain types.

The split intentionally mirrors behavior boundaries rather than translating
Python files line-for-line. Episode-owned map data stays episode-owned; no
global generated-map cache was introduced.

## Differential method

`tools/self_play.py --record-wire` wraps the Python oracle connection and saves
every inbound binary frame plus the exact outbound decision. `replay.nim`
consumes those frames without a server. `tools/compare_stencil.py` compiles the
replay target and rejects the first mask or chat mismatch.

The final corpus covers:

| profile | exact decisions |
|---|---:|
| 1v1 | 5,004 |
| 2v2 | 32,741 |
| 4-player FFA | 33,674 |
| giant 8-player FFA | 50,221 |
| major optional features disabled | 22,299 |
| squads and squad command enabled | 25,296 |
| **total** | **169,235** |

The comparison exposed semantic traps that ordinary outcome tests would not:
Python's ties-to-even rounding, scene dictionary insertion order, the distinction
between an uncached path and a cached failed path, one decision per world-changing
packet, controller bit numbering, and initialization-time sprite metadata.

## Performance and packaging

On the same 2,502-decision replay, the optimized native target used about
0.17 seconds of CPU and 13.0 MB maximum RSS; Python used about 0.40 seconds of CPU
and 70.5 MB peak RSS. The primary memory fix was preserving Python's cached-map
semantics without copying the full walkability grid into every observation.

`paintbot/stencil_nim/Dockerfile` produces a stripped, LTO-optimized
`linux/amd64` binary in a non-root Debian runtime. The dependency graph comes
from the exact canonical Paintbot game revision in `tools/versions.env`.
`tools/self_play.py --candidate-runtime docker` is the packaging/connectivity
check; `--candidate-runtime nim` is the faster native development path.

## Maintenance rule

Behavior changes should be made in Nim. When exact compatibility with the
bootstrap policy matters, record a targeted Python-oracle stream and run the
differential comparator. Keep Python only as long as it provides useful oracle
or tuning-registry value; do not accidentally restore it to the production
image.
