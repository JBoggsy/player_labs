"""King-Richard shim supervisor (0.1.31 contract) — the ONLY module that knows which
Nim client we run.

Launched by the base image's ``vanilla_wow_coworld.player`` WS wrapper via
``KING_NIMROD_COMMAND="python3 -m wowborg.shim"``. At 0.1.31 the wrapper appends an
``--assets=<url>`` argument (the game container serves world data over HTTP — player
images carry none) and exports ``KING_NIMROD_SESSION_DEADLINE_SECONDS``. Responsibilities:

1. Map the wrapper's ``KING_NIMROD_*`` credential env to ``KING_RICHARD_*``.
2. Spawn ``king_richard --scenario=nim-control`` (autonomous planner OFF), forwarding
   the ``--assets`` argument.
3. Connect to the Nim control socket (``vanilla_wow.nim_control.v1``), arm external
   per-step selection, and run the policy loop for the session budget (derived from
   the wrapper-provided deadline, minus a teardown margin).
4. Upload the evidence bundle, stop the Nim client, and exit 0 (nonzero fails the slot).

Modeled on the 0.1.31 ``wow_sdk.control.hosted_general_grinder`` (the deployed image's
own default). Swapping shims means replacing this module + the adapter half of
``wowborg.bridge`` — policies never import either's internals.
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
# The base image installs the game repo's `bots/` tree here; nim-control expects it.
PACKAGED_PLAYER_ROOT = "/opt/coworld-player"
DEFAULT_DURATION_SECONDS = 120.0
# Leave room for evidence upload + teardown inside the session budget.
TEARDOWN_MARGIN_SECONDS = 30.0
DEFAULT_STARTUP_TIMEOUT_SECONDS = 180.0
CHILD_STOP_GRACE_SECONDS = 10.0

CREDENTIAL_SUFFIXES = (
    "REALM_HOST",
    "REALM_PORT",
    "USERNAME",
    "PASSWORD",
    "CHARACTER_NAME",
    "CHARACTER_RACE",
    "CHARACTER_CLASS",
    "CHARACTER_GENDER",
)


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


def assets_argument(argv: list[str], env: dict[str, str] | None = None) -> str | None:
    """Build the Nim child's --assets=<url> argument.

    The deployed 0.1.31 wrapper exports VANILLA_WOW_ASSET_SERVICE_URL (the game's
    authenticated world-data endpoint) and expects the KING_NIMROD_COMMAND child to
    convert it — exactly what hosted_general_grinder does. Without it king_richard
    fetches bare paths, loads no mmaps, and every piloted move fails with
    "no goal-relative progress" (proven by the first v3 hosted probe). Newer wrappers
    may append --assets= to argv directly; accept both, env winning on conflict is
    fine because they carry the same URL.
    """
    source = os.environ if env is None else env
    if url := source.get("VANILLA_WOW_ASSET_SERVICE_URL"):
        return f"--assets={url}"
    return next((a for a in argv if a.startswith("--assets=")), None)


def session_duration_seconds(env: dict[str, str] | None = None) -> float:
    """Policy-loop budget: explicit override > session deadline − margin > default."""
    source = os.environ if env is None else env
    override = source.get("WOWBORG_DURATION_SECONDS")
    if override:
        try:
            return float(override)
        except ValueError:
            log(f"ignoring non-numeric WOWBORG_DURATION_SECONDS={override!r}")
    deadline = source.get("KING_NIMROD_SESSION_DEADLINE_SECONDS")
    if deadline:
        try:
            return max(30.0, float(deadline) - TEARDOWN_MARGIN_SECONDS)
        except ValueError:
            log(f"ignoring non-numeric session deadline {deadline!r}")
    return DEFAULT_DURATION_SECONDS


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


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    runtime_dir = Path(os.environ.get("WOWBORG_RUNTIME_DIR", DEFAULT_RUNTIME_DIR))
    runtime_dir.mkdir(parents=True, exist_ok=True)
    binary = os.environ.get("WOWBORG_KING_RICHARD_BINARY", DEFAULT_KING_RICHARD_BINARY)
    duration_s = session_duration_seconds()
    startup_timeout_s = env_float("WOWBORG_STARTUP_TIMEOUT_SECONDS", DEFAULT_STARTUP_TIMEOUT_SECONDS)
    policy_name = os.environ.get("WOWBORG_POLICY", "random_walk")
    slot = int(os.environ.get("WOW_SDK_NIM_RUNTIME_SLOT", "0") or 0)

    command = [binary, "--scenario=nim-control"]
    if assets := assets_argument(argv):
        command.append(assets)

    log(
        f"starting shim: policy={policy_name} duration={duration_s}s slot={slot} "
        f"runtime_dir={runtime_dir} command={command}"
    )
    child = subprocess.Popen(  # noqa: S603 — fixed binary path, no shell
        command,
        env=richard_environment(runtime_dir),
    )
    try:
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
            slot=slot,
        )
        bridge = ShimBridge(runtime_dir, tracer, slot=slot)
        if not bridge.connect(timeout_s=startup_timeout_s):
            code = child.poll()
            log(f"control socket never came up (child exit={code}); giving up cleanly")
            tracer.emit("session_end", summary={"error": "control_socket_timeout"})
            return 0
        if not bridge.arm_external_control(
            deadline_unix_seconds=time.time() + duration_s
        ):
            log("goal submission rejected; giving up cleanly")
            tracer.emit("session_end", summary={"error": "goal_rejected"})
            return 0

        policy = build_policy(policy_name)
        deadline = time.monotonic() + duration_s
        try:
            # The policy loop must survive transient bridge/socket failures for the
            # whole session (v9: one escaped TimeoutError cost 812s of race time).
            while time.monotonic() < deadline:
                try:
                    policy.run(bridge, until=deadline)
                    break
                except Exception as exc:  # noqa: BLE001
                    log(f"policy loop crashed ({exc!r}); reconnecting and resuming")
                    tracer.emit("policy_restart", error=repr(exc))
                    bridge._reconnect()
                    time.sleep(2.0)
        finally:
            tracer.emit("session_end", summary=getattr(policy, "summary", lambda: None)())
            bridge.close()
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
