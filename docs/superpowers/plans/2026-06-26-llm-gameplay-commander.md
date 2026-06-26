# LLM Gameplay Commander Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A background LLM that steers crewborg's gameplay by writing *priorities* into `belief.commander`, which the existing modes read to bias *how* they execute — never selecting a mode, never blocking a tick.

**Architecture:** A `CommanderStrategy` wraps the existing `RuleBasedStrategy` on the existing `SynchronousStrategyRunner` (mode selection unchanged, every tick). Each tick it delegates to the rules for the mode, feeds a serialized game-state snapshot to a background daemon worker thread (sync Bedrock `call_json`, one call in flight), and returns the worker's latest `CommanderPriorities` as `StrategyResult.inferences`. The runtime folds those into `belief.commander` via the `apply_inferences` hook. Modes read `belief.commander` at their existing candidate-ranking steps under one rule: bias, don't force.

**Tech Stack:** Python 3.12, pydantic, `players.player_sdk` (LLM helpers + `OverwriteBuffer` + `AgentRuntime`), Bedrock Haiku 4.5, pytest.

**Full design:** [`crewrift_lab/crewrift/crewborg/docs/designs/llm-commander.md`](../../../crewrift_lab/crewrift/crewborg/docs/designs/llm-commander.md) (summary in `design.md` §10.6).

## Global Constraints

- All commander code lives under `crewrift_lab/crewrift/crewborg/strategy/commander/` except the `CommanderPriorities` data type (in `types.py`, since it is belief state) and the four mode edits.
- **Disabled path = zero behavior change.** With `CREWBORG_LLM_COMMANDER` unset or no backend, `belief.commander` stays `None` and every mode takes exactly its current branch. This is the correctness gate (Gate-1).
- **Bias, don't force.** Every priority is filter-then-rank or score-nudge and MUST fall back to the current default when it would select nothing valid. Reactive/safety gates are untouched except the two opt-in danger levers.
- **Mirror the meeting LLM conventions** (`strategy/meeting/`): env gating `CREWBORG_LLM_COMMANDER=1` + (`USE_BEDROCK` | `ANTHROPIC_API_KEY`); no-raise client factory degrading to a disabled client; default Haiku 4.5; `CREWBORG_LLM_MODEL` / `CREWBORG_LLM_PROMPT_DIR` / `CREWBORG_LLM_TIMEOUT_SECONDS` reused.
- Run tests with: `uv run pytest crewrift_lab/crewrift/crewborg/tests/...` from the repo root. Lint: `uv run ruff check`.
- The worker thread is a daemon; it must never raise into the inner loop and never touch live mutable belief (handoff only via `OverwriteBuffer`).

## File Structure

**Create:**
- `strategy/commander/__init__.py` — package exports.
- `strategy/commander/schema.py` — `sanitize_priorities(raw, legal_rooms, legal_players)` validation against legal state + danger-reason rule.
- `strategy/commander/context.py` — `serialize_commander_context(belief) -> dict` (gameplay state + legal rooms/players).
- `strategy/commander/llm.py` — `CommanderLLMConfig`, `CommanderLLMResult`, client protocol, `DisabledCommanderClient`, `AnthropicCommanderClient`, `build_commander_client(env)` (mirrors meeting `llm.py`).
- `strategy/commander/prompts.py` — `system_prompt_for_role(role, prompt_dir)`.
- `strategy/commander/memory/crewmate.md`, `strategy/commander/memory/imposter.md` — role doctrine + the danger-mode ⚠️ marking.
- `strategy/commander/worker.py` — `CommanderWorker` daemon thread (snapshot in / priorities out via `OverwriteBuffer`).
- `strategy/commander/strategy.py` — `CommanderStrategy` wrapping `RuleBasedStrategy`.
- `strategy/commander/bias.py` — consumption helpers: `commander_of(belief)`, `filter_or_fallback(candidates, predicate)`, `room_crew_count(belief, room)`.
- Tests under `tests/strategy/commander/` and `tests/modes/`.

**Modify:**
- `types.py:288` — add `CommanderPriorities` model + `Belief.commander: CommanderPriorities | None = None`.
- `__init__.py` (`build_runtime`) — install `CommanderStrategy`, pass `apply_inferences=apply_commander_inferences`.
- `modes/normal.py:85`, `modes/search.py:266,477`, `modes/recon.py:534`, `modes/hunt.py:612` — read priorities (Phases 2–3).
- `strategy/rule_based.py:132` — `skip_evade` danger read (Phase 2).

