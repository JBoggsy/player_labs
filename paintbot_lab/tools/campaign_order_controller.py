#!/usr/bin/env python3
"""Issue statistically selected Paintbot campaign orders each round.

The controller combines current-champion campaign and owned experience-request
results by opponent and cell type. It always issues one unstaked airdrop and may
add one adjacent staked invasion when the posterior predictive probability of
winning both paired games exceeds the configured threshold. Sonnet remains the
platform tool-call adapter; the controller audits whether its calls matched.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import secrets
import time
from collections.abc import Callable
from datetime import UTC, datetime
from math import sqrt
from pathlib import Path
from typing import Any

from coworld.api_client import CoworldApiClient


DEFAULT_LEAGUE = "league_b8fa9b35-ac22-48cf-a03f-07b397aff1c7"
DEFAULT_PLAYER = "ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce"
START_MARKER = "[CAMPAIGN_ORDER_CONTROLLER START]"
END_MARKER = "[CAMPAIGN_ORDER_CONTROLLER END]"
MAX_ERROR_BACKOFF_SECONDS = 300.0
ANALYSIS_SCHEMA_VERSION = 1
DEFAULT_STATS_REFRESH_SECONDS = 60.0
DOUBLE_VICTORY_THRESHOLD = 0.75

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


def bucket_key(opponent_id: str | None, map_ref: str, mode: str) -> str:
    return f"{opponent_id or 'baseline'}|{map_ref}|{mode}"


def posterior(wins: int, nonwins: int) -> dict[str, Any]:
    """Uniform-prior beta-binomial posterior and two-game prediction."""
    alpha = wins + 1
    beta = nonwins + 1
    total = alpha + beta
    observations = wins + nonwins
    win_probability = alpha / total
    double_probability = alpha * (alpha + 1) / (total * (total + 1))

    # Wilson is reported as a frequentist sensitivity interval alongside the
    # Bayesian decision probability. It is not used as an extra gate.
    if observations:
        z = 1.959963984540054
        observed = wins / observations
        denominator = 1 + z * z / observations
        center = (observed + z * z / (2 * observations)) / denominator
        radius = (
            z
            * sqrt(
                observed * (1 - observed) / observations + z * z / (4 * observations**2)
            )
            / denominator
        )
        interval = [max(0.0, center - radius), min(1.0, center + radius)]
    else:
        interval = [0.0, 1.0]
    return {
        "wins": wins,
        "nonwins": nonwins,
        "observations": observations,
        "win_probability": win_probability,
        "double_victory_probability": double_probability,
        "wilson_95": interval,
    }


def normalize_map_ref(row: dict[str, Any]) -> str | None:
    variant = str(row.get("variant_name") or "").lower()
    if "1v1" in variant:
        return "1v1"
    if "2v2" in variant:
        return "2v2"
    if "4ffa8" in variant or ("free-for-all" in variant and "8 per team" in variant):
        return "4ffa8"
    if "4ffa" in variant or "free-for-all" in variant:
        return "4ffa"
    return None


def subject_score(row: dict[str, Any], policy_version_id: str) -> float | None:
    scores = [
        float(score["score"])
        for score in row.get("scores") or []
        if str(score.get("policy_version_id")) == policy_version_id
    ]
    if len(scores) == 1:
        return scores[0]

    subject_positions = {
        int(participant["position"])
        for participant in row.get("participants") or []
        if participant.get("kind") == "policy"
        and str(participant.get("policy_version_id")) == policy_version_id
    }
    participant_scores = {
        float(item["score"])
        for item in row.get("participant_scores") or []
        if int(item["position"]) in subject_positions
    }
    return participant_scores.pop() if len(participant_scores) == 1 else None


def xp_opponents(
    row: dict[str, Any], policy_version_id: str, mode: str
) -> list[dict[str, str]]:
    participants = [
        participant
        for participant in row.get("participants") or []
        if participant.get("kind") == "policy"
    ]
    subject_positions = {
        int(participant["position"])
        for participant in participants
        if str(participant.get("policy_version_id")) == policy_version_id
    }
    if not subject_positions:
        return []

    if mode == "2v2":
        subject_team = min(subject_positions) % 2
        opponents = [
            participant
            for participant in participants
            if int(participant["position"]) % 2 != subject_team
            and participant.get("is_filler") is False
        ]
    else:
        opponents = [
            participant
            for participant in participants
            if str(participant.get("policy_version_id")) != policy_version_id
            and participant.get("is_filler") is False
        ]

    unique: dict[str, dict[str, str]] = {}
    for participant in opponents:
        opponent_id = participant.get("player_id")
        if opponent_id:
            unique[str(opponent_id)] = {
                "id": str(opponent_id),
                "name": str(
                    participant.get("player_name")
                    or participant.get("policy_name")
                    or opponent_id
                ),
            }
    return list(unique.values())


def board_cell_type(board: dict[str, Any], cell: str) -> tuple[str, str] | None:
    try:
        x, y = (int(value) for value in cell.split(",", 1))
    except (AttributeError, TypeError, ValueError):
        return None
    width = board["config"]["width"]
    height = board["config"]["height"]
    if not (0 <= x < width and 0 <= y < height):
        return None
    index = y * width + x
    return board["map_refs"][index], board["modes"][index]


def add_observation(
    buckets: dict[str, dict[str, Any]],
    *,
    opponent_id: str,
    opponent_name: str,
    map_ref: str,
    mode: str,
    won: bool,
    source: str,
) -> None:
    key = bucket_key(opponent_id, map_ref, mode)
    bucket = buckets.setdefault(
        key,
        {
            "opponent_id": opponent_id,
            "opponent_name": opponent_name,
            "map_ref": map_ref,
            "mode": mode,
            "wins": 0,
            "nonwins": 0,
            "campaign_episodes": 0,
            "xp_episodes": 0,
        },
    )
    bucket["opponent_name"] = opponent_name
    bucket["wins" if won else "nonwins"] += 1
    bucket[f"{source}_episodes"] += 1


def combine_buckets(*groups: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    combined: dict[str, dict[str, Any]] = {}
    for group in groups:
        for key, source in group.items():
            target = combined.setdefault(
                key,
                {
                    "opponent_id": source["opponent_id"],
                    "opponent_name": source["opponent_name"],
                    "map_ref": source["map_ref"],
                    "mode": source["mode"],
                    "wins": 0,
                    "nonwins": 0,
                    "campaign_episodes": 0,
                    "xp_episodes": 0,
                },
            )
            target["opponent_name"] = source["opponent_name"]
            for field in ("wins", "nonwins", "campaign_episodes", "xp_episodes"):
                target[field] += int(source.get(field, 0))
    for bucket in combined.values():
        bucket.update(posterior(bucket["wins"], bucket["nonwins"]))
    return combined


def list_champion_episodes(
    client: CoworldApiClient, policy_version_id: Any
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = None
    while True:
        page = client.list_episode_requests(
            policy_version_id=policy_version_id, limit=200, cursor=cursor
        )
        rows.extend(row.model_dump(mode="json") for row in page.entries)
        cursor = page.next_cursor
        if not cursor:
            return rows


def analyze_xp(
    rows: list[dict[str, Any]], policy_version_id: str, requester_user_id: str | None
) -> tuple[dict[str, dict[str, Any]], int]:
    buckets: dict[str, dict[str, Any]] = {}
    episodes = 0
    for row in rows:
        if (
            requester_user_id is None
            or row.get("requester_user_id") != requester_user_id
            or row.get("round_id") is not None
            or row.get("status") != "completed"
            or row.get("error_type")
        ):
            continue
        map_ref = normalize_map_ref(row)
        if not map_ref:
            continue
        mode = "ffa4" if map_ref.startswith("4ffa") else "2v2"
        score = subject_score(row, policy_version_id)
        if score is None:
            continue
        opponents = xp_opponents(row, policy_version_id, mode)
        if not opponents:
            continue
        episodes += 1
        for opponent in opponents:
            add_observation(
                buckets,
                opponent_id=opponent["id"],
                opponent_name=opponent["name"],
                map_ref=map_ref,
                mode=mode,
                won=score > 0,
                source="xp",
            )
    return buckets, episodes


def analyze_campaign(
    board: dict[str, Any],
    history: dict[str, Any],
    rows: list[dict[str, Any]],
    policy_version_id: str,
) -> tuple[dict[str, dict[str, Any]], int]:
    buckets: dict[str, dict[str, Any]] = {}
    rows_by_episode = {
        str(row["episode_id"]): row
        for row in rows
        if row.get("episode_id")
        and row.get("round_id")
        and row.get("status") == "completed"
        and not row.get("error_type")
    }
    names = {
        str(key): str(value) for key, value in (history.get("names") or {}).items()
    }
    seen_episodes: set[str] = set()
    for battle in history.get("battles") or []:
        cell_type = board_cell_type(board, battle.get("target"))
        if not cell_type:
            continue
        map_ref, mode = cell_type
        for episode_id in battle.get("episode_ids") or []:
            row = rows_by_episode.get(str(episode_id))
            if not row or str(episode_id) in seen_episodes:
                continue
            score = subject_score(row, policy_version_id)
            if score is None:
                continue
            seen_episodes.add(str(episode_id))
            for opponent_id in battle.get("opponents") or []:
                add_observation(
                    buckets,
                    opponent_id=str(opponent_id),
                    opponent_name=names.get(str(opponent_id), str(opponent_id)),
                    map_ref=map_ref,
                    mode=mode,
                    won=score > 0,
                    source="campaign",
                )
    return buckets, len(seen_episodes)


def refresh_analysis(
    client: CoworldApiClient,
    board: dict[str, Any],
    league: str,
    player: str,
    previous: dict[str, Any] | None,
    refresh_seconds: float,
    log: EventLogger,
) -> dict[str, Any]:
    memberships = client.list_memberships(
        league_id=league,
        player_id=player,
        active_only=True,
        champions_only=True,
        limit=100,
    )
    if len(memberships) != 1:
        raise RuntimeError(
            f"expected one active champion membership for {player}, found {len(memberships)}"
        )
    champion = memberships[0].policy_version.model_dump(mode="json")
    champion_id = str(champion["id"])
    now_epoch = time.time()
    changed = (
        not previous
        or previous.get("schema_version") != ANALYSIS_SCHEMA_VERSION
        or previous.get("champion", {}).get("id") != champion_id
    )
    due = (
        changed
        or board["round"] != (previous or {}).get("last_campaign_round")
        or now_epoch - float((previous or {}).get("refreshed_at_epoch", 0))
        >= refresh_seconds
    )
    if not due:
        return previous

    rows = list_champion_episodes(client, memberships[0].policy_version.id)
    mine = client.list_experience_requests(mine=True, limit=1, offset=0)
    requester_user_id = mine.entries[0].requester_user_id if mine.entries else None
    xp_buckets, xp_episodes = analyze_xp(rows, champion_id, requester_user_id)

    if changed or board["round"] != (previous or {}).get("last_campaign_round"):
        history = client.get_campaign_history(league, player_id=player).model_dump(
            mode="json"
        )
        campaign_buckets, campaign_episodes = analyze_campaign(
            board, history, rows, champion_id
        )
    else:
        campaign_buckets = (previous or {}).get("campaign_buckets", {})
        campaign_episodes = int(
            (previous or {}).get("sources", {}).get("campaign_episodes", 0)
        )

    buckets = combine_buckets(campaign_buckets, xp_buckets)
    analysis = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "champion": champion,
        "requester_user_id": requester_user_id,
        "refreshed_at": now(),
        "refreshed_at_epoch": now_epoch,
        "last_campaign_round": board["round"],
        "sources": {
            "champion_episode_rows": len(rows),
            "campaign_episodes": campaign_episodes,
            "xp_episodes": xp_episodes,
        },
        "campaign_buckets": campaign_buckets,
        "xp_buckets": xp_buckets,
        "buckets": buckets,
    }
    eligible = sum(
        bucket["mode"] == "2v2"
        and bucket["double_victory_probability"] > DOUBLE_VICTORY_THRESHOLD
        for bucket in buckets.values()
    )
    log(
        {
            "event": "statistics_refreshed",
            "champion": champion,
            "champion_changed": changed,
            "sources": analysis["sources"],
            "matchup_cell_buckets": len(buckets),
            "invasion_eligible_buckets": eligible,
        }
    )
    return analysis


def estimate(
    analysis: dict[str, Any] | None, opponent_id: str | None, map_ref: str, mode: str
) -> dict[str, Any]:
    bucket = ((analysis or {}).get("buckets") or {}).get(
        bucket_key(opponent_id, map_ref, mode)
    )
    if bucket:
        return {"level": "opponent_cell", **bucket}
    return {"level": "prior", **posterior(0, 0)}


def candidates(
    board: dict[str, Any], player_id: str, analysis: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    width = board["config"]["width"]
    height = board["config"]["height"]
    owners = board["frames"][-1]["owners"]
    names = {player["id"]: player["name"] for player in board["players"]}
    result = []
    for index, owner in enumerate(owners):
        if owner == player_id:
            continue
        x, y = index % width, index // width
        owner_name = names.get(owner, "Baseline" if owner is None else str(owner))
        candidate = {
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
        candidate["estimate"] = estimate(
            analysis, owner, candidate["map_ref"], candidate["mode"]
        )
        result.append(candidate)
    return result


def choose_target(
    board: dict[str, Any], player_id: str, analysis: dict[str, Any] | None = None
) -> dict[str, Any]:
    choices = candidates(board, player_id, analysis)
    if not choices:
        raise RuntimeError("no attackable campaign cell")

    non_ffa = [candidate for candidate in choices if candidate["mode"] != "ffa4"]
    pool = non_ffa or choices
    pool.sort(
        key=lambda candidate: (
            -candidate["estimate"]["double_victory_probability"],
            -candidate["estimate"]["observations"],
            candidate["opponent_rank"],
            candidate["center_distance"],
            candidate["cell"],
        )
    )
    return pool[0]


def adjacent_owned_source(
    board: dict[str, Any], player_id: str, target: dict[str, Any]
) -> str | None:
    width = board["config"]["width"]
    height = board["config"]["height"]
    owners = board["frames"][-1]["owners"]
    adjacent = []
    for x, y in (
        (target["x"] - 1, target["y"]),
        (target["x"] + 1, target["y"]),
        (target["x"], target["y"] - 1),
        (target["x"], target["y"] + 1),
    ):
        if 0 <= x < width and 0 <= y < height and owners[y * width + x] == player_id:
            adjacent.append(f"{x},{y}")
    return min(adjacent) if adjacent else None


def choose_invasion(
    board: dict[str, Any],
    player_id: str,
    analysis: dict[str, Any] | None,
    airdrop: dict[str, Any],
    threshold: float = DOUBLE_VICTORY_THRESHOLD,
) -> dict[str, Any] | None:
    eligible = []
    for target in candidates(board, player_id, analysis):
        if target["cell"] == airdrop["cell"] or target["mode"] != "2v2":
            continue
        source = adjacent_owned_source(board, player_id, target)
        estimate_value = target["estimate"]
        if (
            source
            and estimate_value["level"] == "opponent_cell"
            and estimate_value["double_victory_probability"] > threshold
        ):
            eligible.append({**target, "from_cell": source})
    if not eligible:
        return None
    eligible.sort(
        key=lambda target: (
            -target["estimate"]["double_victory_probability"],
            -target["estimate"]["observations"],
            target["center_distance"],
            target["cell"],
        )
    )
    return eligible[0]


def directive(
    round_no: int,
    target: dict[str, Any],
    nonce: str,
    invasion: dict[str, Any] | None = None,
) -> str:
    if invasion:
        orders = f"""Issue exactly two `invade` calls and no others:
