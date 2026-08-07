"""Wowborg player entry point over the canonical hosted Gymnasium environment."""

from __future__ import annotations

import os
import time
from pathlib import Path

from wowborg.artifact import upload_evidence
from wowborg.environment import (
    GymSession,
    PLAYER_WS_URL_ENV,
    build_hosted_env,
    hosted_endpoint_diagnostics,
)
from wowborg.player_progress import PlayerProgressReporter
from wowborg.strategies import build_strategy
from wowborg.trace import Tracer


def main() -> None:
    """Run one synchronous Gymnasium policy loop until the hosted episode closes."""

    player_ws_url = os.environ.get(PLAYER_WS_URL_ENV)
    if not player_ws_url:
        raise SystemExit(f"{PLAYER_WS_URL_ENV} is required")
    runtime_dir = Path(os.environ.get("WOWBORG_RUNTIME_DIR", "/tmp/wowborg-runtime"))
    tracer = Tracer.from_env(runtime_dir)
    tracer.emit("environment_endpoint", **hosted_endpoint_diagnostics(player_ws_url))
    progress = PlayerProgressReporter(player_ws_url, tracer)
    strategy_name = os.environ.get("WOWBORG_STRATEGY", "traverse")
    strategy = build_strategy(strategy_name)
    duration = float(os.environ.get("WOWBORG_DURATION_SECONDS", "86400"))
    env = build_hosted_env(
        player_ws_url,
        startup_timeout_seconds=float(
            os.environ.get("WOWBORG_STARTUP_TIMEOUT_SECONDS", "240")
        ),
        step_timeout_seconds=float(
            os.environ.get("WOWBORG_STEP_TIMEOUT_SECONDS", "30")
        ),
    )
    session: GymSession | None = None
    succeeded = False
    try:
        progress.connect()
        frame, info = env.reset()
        session = GymSession(
            env,
            frame,
            info,
            tracer,
            frame_observer=progress.observe,
        )
        tracer.emit(
            "session_start",
            protocol="vanilla_wow.environment.v1",
            strategy=strategy_name,
            episode_id=frame.episode_id,
        )
        strategy.run(session, until=time.monotonic() + duration)
        tracer.emit(
            "session_end",
            terminated=session.finished,
            summary=strategy.summary(),
            info=session.info,
        )
        succeeded = True
    except Exception as exc:
        tracer.emit("error", error=repr(exc))
        raise
    finally:
        if session is not None:
            session.close()
        else:
            env.close()
        progress.close(
            success=succeeded,
            detail=(
                "wowborg environment policy completed"
                if succeeded
                else "wowborg environment policy failed"
            ),
        )
        upload_evidence(runtime_dir)