---

## PHASE 1 — Scaffold + no-op fallback (execution-ready)

Delivers the full plumbing with the LLM stubbed: `belief.commander` exists, the wrapper installs, the worker pumps, priorities reach belief — and with the flag off, behavior is byte-identical.

### Task 1: `CommanderPriorities` type on Belief

**Files:**
- Modify: `crewrift_lab/crewrift/crewborg/types.py` (add model near `class Belief` at line 288; add field)
- Test: `crewrift_lab/crewrift/crewborg/tests/test_commander_priorities.py`

**Interfaces:**
- Produces: `CommanderPriorities` (frozen pydantic) with fields `target_room: str | None = None`, `target_task: int | None = None`, `posture: Literal["stick","isolate","neutral"] = "neutral"`, `hunt_room: str | None = None`, `target_player: str | None = None`, `avoid_room: str | None = None`, `allow_witnessed_kill: bool = False`, `skip_evade: bool = False`, `danger_reason: str | None = None`, `reason: str | None = None`, `as_of_tick: int = 0`. And `Belief.commander: CommanderPriorities | None = None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_commander_priorities.py
from crewrift.crewborg.types import Belief, CommanderPriorities


def test_belief_defaults_commander_none():
    assert Belief().commander is None


def test_commander_priorities_defaults():
    p = CommanderPriorities()
    assert p.posture == "neutral"
    assert p.target_room is None
    assert p.allow_witnessed_kill is False
    assert p.as_of_tick == 0


def test_commander_priorities_is_frozen():
    p = CommanderPriorities(target_room="electrical")
    import pytest
    with pytest.raises(Exception):
        p.target_room = "medbay"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/test_commander_priorities.py -v`
Expected: FAIL with `ImportError: cannot import name 'CommanderPriorities'`.

- [ ] **Step 3: Add the model and field**

In `types.py`, immediately before `class Belief(BaseModel):` (line 288):

```python
class CommanderPriorities(BaseModel):
    """LLM gameplay-commander priorities folded into belief (design §10.6).

    Sticky: persists until the worker's next cycle overwrites it. Read by the modes
    at their discretionary candidate-ranking steps under "bias, don't force". All
    fields optional; unset → default behaviour. ``as_of_tick`` drives the staleness
    guard. The two danger levers are opt-in and require ``danger_reason``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_room: str | None = None
    target_task: int | None = None
    posture: Literal["stick", "isolate", "neutral"] = "neutral"
    hunt_room: str | None = None
    target_player: str | None = None
    avoid_room: str | None = None
    allow_witnessed_kill: bool = False
    skip_evade: bool = False
    danger_reason: str | None = None
    reason: str | None = None
    as_of_tick: int = 0
```

Add to the `Belief` field block (after `phase: Phase = "unknown"`, line 344):

```python
    # LLM gameplay-commander priorities (design §10.6); None when the commander is
    # disabled — every mode then takes its default branch. Written only on the
    # inner-loop thread via apply_commander_inferences.
    commander: CommanderPriorities | None = None
```

Ensure `Literal` and `ConfigDict` are imported at the top of `types.py` (add to the existing pydantic/typing imports if missing).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/test_commander_priorities.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add crewrift_lab/crewrift/crewborg/types.py crewrift_lab/crewrift/crewborg/tests/test_commander_priorities.py
git commit -m "feat(crewborg): add CommanderPriorities belief state (commander scaffold)"
```

### Task 2: Consumption helpers (`bias.py`)

**Files:**
- Create: `crewrift_lab/crewrift/crewborg/strategy/commander/__init__.py` (empty)
- Create: `crewrift_lab/crewrift/crewborg/strategy/commander/bias.py`
- Test: `crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_bias.py`

**Interfaces:**
- Consumes: `Belief`, `CommanderPriorities` (Task 1).
- Produces:
  - `COMMANDER_TTL_TICKS = 240`
  - `commander_of(belief) -> CommanderPriorities | None` — returns `belief.commander` only if non-None and `belief.last_tick - commander.as_of_tick <= COMMANDER_TTL_TICKS`, else `None` (staleness guard).
  - `filter_or_fallback(candidates: list[T], predicate: Callable[[T], bool]) -> list[T]` — returns the filtered list, or the original if filtering empties it.
  - `room_crew_count(belief, room_name: str) -> int` — count of live non-teammate crew currently in that room (reuses `imposter_common.visible_crew` + `in_rect`).

- [ ] **Step 1: Write the failing test**

```python
# tests/strategy/commander/test_bias.py
from crewrift.crewborg.strategy.commander.bias import commander_of, filter_or_fallback
from crewrift.crewborg.types import Belief, CommanderPriorities


