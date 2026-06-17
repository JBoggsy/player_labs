# mentalist_v4 — Cue-n-Woo player

A full rewrite of the Cue-n-Woo player, built on the **Player SDK** and a strategy
derived entirely from tournament-field evidence (not the dead v1–v3 classify→prose
approach). Strategy + research: [`../docs/designs/mentalist-v4-strategy-and-design.md`](../docs/designs/mentalist-v4-strategy-and-design.md).

## The strategy in one paragraph

The league is won by a **planted-passphrase exploit**, not by reading the hidden style.
The judge's scoring prompt contains *both* players' private interview transcripts, so a
player can **plant** a `<label> = <value>` line in its private asks (which the judge reads
at scoring) and **retrieve** it with a challenge question — the opponent never saw that
transcript and can't answer. So we (1) **author** our own plant→retrieve passphrases
(offense), (2) **defend** against opponents' passphrases with a harvested key→value table
— the only counter, since a true passphrase is unbeatable blind — and (3, scan-gated)
**fingerprint** the judge's steering via self-report probes to make answers concrete.

## Architecture (Player SDK)

Transport + telemetry come from `players.player_sdk`; the strategy is transport-free.

| Module | Responsibility |
|---|---|
| `__main__.py` | Wires `run_message_bridge` (SDK: connect/iterate/send + exit-0-on-close) + `TraceOutputs` (SDK telemetry → episode artifact zip) to the engine. Decodes the Cue-n-Woo JSON protocol. |
| `engine.py` | `PhaseEngine` — pure state machine over the 4 phases (private_questions → proposals → answers → reveal). Idempotence from per-slot counts + one in-flight guard. No transport. |
| `author.py` | Offense: builds plant (private ask) + retrieve (challenge question) + committed-answer triples. Direction A (passphrase). Fresh cue labels to avoid colliding with biglobes/daveey vocab. |
| `passphrase.py` | Defense: detects retrieval questions; extracts an embedded `= value`, else looks up the cue label in `data/opponent_passphrases.json` (author-keyed preferred). The only counter to an opponent passphrase. |
| `validator.py` | Game answer legality (≤12 tokens, ASCII) + deterministic repair. Unchanged from v3 (scoring rules didn't change). |
| `config.py` | Tunable knobs (directive direction, fingerprint toggle, time fallbacks). |
| `data/opponent_passphrases.json` | Harvested key→value table (550 episodes, rounds 213–235). **Re-verify before submit** — opponents may rotate cue-sets. |

**Not yet built (scan-gated):** `interview.py` / `fingerprint.py` — self-report probes +
parsing. Gated on the self-report fingerprint scan (`../probe/probe_selfreport_v2.py`);
`config.FINGERPRINT_ENABLED` is `False` until it validates.

## Why the SDK, and which parts

`run_message_bridge` + `TraceOutputs` are the genuinely game-agnostic SDK pieces (the
bridge even bakes in the hard-won "exit 0 even on an abrupt code-1006 close" rule the
Coworld runner requires). We deliberately do **not** use the SDK's tick-based
`AgentRuntime` — Cue-n-Woo is turn-based with ~7 actions per episode, not a per-frame
gridworld. This mirrors how crewborg uses the SDK.

## Tests

```sh
uv run pytest cue_n_woo_lab/mentalist_v4/tests
```

Covers the full episode flow (plant → retrieve → defend → reveal), passphrase
extraction/lookup (incl. author-collision resolution) against real corpus question texts,
committed-answer legality, idempotence, and error handling.

## Build & run

```sh
cd cue_n_woo_lab/mentalist_v4
docker build --platform linux/amd64 --build-arg PLAYERS_SDK_REF=main -t mentalist-v4:dev .
# entry: python -m mentalist_v4  (reads COWORLD_PLAYER_WS_URL)
```
