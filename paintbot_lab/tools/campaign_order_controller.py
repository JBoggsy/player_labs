#!/usr/bin/env python3
"""Issue one verified, unstaked Paintbot campaign airdrop per round.

This is deliberately a thin deterministic controller. It reads the live board,
chooses a non-FFA cell owned by a favorable opponent, and rewrites only a marked
one-round section of our player-authored strategist prompt. Sonnet remains the
platform tool-call adapter; the controller audits whether its call matched.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import secrets
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from coworld.api_client import CoworldApiClient


DEFAULT_LEAGUE = "league_b8fa9b35-ac22-48cf-a03f-07b397aff1c7"
DEFAULT_PLAYER = "ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce"
START_MARKER = "[CAMPAIGN_ORDER_CONTROLLER START]"
END_MARKER = "[CAMPAIGN_ORDER_CONTROLLER END]"
MAX_ERROR_BACKOFF_SECONDS = 300.0

# Conservative matchup ordering from the 100-game tournament-clone evaluation.
# Max and NanosaurusX were robust even in the one-seat cut; RowDaBoat follows on
# overall evidence. The remaining ordering is used only as a fallback.
OPPONENT_PRIORITY = [
    "Max Yankov",
    "NanosaurusX",
    "RowDaBoat",
    "Bella",
    "Rohit Mukherjee",
    "Alex Smith",
    "Ari Sklar",
    "relh",
    "Jordan",
    "daveey",
    "Andre von Houck",
    "Ron @ SWGY",
]
OPPONENT_RANK = {name: rank for rank, name in enumerate(OPPONENT_PRIORITY)}
EventLogger = Callable[[dict[str, Any]], None]
StateCheckpoint = Callable[[dict[str, Any]], None]


def now() -> str:
    return datetime.now(UTC).isoformat()


def without_directive(prompt: str) -> str:
    start = prompt.find(START_MARKER)
    if start < 0:
        return prompt.rstrip()
    end = prompt.find(END_MARKER, start)
    if end < 0:
        raise RuntimeError("prompt has a controller start marker without an end marker")
    return (prompt[:start] + prompt[end + len(END_MARKER) :]).strip()


def choose_target(board: dict[str, Any], player_id: str) -> dict[str, Any]:
    width = board["config"]["width"]
    height = board["config"]["height"]
    owners = board["frames"][-1]["owners"]
    names = {player["id"]: player["name"] for player in board["players"]}
    candidates = []
    for index, owner in enumerate(owners):
        if owner == player_id:
            continue
        x, y = index % width, index // width
        owner_name = names.get(owner, "Baseline" if owner is None else str(owner))
        candidates.append(
            {
                "cell": f"{x},{y}",
                "x": x,
                "y": y,
                "owner_id": owner,
                "owner_name": owner_name,
                "map_ref": board["map_refs"][index],
                "mode": board["modes"][index],
                "opponent_rank": OPPONENT_RANK.get(owner_name, len(OPPONENT_PRIORITY)),
                "center_distance": abs(x - (width - 1) / 2) + abs(y - (height - 1) / 2),
            }
        )
    if not candidates:
        raise RuntimeError("no attackable campaign cell")

    non_ffa = [candidate for candidate in candidates if candidate["mode"] != "ffa4"]
    pool = non_ffa or candidates
    pool.sort(
        key=lambda candidate: (
            candidate["opponent_rank"],
            candidate["center_distance"],
            candidate["cell"],
        )
    )
    return pool[0]


def directive(round_no: int, target: dict[str, Any], nonce: str) -> str:
    return f"""{START_MARKER}
# NEXT ROUND DIRECTIVE — ROUND {round_no} ONLY
Directive nonce: {nonce}
This section overrides the general targeting guidance above for round {round_no}.
When the live context begins with ROUND {round_no}, issue exactly one `invade`
tool call with `target_cell` set to `{target['cell']}` and OMIT `from_cell`, so
it is an unstaked airdrop. Do not call `invade` for any other cell. Do not issue
a staked invasion and do not call `pass`.