def test_filter_or_fallback_keeps_matches():
    assert filter_or_fallback([1, 2, 3, 4], lambda x: x % 2 == 0) == [2, 4]


def test_filter_or_fallback_falls_back_when_empty():
    assert filter_or_fallback([1, 3, 5], lambda x: x % 2 == 0) == [1, 3, 5]


def test_commander_of_fresh():
    b = Belief()
    b.last_tick = 100
    b.commander = CommanderPriorities(target_room="electrical", as_of_tick=50)
    assert commander_of(b).target_room == "electrical"


def test_commander_of_stale_returns_none():
    b = Belief()
    b.last_tick = 10_000
    b.commander = CommanderPriorities(target_room="electrical", as_of_tick=50)
    assert commander_of(b) is None


def test_commander_of_none():
    assert commander_of(Belief()) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_bias.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `bias.py`**

```python
# strategy/commander/bias.py
"""Consumption helpers for commander priorities (design §10.6).

The modes read priorities through these so the "bias, don't force" + staleness
rules live in one place, not copied into four modes.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from crewrift.crewborg.modes import imposter_common as ic
from crewrift.crewborg.types import Belief, CommanderPriorities

T = TypeVar("T")

# A priority older than this (≈10 s at 24 Hz) is ignored — a dead/slow worker
# degrades to default behaviour rather than a stale fixation.
COMMANDER_TTL_TICKS = 240


def commander_of(belief: Belief) -> CommanderPriorities | None:
    c = belief.commander
    if c is None:
        return None
    if belief.last_tick - c.as_of_tick > COMMANDER_TTL_TICKS:
        return None
    return c


def filter_or_fallback(candidates: list[T], predicate: Callable[[T], bool]) -> list[T]:
    kept = [c for c in candidates if predicate(c)]
    return kept if kept else candidates


def room_crew_count(belief: Belief, room_name: str) -> int:
    if belief.map is None:
        return 0
    room = next((r for r in belief.map.rooms if r.name == room_name), None)
    if room is None:
        return 0
    return sum(1 for c in ic.visible_crew(belief) if ic.in_rect((c.world_x, c.world_y), room))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_bias.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add crewrift_lab/crewrift/crewborg/strategy/commander/__init__.py crewrift_lab/crewrift/crewborg/strategy/commander/bias.py crewrift_lab/crewrift/crewborg/tests/strategy/commander/
git commit -m "feat(crewborg): commander consumption helpers (bias/staleness)"
```

### Task 3: Context serialization + schema sanitization

**Files:**
- Create: `strategy/commander/context.py`, `strategy/commander/schema.py`
- Test: `tests/strategy/commander/test_schema.py`

**Interfaces:**
- Produces:
  - `serialize_commander_context(belief) -> dict` — includes keys `phase`, `self` (role/room/position/kill_ready/ticks_until_kill_ready), `legal_rooms: list[str]`, `legal_players: list[str]` (alive non-self colors), `roster` (color → last-seen room + alive), `bodies`, `active_mode`.
  - `sanitize_priorities(raw: dict, legal_rooms: set[str], legal_players: set[str], as_of_tick: int) -> CommanderPriorities` — drops unknown rooms/players to `None`, drops a danger lever set without a non-empty `danger_reason`, stamps `as_of_tick`.

- [ ] **Step 1: Write the failing test**

