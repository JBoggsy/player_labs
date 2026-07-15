"""King-Richard shim supervisor — the ONLY module that knows which Nim client we run.

Launched by the base image's ``vanilla_wow_coworld.player`` WS wrapper via
``KING_NIMROD_COMMAND="python3 -m wowborg.shim"``. Responsibilities:

1. Map the wrapper's ``KING_NIMROD_*`` credential env to ``KING_RICHARD_*``.
2. Spawn ``king_richard --scenario=nim-control`` with the autonomous planner OFF,
   so our Python policy owns every decision.
3. Wait for the file bridge (``state.json``) to appear, then run the selected
   policy loop in-process for a bounded duration.
4. Stop the Nim client and exit 0 (Coworld treats nonzero as a failed slot).

Modeled on the repo-proven ``wow_sdk.control.hosted_general_grinder`` (the deployed
image's own default). Swapping to a different shim means replacing this module and
the adapter half of ``wowborg.bridge`` — policies never import either's internals.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_RUNTIME_DIR = Path("/tmp/wowborg-runtime")
DEFAULT_KING_RICHARD_BINARY = "/usr/local/bin/king_richard"
# The base image installs the game repo's `bots/` decision package here; king_richard's
# nim-control mode expects it importable (mirrors hosted_general_grinder.py).
PACKAGED_PLAYER_ROOT = "/opt/coworld-player"
# 120 s is the longest hosted duration with a completed XP/replay proof upstream;
# pod + VMaNGOS startup eats most of the 20-minute job budget before our clock starts.
DEFAULT_DURATION_SECONDS = 120.0
DEFAULT_STARTUP_TIMEOUT_SECONDS = 120.0
CHILD_STOP_GRACE_SECONDS = 10.0

CREDENTIAL_SUFFIXES = ("REALM_HOST", "REALM_PORT", "USERNAME", "PASSWORD", "CHARACTER_NAME")


def log(message: str) -> None:
    print(f"WOWBORG-SHIM {message}", flush=True)


def richard_environment(runtime_dir: Path, base_env: dict[str, str] | None = None) -> dict[str, str]:
    """Build the king_richard child env from the wrapper-provided KING_NIMROD_* vars."""
    env = dict(os.environ if base_env is None else base_env)
    for suffix in CREDENTIAL_SUFFIXES:
        if value := env.get(f"KING_NIMROD_{suffix}"):
            env[f"KING_RICHARD_{suffix}"] = value
    env["WOW_SDK_NIM_RUNTIME_DIR"] = str(runtime_dir)
    env["KING_RICHARD_AUTONOMOUS"] = "0"
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (PACKAGED_PLAYER_ROOT, env.get("PYTHONPATH")))
    )
    return env


def wait_for_state(state_file: Path, timeout_seconds: float, child: subprocess.Popen) -> bool:
    """Wait until the Nim client writes its first snapshot (it is logged in by then)."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if state_file.exists():
            return True
        if child.poll() is not None:
            return False
        time.sleep(1.0)
    return False


def stop_child(child: subprocess.Popen) -> None:
    if child.poll() is not None:
        return
    child.send_signal(signal.SIGTERM)
    try:
        child.wait(timeout=CHILD_STOP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        log(f"ignoring non-numeric {name}={raw!r}; using {default}")
        return default


def main() -> int:
    runtime_dir = Path(os.environ.get("WOWBORG_RUNTIME_DIR", DEFAULT_RUNTIME_DIR))
    runtime_dir.mkdir(parents=True, exist_ok=True)
    binary = os.environ.get("WOWBORG_KING_RICHARD_BINARY", DEFAULT_KING_RICHARD_BINARY)
    duration_s = env_float("WOWBORG_DURATION_SECONDS", DEFAULT_DURATION_SECONDS)
    startup_timeout_s = env_float("WOWBORG_STARTUP_TIMEOUT_SECONDS", DEFAULT_STARTUP_TIMEOUT_SECONDS)
    policy_name = os.environ.get("WOWBORG_POLICY", "random_walk")

    log(f"starting shim: policy={policy_name} duration={duration_s}s runtime_dir={runtime_dir}")
    child = subprocess.Popen(  # noqa: S603 — fixed binary path, no shell
        [binary, "--scenario=nim-control"],
        env=richard_environment(runtime_dir),
    )
    try:
        if not wait_for_state(runtime_dir / "state.json", startup_timeout_s, child):
            code = child.poll()
            log(f"nim client never produced state.json (child exit={code}); giving up cleanly")
            return 0

        log("state.json present — nim client is in-world; starting policy loop")
        # Imported late so a bridge/policy import error still yields a clean exit path.
        from wowborg.bridge import ShimBridge
        from wowborg.policies import build_policy
        from wowborg.trace import Tracer

        tracer = Tracer.from_env(runtime_dir)
        tracer.emit(
            "session_start",
            policy=policy_name,
            duration_s=duration_s,
            runtime_dir=str(runtime_dir),
            character=os.environ.get("KING_NIMROD_CHARACTER_NAME"),
            slot=os.environ.get("COWORLD_SLOT"),
        )
        bridge = ShimBridge(runtime_dir, tracer)
        policy = build_policy(policy_name)
        deadline = time.monotonic() + duration_s
        try:
            policy.run(bridge, until=deadline)
        finally:
            tracer.emit("session_end", summary=getattr(policy, "summary", lambda: None)())
            from wowborg.artifact import upload_evidence

            members = upload_evidence(runtime_dir)
            log(f"evidence bundle: {members if members is not None else 'no upload URL configured'}")
        log("policy loop finished")
        return 0
    except Exception as exc:  # noqa: BLE001 — a crashed policy must not fail the slot
        log(f"exiting after handled error: {exc!r}")
        try:
            from wowborg.trace import Tracer

            Tracer.from_env(runtime_dir).emit("error", error=repr(exc))
        except Exception:  # noqa: BLE001
            pass
        return 0
    finally:
        stop_child(child)
        log("nim client stopped")


if __name__ == "__main__":
    sys.exit(main())