Verified immediately before this directive was saved: cell {target['cell']} is
owned by {target['owner_name']} and is map_ref `{target['map_ref']}`, campaign
mode `{target['mode']}`.

If the live context's round number is not {round_no}, this directive is stale:
do not reuse its target. Call `pass` exactly once instead.
{END_MARKER}"""


def append_log(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps({"at": now(), **event}, sort_keys=True) + "\n")


def validate_board(board: dict[str, Any]) -> None:
    size = board["config"]["width"] * board["config"]["height"]
    if not board["frames"] or board["frames"][-1]["round"] != board["round"]:
        raise RuntimeError("latest settled frame does not match board round")
    for field in ("map_refs", "modes"):
        if len(board[field]) != size:
            raise RuntimeError(f"board {field} has {len(board[field])} entries, expected {size}")
    if len(board["frames"][-1]["owners"]) != size:
        raise RuntimeError("board owner array has the wrong length")


def target_still_matches(board: dict[str, Any], target: dict[str, Any]) -> bool:
    width = board["config"]["width"]
    index = target["y"] * width + target["x"]
    return (
        board["frames"][-1]["owners"][index] == target["owner_id"]
        and board["map_refs"][index] == target["map_ref"]
        and board["modes"][index] == target["mode"]
    )


def restore_directive(
    client: CoworldApiClient,
    league: str,
    player: str,
    state: dict[str, Any],
    log: EventLogger,
) -> None:
    if state.get("directive_restored"):
        return
    current = client.get_campaign_prompt(league, player_id=player).prompt
    nonce = state.get("nonce")
    if START_MARKER not in current:
        # A human may already have restored or replaced it. Never overwrite that.
        state["directive_restored"] = True
        state["phase"] = "restored"
        log({"event": "directive_already_absent", "round": state.get("directive_round")})
        return
    if not nonce or nonce not in current:
        raise RuntimeError("live controller block does not contain this process's nonce; refusing to overwrite")
    base = without_directive(current)
    if hashlib.sha256(base.encode()).hexdigest() != state.get("base_prompt_sha256"):
        raise RuntimeError("base prompt changed while directive was armed; refusing to overwrite")
    client.set_campaign_prompt(league, player_id=player, prompt=base)
    for attempt in range(8):
        if client.get_campaign_prompt(league, player_id=player).prompt == base:
            break
        if attempt == 7:
            raise RuntimeError("directive restore readback mismatch")
        time.sleep(2)
    state["directive_restored"] = True
    state["phase"] = "restored"
    log({"event": "directive_restored", "round": state.get("directive_round")})


def audit_conversation(
    client: CoworldApiClient,
    league: str,
    player: str,
    state: dict[str, Any],
    log: EventLogger,
) -> None:
    directive_round = state.get("directive_round")
    if not directive_round or state.get("audited_round") == directive_round:
        return
    try:
        conversation = client.get_campaign_conversation(league, player_id=player, round_no=directive_round)
    except Exception:
        return
    calls = [block for block in (conversation.response or []) if block.get("type") == "tool_use"]
    expected = state["target"]["cell"]
    matching = [
        block
        for block in calls
        if block.get("name") == "invade"
        and (block.get("input") or {}).get("target_cell") == expected
        and "from_cell" not in (block.get("input") or {})
    ]
    compliant = len(calls) == 1 and len(matching) == 1
    log(
        {
            "event": "conversation_audit",
            "round": directive_round,
            "expected_target": expected,
            "compliant": compliant,
            "tool_calls": calls,
            "reasoning": conversation.reasoning,
            "error": conversation.error,
        },
    )
    state["audited_round"] = directive_round
    state["audit_compliant"] = compliant


def audit_pending(
    client: CoworldApiClient,
    board: dict[str, Any],
    league: str,
    player: str,
    state: dict[str, Any],
    log: EventLogger,
) -> None:
    pending = board.get("pending_round")
    if not pending or pending.get("round") != state.get("directive_round"):
        return
    already_logged = state.get("pending_audited_round") == pending["round"]
    target = state["target"]
    orders = (pending.get("orders") or {}).get(player) or {}
    order_ok = (
        orders.get("airdrops") == [target["cell"]]
        and orders.get("invasions") == []
        and orders.get("auto_airdrops") == 0
        and orders.get("dropped") == []
    )
    battles = [
        battle
        for battle in pending.get("battles") or []
        if battle.get("attacker") == player and battle.get("target") == target["cell"]
    ]
    battle_ok = len(battles) == 1 and all(
        (
            battle.get("source") is None
            and battle.get("staked") is False
            and battle.get("map_ref") == target["map_ref"]
            and battle.get("mode") == target["mode"]
        )
        for battle in battles
    )
    state["saw_pending_round"] = pending["round"]
    state["pending_order_compliant"] = order_ok and battle_ok
    if not already_logged:
        log(
            {
                "event": "pending_order_audit",
                "round": pending["round"],
                "target": target,
                "order_ok": order_ok,
                "battle_ok": battle_ok,
                "orders": orders,
                "battles": battles,
            },
        )
        state["pending_audited_round"] = pending["round"]
    audit_conversation(client, league, player, state, log)
    restore_directive(client, league, player, state, log)


def audit_settlement(board: dict[str, Any], player: str, state: dict[str, Any], log: EventLogger) -> None:
    directive_round = state.get("directive_round")
    if directive_round != board["round"] or state.get("settlement_audited_round") == directive_round:
        return
    target = state["target"]
    battles = [
        battle
        for battle in board["frames"][-1].get("battles") or []
        if battle.get("attacker") == player and battle.get("target") == target["cell"]
    ]
    width = board["config"]["width"]
    index = target["y"] * width + target["x"]
    owner_after = board["frames"][-1]["owners"][index]
    log(
        {
            "event": "settlement_audit",
            "round": directive_round,
            "target": target,
            "owner_after": owner_after,
            "captured": owner_after == player,
            "battles": battles,
        },
    )
    state["settlement_audited_round"] = directive_round


def install_directive(
    client: CoworldApiClient,
    board: dict[str, Any],
    league: str,
    player: str,
    state: dict[str, Any],
) -> None:
    target = state["target"]
    current = client.get_campaign_prompt(league, player_id=player).prompt
    base = without_directive(current)
    if hashlib.sha256(base.encode()).hexdigest() != state["base_prompt_sha256"]:
        raise RuntimeError("base prompt changed while directive was being armed")
    updated = base + "\n\n" + directive(state["directive_round"], target, state["nonce"])
    if len(updated) > 4000:
        raise RuntimeError(f"updated prompt is {len(updated)} chars; API maximum is 4000")
    if START_MARKER in current:
        if current != updated:
            raise RuntimeError("another controller directive is already live")
    else:
        client.set_campaign_prompt(league, player_id=player, prompt=updated)

    for attempt in range(8):
        readback = client.get_campaign_prompt(league, player_id=player)
        full = client.get_campaign_full_prompt(league, player_id=player)
        fresh_board = client.get_campaign_board(league).model_dump(mode="json")
        validate_board(fresh_board)
        if (
            fresh_board["round"] != board["round"]
            or fresh_board.get("pending_round") is not None
            or not target_still_matches(fresh_board, target)
        ):
            raise RuntimeError("board changed while directive was being armed")
        if readback.prompt == updated and state["nonce"] in full.context:
            break
        if attempt == 7:
            raise RuntimeError("prompt/full-prompt readback did not contain the exact directive")
        time.sleep(2)
    state["prompt_chars"] = len(updated)


def recover_interrupted_arm(
    client: CoworldApiClient,
    board: dict[str, Any],
    league: str,
    player: str,
    state: dict[str, Any],
    log: EventLogger,
    checkpoint: StateCheckpoint,
) -> None:
    if state.get("phase") != "arming":
        return
    pending = board.get("pending_round")
    if pending and pending.get("round") == state.get("directive_round"):
        state["phase"] = "armed"
        checkpoint(state)
        return
    if (
        pending is not None
        or board["round"] != state.get("board_round_when_written")
        or not target_still_matches(board, state["target"])
    ):
        restore_directive(client, league, player, state, log)
        checkpoint(state)
        return
    install_directive(client, board, league, player, state)
    state["phase"] = "armed"
    checkpoint(state)
    log(
        {
            "event": "directive_arm_recovered",
            "round": state["directive_round"],
            "target": state["target"],
            "nonce": state["nonce"],
        }
    )


def run_cycle(
    args: argparse.Namespace,
    client: CoworldApiClient,
    state: dict[str, Any],
    log: EventLogger,
    checkpoint: StateCheckpoint,
) -> dict[str, Any]:
    board = client.get_campaign_board(args.league).model_dump(mode="json")
    validate_board(board)
    recover_interrupted_arm(client, board, args.league, args.player, state, log, checkpoint)
    audit_conversation(client, args.league, args.player, state, log)
    audit_pending(client, board, args.league, args.player, state, log)
    audit_settlement(board, args.player, state, log)

    pending = board.get("pending_round")
    previous_settled = (
        state.get("directive_round") == board["round"]
        and state.get("saw_pending_round") == board["round"]
        and state.get("pending_order_compliant") is True
        and state.get("audit_compliant") is True
    )
    initial_arm = not state and args.arm_now
    if pending is None and (previous_settled or initial_arm):
        next_round = board["round"] + 1
        if state.get("directive_round") != next_round:
            previous_state = state
            target = choose_target(board, args.player)
            current = client.get_campaign_prompt(args.league, player_id=args.player)
            base = without_directive(current.prompt)
            nonce = f"r{next_round}-{secrets.token_hex(8)}"
            state = {
                "phase": "arming",
                "directive_round": next_round,
                "board_round_when_written": board["round"],
                "target": target,
                "nonce": nonce,
                "base_prompt_sha256": hashlib.sha256(base.encode()).hexdigest(),
                "written_at": now(),
            }
            checkpoint(state)
            try:
                install_directive(client, board, args.league, args.player, state)
            except Exception:
                restore_directive(client, args.league, args.player, state, log)
                state = previous_state
                checkpoint(state)
                raise
            state["phase"] = "armed"
            checkpoint(state)
            log(
                {
                    "event": "directive_saved",
                    "round": next_round,
                    "board_round": board["round"],
                    "target": target,
                    "nonce": nonce,
                    "prompt_chars": state["prompt_chars"],
                }
            )
            print(
                f"round {next_round}: saved unstaked airdrop {target['cell']} "
                f"vs {target['owner_name']} ({target['map_ref']}/{target['mode']})",
                flush=True,
            )
    checkpoint(state)
    return state


def run(args: argparse.Namespace) -> None:
    state_path = Path(args.state)
    log_path = Path(args.log)
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    lock_path = state_path.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    log = lambda event: append_log(log_path, event)

    def checkpoint(value: dict[str, Any]) -> None:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = state_path.with_name(f".{state_path.name}.{os.getpid()}.tmp")
        with temporary.open("w") as handle:
            handle.write(json.dumps(value, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, state_path)

    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        error_backoff = args.poll_seconds
        while True:
            try:
                with CoworldApiClient.from_login(server_url=args.server) as client:
                    state = run_cycle(args, client, state, log, checkpoint)
                sleep_seconds = args.poll_seconds
                error_backoff = args.poll_seconds
            except Exception as error:
                log({"event": "error", "error": repr(error)})
                print(f"controller error: {error!r}", flush=True)
                sleep_seconds = error_backoff
                error_backoff = min(error_backoff * 2, MAX_ERROR_BACKOFF_SECONDS)
            if args.once:
                return
            time.sleep(sleep_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", default=DEFAULT_LEAGUE)
    parser.add_argument("--player", default=DEFAULT_PLAYER)
    parser.add_argument("--server", default="https://softmax.com/api")
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    parser.add_argument("--state", default="/tmp/stencil-campaign-order-controller/state.json")
    parser.add_argument("--log", default="/tmp/stencil-campaign-order-controller/events.jsonl")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--arm-now", action="store_true", help="Allow the first directive without observing settlement")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