```python
# tests/strategy/commander/test_schema.py
from crewrift.crewborg.strategy.commander.schema import sanitize_priorities


LEGAL_ROOMS = {"electrical", "medbay"}
LEGAL_PLAYERS = {"red", "blue"}


def test_unknown_room_dropped():
    p = sanitize_priorities({"target_room": "atlantis"}, LEGAL_ROOMS, LEGAL_PLAYERS, as_of_tick=5)
    assert p.target_room is None
    assert p.as_of_tick == 5


def test_known_room_kept():
    p = sanitize_priorities({"hunt_room": "medbay"}, LEGAL_ROOMS, LEGAL_PLAYERS, as_of_tick=5)
    assert p.hunt_room == "medbay"


def test_danger_without_reason_dropped():
    p = sanitize_priorities({"allow_witnessed_kill": True}, LEGAL_ROOMS, LEGAL_PLAYERS, as_of_tick=5)
    assert p.allow_witnessed_kill is False


def test_danger_with_reason_kept():
    p = sanitize_priorities(
        {"skip_evade": True, "danger_reason": "last imposter, must snowball"},
        LEGAL_ROOMS, LEGAL_PLAYERS, as_of_tick=5,
    )
    assert p.skip_evade is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `schema.py` and `context.py`**

```python
# strategy/commander/schema.py
"""Validate raw LLM JSON into CommanderPriorities against the current legal state."""

from __future__ import annotations

from typing import Any

from crewrift.crewborg.types import CommanderPriorities

_VALID_POSTURE = {"stick", "isolate", "neutral"}


def sanitize_priorities(
    raw: dict[str, Any], legal_rooms: set[str], legal_players: set[str], *, as_of_tick: int
) -> CommanderPriorities:
    def room(key: str) -> str | None:
        v = raw.get(key)
        return v if isinstance(v, str) and v in legal_rooms else None

    def player(key: str) -> str | None:
        v = raw.get(key)
        return v if isinstance(v, str) and v in legal_players else None

    posture = raw.get("posture")
    posture = posture if posture in _VALID_POSTURE else "neutral"

    danger_reason = raw.get("danger_reason")
    has_reason = isinstance(danger_reason, str) and danger_reason.strip() != ""
    allow_witnessed_kill = bool(raw.get("allow_witnessed_kill")) and has_reason
    skip_evade = bool(raw.get("skip_evade")) and has_reason

    target_task = raw.get("target_task")
    target_task = target_task if isinstance(target_task, int) else None

    return CommanderPriorities(
        target_room=room("target_room"),
        target_task=target_task,
        posture=posture,
        hunt_room=room("hunt_room"),
        target_player=player("target_player"),
        avoid_room=room("avoid_room"),
        allow_witnessed_kill=allow_witnessed_kill,
        skip_evade=skip_evade,
        danger_reason=danger_reason if (allow_witnessed_kill or skip_evade) else None,
        reason=raw.get("reason") if isinstance(raw.get("reason"), str) else None,
        as_of_tick=as_of_tick,
    )
```

```python
# strategy/commander/context.py
"""Serialize Belief into explicit gameplay state for the commander LLM (design §10.6)."""

from __future__ import annotations

from typing import Any

from crewrift.crewborg.strategy.opportunity import ticks_until_kill_ready
from crewrift.crewborg.types import Belief


def _room_name(belief: Belief, x: int | None, y: int | None) -> str | None:
    if belief.map is None or x is None or y is None:
        return None
    for room in belief.map.rooms:
        if room.x <= x < room.x + room.w and room.y <= y < room.y + room.h:
            return room.name
    return None


def legal_rooms(belief: Belief) -> list[str]:
    return [r.name for r in belief.map.rooms] if belief.map is not None else []


def legal_players(belief: Belief) -> list[str]:
    return [
        rec.color
        for rec in belief.roster.values()
        if rec.life_status != "dead" and rec.color not in belief.teammate_colors
    ]


def serialize_commander_context(belief: Belief) -> dict[str, Any]:
    return {
        "phase": belief.phase,
        "self": {
            "role": belief.self_role,
            "room": _room_name(belief, belief.self_world_x, belief.self_world_y),
            "kill_ready": belief.self_kill_ready,
            "ticks_until_kill_ready": ticks_until_kill_ready(belief),
        },
        "legal_rooms": legal_rooms(belief),
        "legal_players": legal_players(belief),
        "roster": {
            rec.color: {
                "alive": rec.life_status != "dead",
                "room": _room_name(belief, rec.world_x, rec.world_y),
                "last_seen_tick": rec.last_seen_tick,
            }
            for rec in belief.roster.values()
        },
        "active_mode": belief.commander_active_mode if hasattr(belief, "commander_active_mode") else None,
    }