1. `target_cell={target["cell"]}` with `from_cell` OMITTED (unstaked airdrop).
2. `target_cell={invasion["cell"]}` with `from_cell={invasion["from_cell"]}` (staked invasion)."""
        verification = (
            f"Airdrop {target['cell']} is {target['owner_name']} {target['map_ref']}/{target['mode']}; "
            f"invasion {invasion['from_cell']}->{invasion['cell']} is {invasion['owner_name']} "
            f"{invasion['map_ref']}/{invasion['mode']}."
        )
    else:
        orders = f"""Issue exactly one `invade` call with `target_cell={target["cell"]}` and
`from_cell` OMITTED (unstaked airdrop). Issue no other tool call."""
        verification = f"Airdrop {target['cell']} is {target['owner_name']} {target['map_ref']}/{target['mode']}."
    return f"""{START_MARKER}
# NEXT ROUND DIRECTIVE — ROUND {round_no} ONLY
Directive nonce: {nonce}
This section overrides the general targeting guidance above for round {round_no}.
When the live context begins with ROUND {round_no}: {orders}
Do not call `pass`. Verified immediately before save: {verification}

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
            raise RuntimeError(
                f"board {field} has {len(board[field])} entries, expected {size}"
            )
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


def invasion_still_matches(
    board: dict[str, Any], player: str, invasion: dict[str, Any] | None
) -> bool:
    if not invasion:
        return True
    if not target_still_matches(board, invasion):
        return False
    width = board["config"]["width"]
    source_x, source_y = (int(value) for value in invasion["from_cell"].split(",", 1))
    return (
        abs(source_x - invasion["x"]) + abs(source_y - invasion["y"]) == 1
        and board["frames"][-1]["owners"][source_y * width + source_x] == player
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
        log(
            {"event": "directive_already_absent", "round": state.get("directive_round")}
        )
        return
    if not nonce or nonce not in current:
        raise RuntimeError(
            "live controller block does not contain this process's nonce; refusing to overwrite"
        )
    base = without_directive(current)
    if hashlib.sha256(base.encode()).hexdigest() != state.get("base_prompt_sha256"):
        raise RuntimeError(
            "base prompt changed while directive was armed; refusing to overwrite"
        )
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
        conversation = client.get_campaign_conversation(
            league, player_id=player, round_no=directive_round
        )
    except Exception:
        return
    calls = [
        block
        for block in (conversation.response or [])
        if block.get("type") == "tool_use"
    ]
    target = state["target"]
    invasion = state.get("invasion")
    expected_calls = [{"target_cell": target["cell"]}]
    if invasion:
        expected_calls.append(
            {"target_cell": invasion["cell"], "from_cell": invasion["from_cell"]}
        )
    actual_calls = []
    for block in calls:
        if block.get("name") != "invade":
            continue
        inputs = block.get("input") or {}
        normalized = {"target_cell": inputs.get("target_cell")}
        if "from_cell" in inputs:
            normalized["from_cell"] = inputs["from_cell"]
        actual_calls.append(normalized)
    compliant = len(calls) == len(expected_calls) and actual_calls == expected_calls
    log(
        {
            "event": "conversation_audit",
            "round": directive_round,
            "expected_calls": expected_calls,
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
    orders, battles, order_ok, battle_ok = audit_order_record(pending, player, state)
    state["saw_pending_round"] = pending["round"]
    state["pending_order_compliant"] = order_ok and battle_ok
    if not already_logged:
        log(
            {
                "event": "pending_order_audit",
                "round": pending["round"],
                "target": state["target"],
                "invasion": state.get("invasion"),
                "order_ok": order_ok,
                "battle_ok": battle_ok,
                "orders": orders,
                "battles": battles,
            },
        )
        state["pending_audited_round"] = pending["round"]
    audit_conversation(client, league, player, state, log)
    restore_directive(client, league, player, state, log)


def audit_order_record(
    record: dict[str, Any], player: str, state: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], bool, bool]:
    target = state["target"]
    invasion = state.get("invasion")
    orders = (record.get("orders") or {}).get(player) or {}
    expected_invasions = []
    if invasion:
        expected_invasions.append(
            {"from_cell": invasion["from_cell"], "target_cell": invasion["cell"]}
        )
    order_ok = (
        orders.get("airdrops") == [target["cell"]]
        and orders.get("invasions") == expected_invasions
        and orders.get("auto_airdrops") == 0
        and orders.get("dropped") == []
    )
    airdrop_battles = [
        battle
        for battle in record.get("battles") or []
        if battle.get("attacker") == player and battle.get("target") == target["cell"]
    ]
    airdrop_ok = len(airdrop_battles) == 1 and all(
        (
            battle.get("source") is None
            and battle.get("staked") is False
            and battle.get("map_ref") == target["map_ref"]
            and battle.get("mode") == target["mode"]
        )
        for battle in airdrop_battles
    )
    invasion_battles = []
    invasion_ok = True
    if invasion:
        invasion_battles = [
            battle
            for battle in record.get("battles") or []
            if battle.get("attacker") == player
            and battle.get("target") == invasion["cell"]
        ]
        invasion_ok = len(invasion_battles) == 1 and all(
            battle.get("source") == invasion["from_cell"]
            and battle.get("staked") is True
            and battle.get("map_ref") == invasion["map_ref"]
            and battle.get("mode") == invasion["mode"]
            for battle in invasion_battles
        )
    battles = airdrop_battles + invasion_battles
    battle_ok = airdrop_ok and invasion_ok
    return orders, battles, order_ok, battle_ok


def recover_missed_pending_round(
    client: CoworldApiClient,
    board: dict[str, Any],
    league: str,
    player: str,
    state: dict[str, Any],
    log: EventLogger,
) -> None:
    directive_round = state.get("directive_round")
    if (
        not directive_round
        or state.get("saw_pending_round") == directive_round
        or board["round"] < directive_round
    ):
        return
    frame = next(
        (frame for frame in board["frames"] if frame.get("round") == directive_round),
        None,
    )
    if frame is None:
        return
    orders, battles, order_ok, battle_ok = audit_order_record(frame, player, state)
    state["saw_pending_round"] = directive_round
    state["pending_order_compliant"] = order_ok and battle_ok
    state["settled_order_recovered"] = True
    log(
        {
            "event": "settled_order_recovery",
            "round": directive_round,
            "target": state["target"],
            "invasion": state.get("invasion"),
            "order_ok": order_ok,
            "battle_ok": battle_ok,
            "orders": orders,
            "battles": battles,
        }
    )
    restore_directive(client, league, player, state, log)


def audit_settlement(
    board: dict[str, Any], player: str, state: dict[str, Any], log: EventLogger
) -> None:
    directive_round = state.get("directive_round")
    if not directive_round or state.get("settlement_audited_round") == directive_round:
        return
    frame = next(
        (frame for frame in board["frames"] if frame.get("round") == directive_round),
        None,
    )
    if frame is None:
        return
    target = state["target"]
    battles = [
        battle
        for battle in frame.get("battles") or []
        if battle.get("attacker") == player and battle.get("target") == target["cell"]
    ]
    width = board["config"]["width"]
    index = target["y"] * width + target["x"]
    owner_after = frame["owners"][index]
    invasion = state.get("invasion")
    invasion_owner_after = None
    invasion_captured = None
    if invasion:
        invasion_index = invasion["y"] * width + invasion["x"]
        invasion_owner_after = frame["owners"][invasion_index]
        invasion_captured = invasion_owner_after == player
    log(
        {
            "event": "settlement_audit",
            "round": directive_round,
            "target": target,
            "owner_after": owner_after,
            "captured": owner_after == player,
            "invasion": invasion,
            "invasion_owner_after": invasion_owner_after,
            "invasion_captured": invasion_captured,
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
    invasion = state.get("invasion")
    current = client.get_campaign_prompt(league, player_id=player).prompt
    base = without_directive(current)
    if hashlib.sha256(base.encode()).hexdigest() != state["base_prompt_sha256"]:
        raise RuntimeError("base prompt changed while directive was being armed")
    updated = (
        base
        + "\n\n"
        + directive(state["directive_round"], target, state["nonce"], invasion)
    )
    if len(updated) > 4000:
        raise RuntimeError(
            f"updated prompt is {len(updated)} chars; API maximum is 4000"
        )
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
            or not invasion_still_matches(fresh_board, player, invasion)
        ):
            raise RuntimeError("board changed while directive was being armed")
        if readback.prompt == updated and state["nonce"] in full.context:
            break
        if attempt == 7:
            raise RuntimeError(
                "prompt/full-prompt readback did not contain the exact directive"
            )
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
        or not invasion_still_matches(board, player, state.get("invasion"))
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
    had_directive = bool(state.get("directive_round"))
    recover_interrupted_arm(
        client, board, args.league, args.player, state, log, checkpoint
    )
    audit_conversation(client, args.league, args.player, state, log)
    audit_pending(client, board, args.league, args.player, state, log)
    recover_missed_pending_round(client, board, args.league, args.player, state, log)
    audit_settlement(board, args.player, state, log)
    state["analysis"] = refresh_analysis(
        client,
        board,
        args.league,
        args.player,
        state.get("analysis"),
        getattr(args, "stats_refresh_seconds", DEFAULT_STATS_REFRESH_SECONDS),
        log,
    )

    pending = board.get("pending_round")
    directive_round = state.get("directive_round")
    previous_settled = (
        directive_round is not None
        and directive_round <= board["round"]
        and state.get("saw_pending_round") == directive_round
        and state.get("pending_order_compliant") is True
        and (
            state.get("audit_compliant") is True
            or state.get("settled_order_recovered") is True
        )
    )
    initial_arm = not had_directive and args.arm_now
    if pending is None and (previous_settled or initial_arm):
        next_round = board["round"] + 1
        if state.get("directive_round") != next_round:
            previous_state = state
            target = choose_target(board, args.player, state["analysis"])
            invasion = choose_invasion(board, args.player, state["analysis"], target)
            current = client.get_campaign_prompt(args.league, player_id=args.player)
            base = without_directive(current.prompt)
            nonce = f"r{next_round}-{secrets.token_hex(8)}"
            state = {
                "phase": "arming",
                "directive_round": next_round,
                "board_round_when_written": board["round"],
                "target": target,
                "invasion": invasion,
                "nonce": nonce,
                "base_prompt_sha256": hashlib.sha256(base.encode()).hexdigest(),
                "written_at": now(),
                "analysis": previous_state["analysis"],
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
                    "invasion": invasion,
                    "invasion_threshold": DOUBLE_VICTORY_THRESHOLD,
                    "nonce": nonce,
                    "prompt_chars": state["prompt_chars"],
                }
            )
            message = (
                f"round {next_round}: saved airdrop {target['cell']} vs {target['owner_name']} "
                f"({target['map_ref']}/{target['mode']}, double={target['estimate']['double_victory_probability']:.1%})"
            )
            if invasion:
                message += (
                    f" plus invasion {invasion['from_cell']}->{invasion['cell']} vs {invasion['owner_name']} "
                    f"(double={invasion['estimate']['double_victory_probability']:.1%})"
                )
            print(message, flush=True)
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
    parser.add_argument(
        "--stats-refresh-seconds", type=float, default=DEFAULT_STATS_REFRESH_SECONDS
    )
    parser.add_argument(
        "--state", default="/tmp/stencil-campaign-order-controller/state.json"
    )
    parser.add_argument(
        "--log", default="/tmp/stencil-campaign-order-controller/events.jsonl"
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--arm-now",
        action="store_true",
        help="Allow the first directive without observing settlement",
    )
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
