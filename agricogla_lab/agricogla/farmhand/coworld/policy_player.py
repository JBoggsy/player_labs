"""farmhand websocket bridge: SDK cogweb bridge + the scorer brain.

The SDK's ``run_cogweb_bridge`` owns the cogweb.player.v1 envelope (welcome/
observation/reply/final, id-echo, reason re-requests, chess clock, clean exit). We
supply the ``decide`` callback and emit per-decision telemetry to the episode
artifact (what the post-mortem reporter consumes).
"""

from __future__ import annotations

import asyncio
import sys

from players.player_sdk import TraceEvent, TraceOutputs

# The cogweb bridge is VENDORED here (agricogla/farmhand/coworld/cogweb_bridge.py)
# until it lands in the public Player SDK — see Metta-AI/players PR (boses/cogweb-bridge).
# It imports only public-SDK primitives (run_message_bridge, TraceOutputs), so the
# vendored copy and the eventual SDK module are byte-identical; swap this import to
# `from players.player_sdk import ...` once merged.
from agricogla.farmhand.coworld.cogweb_bridge import (
    CogwebContext,
    env_ws_url,
    run_cogweb_bridge,
)

from agricogla.farmhand.brain import Brain
from agricogla.farmhand.params import load_params


def _log(msg: str) -> None:
    print(f"[farmhand] {msg}", file=sys.stderr, flush=True)


async def _run() -> None:
    url = env_ws_url()
    brain = Brain(load_params())

    with TraceOutputs.from_env(prefix="AGRICOGLA", default_outputs="jsonl@artifact") as out:
        sink = out.trace_sink

        def decide(view, ctx: CogwebContext):
            decision = brain.decide(view, ctx.seat, rejected=ctx.reason is not None)
            if sink is not None:
                # Per-decision telemetry for the reporter: round, phase, what we
                # played, and whether this was a forced re-decide after a reject.
                rnd = (view or {}).get("round")
                phase = (view or {}).get("phase")
                sink.record(TraceEvent(
                    tick=0,
                    step=rnd if isinstance(rnd, int) else None,
                    name="domain.decision",
                    data={
                        "round": rnd,
                        "phase": phase,
                        "seat": ctx.seat,
                        "action": decision.get("action") if isinstance(decision, dict) else None,
                        "rejected": ctx.reason is not None,
                        "reason": ctx.reason,
                        "time_left_ms": ctx.time_left_ms,
                    },
                ))
            return decision

        def on_final(scores):
            if sink is not None:
                sink.record(TraceEvent(tick=0, name="domain.final", data={"scores": list(scores)}))
            _log(f"final scores: {scores}")

        await run_cogweb_bridge(
            url, decide, on_final=on_final, trace_outputs=out,
            ping_interval=20, ping_timeout=20, max_size=None,
        )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