```

> Note: drop the `active_mode` line if `belief` exposes the active mode elsewhere; it is informational only. Keep the serialization minimal — the LLM needs rooms, players, role, and kill timing.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_schema.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add crewrift_lab/crewrift/crewborg/strategy/commander/context.py crewrift_lab/crewrift/crewborg/strategy/commander/schema.py crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_schema.py
git commit -m "feat(crewborg): commander context serialization + schema sanitization"
```

### Task 4: LLM client + worker thread (with disabled fallback)

**Files:**
- Create: `strategy/commander/llm.py`, `strategy/commander/prompts.py`, `strategy/commander/memory/{crewmate,imposter}.md`, `strategy/commander/worker.py`
- Test: `tests/strategy/commander/test_worker.py`

**Interfaces:**
- Consumes: `serialize_commander_context`, `sanitize_priorities`, SDK helpers (`bedrock_enabled`/`select_client`/`resolve_model`/`call_json`/`extract_json_object`/`DEFAULT_*_MODEL`), `OverwriteBuffer`.
- Produces:
  - `build_commander_client(env) -> CommanderLLMClient` — no-raise; `DisabledCommanderClient` when `CREWBORG_LLM_COMMANDER` not truthy or no backend.
  - `CommanderWorker(client)` with `.snapshots: OverwriteBuffer[dict]`, `.priorities: OverwriteBuffer[dict]`, `.start()`, `.close()`. Loop: `wait_take` snapshot → `client.decide(ctx)` → publish raw priorities dict. A disabled client makes `start()` a no-op (worker never runs).

- [ ] **Step 1: Write the failing test** (worker with a fake client; no network)

```python
# tests/strategy/commander/test_worker.py
import time
from crewrift.crewborg.strategy.commander.worker import CommanderWorker


class _FakeClient:
    enabled = True
    def decide(self, context):
        return {"hunt_room": context["legal_rooms"][0], "reason": "fake"}


class _Disabled:
    enabled = False
    def decide(self, context):
        raise RuntimeError("disabled")


def test_worker_publishes_priorities():
    w = CommanderWorker(_FakeClient())
    w.start()
    try:
        w.snapshots.publish({"legal_rooms": ["electrical"], "legal_players": []})
        out = None
        for _ in range(50):
            out = w.priorities.take()
            if out is not None:
                break
            time.sleep(0.02)
        assert out is not None and out["hunt_room"] == "electrical"
    finally:
        w.close()


def test_disabled_worker_never_runs():
    w = CommanderWorker(_Disabled())
    w.start()
    try:
        w.snapshots.publish({"legal_rooms": ["x"], "legal_players": []})
        time.sleep(0.1)
        assert w.priorities.take() is None
    finally:
        w.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_worker.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `llm.py`, `prompts.py`, `memory/*.md`, `worker.py`**

`llm.py` mirrors `strategy/meeting/llm.py` (config dataclass, `CommanderLLMResult`, `CommanderLLMClient` protocol, `DisabledCommanderClient`, `AnthropicCommanderClient.decide(context) -> dict`, `build_commander_client(env)` with `_load_sdk_helpers()` and the no-raise `try/except → DisabledCommanderClient`). Gate on `env.get("CREWBORG_LLM_COMMANDER")` truthy AND (`bedrock_enabled(env)` or `ANTHROPIC_API_KEY`). The decide builds a request with the context + a `response_schema` describing the `CommanderPriorities` fields, calls `call_json`, returns the parsed dict (raw — sanitization happens in the strategy where legal state is known).

`prompts.py` mirrors `strategy/meeting/prompts.py`: `system_prompt_for_role(role, prompt_dir)` loading `memory/{crewmate,imposter}.md`, baked minimal fallback, `CREWBORG_LLM_PROMPT_DIR` override (reuse the meeting `PROMPT_DIR_ENV` constant or a commander-specific one).

`memory/imposter.md` and `memory/crewmate.md` carry the Crewrift play guide + role doctrine. The imposter prompt MUST mark danger fields:
```
⚠️ DANGER fields — only set with a strong, stated reason in `danger_reason`:
- allow_witnessed_kill: strike even if a crewmate may witness it. Usually loses the game. Set ONLY when the math favors it (e.g. last kill to win, or you're the last imposter and stealth no longer matters).
- skip_evade: don't flee/vent after a kill. Set ONLY to immediately chain a second kill on an isolated victim.
```

`worker.py`:
```python
# strategy/commander/worker.py
from __future__ import annotations

import threading
from typing import Any, Protocol

from players.player_sdk import OverwriteBuffer


class _Client(Protocol):
    enabled: bool
    def decide(self, context: dict[str, Any]) -> dict[str, Any]: ...


class CommanderWorker:
    """Daemon thread: take latest game-state snapshot → LLM → publish raw priorities.

    Never touches live belief; both directions go through OverwriteBuffer. A disabled
    client makes start() a no-op so the disabled path costs nothing.
    """

    def __init__(self, client: _Client, *, wait_timeout: float = 0.1) -> None:
        self._client = client
        self._wait_timeout = wait_timeout
        self.snapshots: OverwriteBuffer[dict[str, Any]] = OverwriteBuffer()
        self.priorities: OverwriteBuffer[dict[str, Any]] = OverwriteBuffer()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not getattr(self._client, "enabled", False) or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="crewborg-commander")
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        self.snapshots.close()
        self.priorities.close()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            ctx = self.snapshots.wait_take(timeout=self._wait_timeout)
            if ctx is None:
                continue
            try:
                result = self._client.decide(ctx)
            except Exception:
                continue  # never crash the worker; next snapshot retries
            if result is not None:
                self.priorities.publish(result)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_worker.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add crewrift_lab/crewrift/crewborg/strategy/commander/llm.py crewrift_lab/crewrift/crewborg/strategy/commander/prompts.py crewrift_lab/crewrift/crewborg/strategy/commander/memory crewrift_lab/crewrift/crewborg/strategy/commander/worker.py crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_worker.py
git commit -m "feat(crewborg): commander LLM client + daemon worker thread (no-raise, disabled fallback)"
```

### Task 5: `CommanderStrategy` wrapper + `build_runtime` wiring

**Files:**
- Create: `strategy/commander/strategy.py`
- Modify: `__init__.py` (`build_runtime`)
- Test: `tests/strategy/commander/test_strategy.py`

**Interfaces:**
- Consumes: `RuleBasedStrategy`, `CommanderWorker`, `build_commander_client`, `serialize_commander_context`, `sanitize_priorities`, `serialize` legal-room/player helpers.
- Produces:
  - `CommanderStrategy(rules, worker)` — `.decide(snapshot) -> StrategyResult`: read belief under `snapshot.read()`, get the rules' directive, publish the serialized context to `worker.snapshots`, take the latest raw priorities from `worker.priorities` (if any), sanitize against current legal state, and return `StrategyResult(directive=<rules>, inferences={"commander": priorities.model_dump()})`. Caches the last sanitized priorities so a returned `inferences` is present every tick (sticky), not only on the ticks a fresh LLM result lands.
  - `apply_commander_inferences(belief, inferences) -> None` — set `belief.commander = CommanderPriorities(**inferences["commander"])` when present.

- [ ] **Step 1: Write the failing test** (fake worker, no LLM)

```python
# tests/strategy/commander/test_strategy.py
from crewrift.crewborg.strategy.commander.strategy import CommanderStrategy, apply_commander_inferences
from crewrift.crewborg.strategy.rule_based import RuleBasedStrategy
from crewrift.crewborg.strategy.commander.worker import CommanderWorker
from crewrift.crewborg.types import Belief, CommanderPriorities
# Reuse the existing snapshot test helper used by RuleBasedStrategy tests:
from crewrift.crewborg.tests.strategy.helpers import make_snapshot  # adjust import to the repo's helper


class _Disabled:
    enabled = False
    def decide(self, ctx): raise RuntimeError


def test_commander_strategy_returns_rule_directive_and_no_priorities_when_disabled():
    belief = Belief()
    belief.phase = "Playing"
    belief.self_role = "crewmate"
    snap = make_snapshot(belief)
    strat = CommanderStrategy(RuleBasedStrategy(), CommanderWorker(_Disabled()))
    result = strat.decide(snap)
    assert result.directive.mode == "normal"            # rules unchanged
    # disabled worker → no commander inferences (or commander stays None after apply)
    inf = result.inferences.get("commander")
    apply_commander_inferences(belief, result.inferences)
    assert belief.commander is None or inf is None


def test_apply_commander_inferences_sets_belief():
    belief = Belief()
    apply_commander_inferences(belief, {"commander": CommanderPriorities(target_room="electrical").model_dump()})
    assert belief.commander.target_room == "electrical"
```

> If the repo has no `make_snapshot` helper, build the `BeliefSnapshot` the way the existing `tests/strategy/test_rule_based.py` does — read that test first and copy its snapshot construction.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_strategy.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `strategy.py` and wire `build_runtime`**

`strategy.py`:
```python
# strategy/commander/strategy.py
from __future__ import annotations

from typing import Any

from crewrift.crewborg.strategy.commander.context import (
    legal_players, legal_rooms, serialize_commander_context,
)
from crewrift.crewborg.strategy.commander.schema import sanitize_priorities
from crewrift.crewborg.strategy.commander.worker import CommanderWorker
from crewrift.crewborg.strategy.rule_based import RuleBasedStrategy
from crewrift.crewborg.types import ActionState, Belief, CommanderPriorities
from players.player_sdk import StrategyResult
from players.player_sdk.types import BeliefSnapshot


class CommanderStrategy:
    """Wrap the rule-based mode selector; add async LLM priorities via inferences."""

    def __init__(self, rules: RuleBasedStrategy, worker: CommanderWorker) -> None:
        self._rules = rules
        self._worker = worker
        self._last: CommanderPriorities | None = None
        self._started = False

    def decide(self, snapshot: BeliefSnapshot[Belief, ActionState]) -> StrategyResult:
        if not self._started:
            self._worker.start()
            self._started = True
        with snapshot.read() as memory:
            belief = memory.belief
            directive = self._rules._select(belief)  # same selection the rules run
            ctx = serialize_commander_context(belief)
            rooms = set(legal_rooms(belief))
            players = set(legal_players(belief))
            tick = belief.last_tick
        self._worker.snapshots.publish(ctx)
        raw = self._worker.priorities.take()
        if raw is not None:
            self._last = sanitize_priorities(raw, rooms, players, as_of_tick=tick)
        inferences: dict[str, Any] = {}
        if self._last is not None:
            inferences["commander"] = self._last.model_dump()
        return StrategyResult(directive=directive, inferences=inferences)


def apply_commander_inferences(belief: Belief, inferences: dict[str, Any]) -> None:
    payload = inferences.get("commander")
    if payload is not None:
        belief.commander = CommanderPriorities(**payload)
```

> `RuleBasedStrategy.decide` already wraps `_select` in `snapshot.read()`; calling `self._rules._select(belief)` inside our own read avoids a double lock. If `_select` is considered private, add a thin public `select(belief)` to `RuleBasedStrategy` and call that instead.

In `__init__.py` `build_runtime`, replace the strategy runner block:
```python
from crewrift.crewborg.strategy.commander.llm import build_commander_client
from crewrift.crewborg.strategy.commander.strategy import CommanderStrategy, apply_commander_inferences
from crewrift.crewborg.strategy.commander.worker import CommanderWorker
import os

# ... inside build_runtime, where the runner is constructed:
commander = CommanderStrategy(RuleBasedStrategy(), CommanderWorker(build_commander_client(dict(os.environ))))
return AgentRuntime(
    # ... unchanged args ...
    strategy_runner=SynchronousStrategyRunner(
        commander, trace_sink=trace_sink, metrics_sink=metrics_sink,
    ),
    apply_inferences=apply_commander_inferences,
    # ... unchanged args ...
)
```

- [ ] **Step 4: Run tests + the full crewborg suite (no regressions)**

Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_strategy.py -v`
Expected: PASS.
Run: `uv run pytest crewrift_lab/crewrift/crewborg/tests`
Expected: the whole suite still passes (commander disabled by default → no behavior change).

- [ ] **Step 5: Gate-1 smoke (disabled path = no change)**

Run a local smoke with the flag OFF and confirm connect→play→exit is unchanged (coworld-local-run skill). Then `CREWBORG_LLM_COMMANDER=1 USE_BEDROCK=1` and confirm `commander_decision`/`strategy_inferences` traces appear and the agent still plays.

- [ ] **Step 6: Commit**

```bash
git add crewrift_lab/crewrift/crewborg/strategy/commander/strategy.py crewrift_lab/crewrift/crewborg/__init__.py crewrift_lab/crewrift/crewborg/tests/strategy/commander/test_strategy.py
git commit -m "feat(crewborg): CommanderStrategy wrapper + build_runtime wiring (priorities → belief)"
```

---

## PHASE 2 — Imposter levers + danger mode (highest expected lift)

Each task: write a mode test that sets `belief.commander` and asserts the biased choice, plus a test that an invalid/stale priority falls back to current behavior. Then implement the minimal read via `bias.py` helpers. Commit per task.

### Task 6: `hunt_room` / `avoid_room` in SearchMode
- Modify `modes/search.py` `_nearby_task_rooms` (line 477) and `_pick_room` (line 266): after building `rooms`, if `commander_of(belief)` has `hunt_room` and it's among the candidate rooms, set `self._target_room` to it deterministically instead of `self._rng.choice`; drop any room whose name == `avoid_room`. Use `filter_or_fallback` so an empty result reverts to the random pick. Test: a commander with `hunt_room="medbay"` makes Search head to medbay; an unknown room falls back to random.

### Task 7: `target_player` in SearchMode follow + ReconMode
- `modes/search.py` `_a_crewmate_left` (line 449): prefer returning the `target_player` record when it qualifies. `modes/recon.py` `decide` (line 534): if `target_player` alive & known, close on them instead of `most_recent_victim`. Tests assert the biased target; fallback when target unknown/dead.

### Task 8: `target_player` score-nudge in HuntMode
- `modes/hunt.py` `_resolve_victim` (line 612): when no committed victim, prefer `target_player` if it's among visible selectable victims; else `select_victim`. Strike gates untouched. Test: with two visible victims, the commander's `target_player` is chosen; without it, `select_victim`'s pick stands.

### Task 9: Danger mode — `allow_witnessed_kill` + `skip_evade`
- `modes/hunt.py` strike gate (line 599): `unwitnessed(belief, victim) or (commander_of(belief) and commander.allow_witnessed_kill)`. Emit a `commander_danger` trace with `danger_reason` when this path fires the kill.
- `strategy/rule_based.py` `_select_imposter` evade branch (line 132): skip the `_recent_self_kill → evade` return when `commander_of(belief)` has `skip_evade`. Trace `commander_danger`.
- Tests: witnessed victim + `allow_witnessed_kill` (with reason) → `kill` intent; without the flag → shadow. Recent kill + `skip_evade` → not Evade; without → Evade. Stale priority → conservative.

---

## PHASE 3 — Crewmate levers

### Task 10: `target_room` / `target_task` in NormalMode
- `modes/normal.py` `_pick_target` (line 85): filter `candidates` to those whose task is in `target_room` (`filter_or_fallback`); if `target_task` is signalled+reachable, return it. Tests: room bias picks a task in that room; unreachable/empty falls back to nearest.

### Task 11: `posture` (stick/isolate) in NormalMode
- `modes/normal.py` `_pick_target`: when `posture != "neutral"`, break ties among reachable signalled tasks by `room_crew_count` of each task's room (stick = max, isolate = min) before the distance tiebreak. Tests: with two equidistant tasks, `stick` picks the crowded room, `isolate` the empty one.

---

## PHASE 4 — Later (out of scope for this plan)

- Real `EscortMode` (active crewmate buddy-following).
- Unify with the meeting LLM (a meeting sets the next Playing-phase plan).
- Tracing dashboard / warehouse `commander` analysis for eval (`commander_applied` rate, danger win/loss tally).

---

## Self-Review

- **Spec coverage:** §2 architecture → Tasks 1,2,5. §3 priorities vocab → Task 1 (type), Task 3 (sanitize), Tasks 6–11 (consumption). §4 danger mode → Task 9. §5 bias-don't-force + staleness → Task 2 helpers, used in 6–11. §6 worker/prompt/config → Tasks 3,4. §7 tracing → Tasks 5,9 (`commander_decision`/`commander_danger`); fuller tracing is Phase 4. §8 phasing → phase headers. ✅
- **Disabled path:** Tasks 4 (worker no-op), 5 (Step 5 Gate-1) verify zero change. ✅
- **Type consistency:** `CommanderPriorities` fields are defined once (Task 1) and used verbatim in `sanitize_priorities` (Task 3), `apply_commander_inferences` (Task 5), and the mode reads (6–11). `commander_of` is the single staleness gate. ✅
- **Known follow-up for the executor:** confirm the exact `BeliefSnapshot` construction used by existing strategy tests (Task 5 Step 1 note) and whether `RuleBasedStrategy._select` should be promoted to a public `select()`.
