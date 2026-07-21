"""A scripted vanilla_wow.nim_control.v1 server for tests and container smokes.

Speaks the real binary framing (KNRD magic, <IHHII header, JSON payloads) against the
real ``wow_sdk.nim_control`` client from the pinned SDK snapshot. Behavior: accepts one
goal, then offers frames at a fixed cadence; every selection settles successfully after
a short delay, moving the observed position to the selected destination.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time

FRAME_MAGIC = 0x44524E4B
FRAME_HEADER = struct.Struct("<IHHII")
FRAME_VERSION = 1
# Frame types (mirrors wow_sdk.nim_control)
GOAL_REQUEST = 1
CONTROL_DIRECTIVE = 2
ACTION_SELECTION = 3
STATUS_REQUEST = 4
CONTROL_STATUS = 5
ENVIRONMENT_FRAME = 6
ACTION_SETTLED = 7
CONTROL_ERROR = 8

PROTOCOL = "vanilla_wow.nim_control.v1"
ENV_PROTOCOL = "vanilla_wow.bot_environment.v1"


class FakeControlServer:
    """Single-client scripted controller. Start with .serve_forever() in a thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0, *, slot: int = 0) -> None:
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind((host, port))
        self._listener.listen(1)
        self.port = self._listener.getsockname()[1]
        self.slot = slot
        self.revision = 1
        self.frame_id = 0
        self.tick = 100
        self.position = [-618.5, -4251.7, 38.7]
        self.goal: dict | None = None
        self.selections: list[dict] = []
        self._pending_settlement: dict | None = None
        self._settled: dict | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ---- lifecycle ----
    def start(self) -> "FakeControlServer":
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        try:
            self._listener.close()
        except OSError:
            pass

    # ---- protocol ----
    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._listener.accept()
            except OSError:
                return
            with conn:
                try:
                    self._handle(conn)
                except (ConnectionError, OSError, struct.error):
                    continue

    def _handle(self, conn: socket.socket) -> None:
        while not self._stop.is_set():
            header = self._recv_exact(conn, FRAME_HEADER.size)
            if header is None:
                return
            magic, _version, frame_type, request_id, length = FRAME_HEADER.unpack(header)
            if magic != FRAME_MAGIC:
                return
            payload = json.loads(self._recv_exact(conn, length) or b"{}")
            self._settle_if_due()
            if frame_type == STATUS_REQUEST:
                if payload.get("include_action_settled"):
                    if self._settled is None:
                        self._send(
                            conn, CONTROL_ERROR, request_id,
                            {
                                "protocol": PROTOCOL, "type": "control_error",
                                "code": "no_settlement",
                                "message": "no action has settled yet",
                                "revision": self.revision,
                                "slot": self.slot, "tick": self.tick,
                            },
                        )
                    else:
                        self._send(conn, ACTION_SETTLED, request_id, self._settled)
                elif payload.get("include_environment_frame"):
                    self._send(conn, ENVIRONMENT_FRAME, request_id, self._frame())
                else:
                    self._send(conn, CONTROL_STATUS, request_id, self._status())
            elif frame_type == GOAL_REQUEST:
                self.goal = payload
                self.revision += 1
                self._send(conn, CONTROL_STATUS, request_id, self._status())
            elif frame_type == ACTION_SELECTION:
                self.selections.append(payload)
                action = payload.get("action", {})
                self._pending_settlement = {
                    "frame_id": payload.get("frame_id", self.frame_id),
                    "action": action,
                    "due": time.monotonic() + 0.2,
                }
                self._send(conn, CONTROL_STATUS, request_id, self._status())
            elif frame_type == CONTROL_DIRECTIVE:
                self._send(conn, CONTROL_STATUS, request_id, self._status())
            else:
                self._send(
                    conn,
                    CONTROL_ERROR,
                    request_id,
                    {
                        "protocol": PROTOCOL,
                        "type": "control_error",
                        "code": "unsupported",
                        "message": f"frame type {frame_type}",
                        "revision": self.revision,
                        "slot": self.slot,
                        "tick": self.tick,
                    },
                )

    def _settle_if_due(self) -> None:
        pending = self._pending_settlement
        if pending is None or time.monotonic() < pending["due"]:
            return
        action = pending["action"]
        destination = action.get("destination")
        if destination:
            self.position = [destination["x"], destination["y"], destination["z"]]
        self.tick += 5
        self._settled = {
            "protocol": PROTOCOL,
            "type": "action_settled",
            "revision": self.revision,
            "frame_id": pending["frame_id"],
            "action": action,
            "sequence": len(self.selections),
            "request_id": f"fake-{len(self.selections)}",
            "action_kind": action.get("kind", "noop"),
            "success": True,
            "message": "fake settlement",
            "settled_tick": self.tick,
            "slot": self.slot,
        }
        self._pending_settlement = None
        self.frame_id += 1

    def _status(self) -> dict:
        settling = self._pending_settlement is not None
        status = {
            "protocol": PROTOCOL,
            "type": "control_status",
            "revision": self.revision,
            "goal": {
                "id": (self.goal or {}).get("goal_id", ""),
                "kind": (self.goal or {}).get("goal_kind", "leveling"),
                "profile_id": "",
                "task_id": "",
                "role": "",
                "leader_name": "",
                "party_members": [],
                "stop_level": 0,
                "deadline_unix_seconds": 0.0,
                "practice_reset": False,
                "rfc_launch": False,
            },
            "phase": "executing" if settling else ("offered" if self.goal else "idle"),
            "frame_id": self.frame_id,
            "observed_tick": self.tick,
            "settled_tick": self._settled["settled_tick"] if self._settled else 0,
            "automatic_selection": (self.goal or {}).get("selection_mode") != "external",
            "override_active": False,
            "last_action": self._settled["action_kind"] if self._settled else "",
            "last_result": self._settled["message"] if self._settled else "",
            "attention": "",
            "action_ready": False,
            "recommended_action": None,
            "selected_action": None,
            "slot": self.slot,
            "tick": self.tick,
        }
        return status

    def _frame(self) -> dict:
        settling = self._pending_settlement is not None
        ready = self.goal is not None and not settling
        noop = {k: 0 for k in (
            "target", "spell", "item", "equipment_slot", "quest", "choice",
            "recipient", "text", "trigger", "dialog")}
        recommended = {"kind": "noop", **noop, "destination": None} if ready else None
        return {
            "protocol": ENV_PROTOCOL,
            "type": "environment_frame",
            "revision": self.revision,
            "frame_id": self.frame_id,
            "goal_id": (self.goal or {}).get("goal_id", ""),
            "phase": "offered" if ready else ("executing" if settling else "idle"),
            "observed_tick": self.tick,
            "observation": self._observation(),
            "bindings": {
                "entities": [], "spells": [], "items": [], "quests": [],
                "texts": [{"index": 1, "value": "wowborg random_walk starting"}],
                "triggers": [], "dialogs": [],
            },
            "action_space": self._action_space(),
            "action_mask": self._action_mask(),
            "action_ready": ready,
            "recommended_action": recommended,
            "navigation": {
                "owner": "vmangos_detour",
                "profile": "vmangos_player_ground_water",
                "include_flags": ["ground", "water"],
                "exclude_flags": ["steep"],
                "action_contract": "semantic_destination",
            },
            "previous_transition": self._settled,
            "slot": self.slot,
            "tick": self.tick,
        }

    def _observation(self) -> dict:
        x, y, z = self.position
        return {
            "tick": self.tick,
            "player_guid": "1000000",
            "name": "Smoketest",
            "class_id": 1,
            "level": 1,
            "xp_known": True, "xp": 0, "next_level_xp": 400,
            "location": {"map_id": 1, "x": x, "y": y, "z": z, "orientation": 0.0},
            "reached_route_node_ids": [],
            "health_known": True, "health": 60, "max_health": 60,
            "active_power_known": True, "active_power": 0, "active_max_power": 100,
            "base_mana_known": False, "base_mana": 0,
            "potion_cooldown_remaining_ms": 0,
            "in_combat": False,
            "active_cast_spell_id": 0, "active_channel_spell_id": 0,
            "active_pet_guid": "0", "active_pet_dead": False,
            "active_pet_health_known": False, "active_pet_health": 0,
            "active_pet_max_health": 0, "active_pet_target_guid": "0",
            "active_pet_happiness_known": False, "active_pet_happiness": "unknown",
            "active_pet_feed_pending": False,
            "auto_attack_guid": "0", "auto_repeat_spell_id": 0,
            "auto_repeat_target_guid": "0", "combat_focus_guid": "0",
            "environmental_damage_recent": False, "environmental_damage_type": 0,
            "is_dead": False, "is_ghost": False,
            "resurrect_offer_guid": "0",
            "corpse_known": False,
            "corpse_location": {"map_id": 0, "x": 0, "y": 0, "z": 0, "orientation": 0},
            "can_reclaim_corpse": False,
            "corpse_reclaim_failures": 0, "corpse_navigation_exhaustions": 0,
            "unsafe_corpse_reclaim_deaths": 0,
            "graveyard_known": False,
            "graveyard_location": {"map_id": 0, "x": 0, "y": 0, "z": 0, "orientation": 0},
            "known_spells": [], "cooldown_spell_ids": [], "active_aura_spell_ids": [],
            "eating": False, "drinking": False,
            "ranged_attack_usable_known": False, "ranged_attack_usable": False,
            "last_train_visit_level": 0,
            "copper_known": True, "copper": 0,
            "inventory_sell_count": 0,
            "bag_space_known": True, "free_bag_slots": 16, "backpack_free_slots": 16,
            "equipped_durability_known": False, "equipped_durability_worst_percent": 100,
            "repair_all_cost_known": False, "repair_all_cost": 0,
            "vendor_maintenance_recently": False,
            "exhausted_vendor_approach_guids": [],
            "hazardous_trainer_approach_guids": [],
            "equipment_upgrade": {
                "found": False, "item_guid": "0", "item_id": 0, "name": "",
                "equipment_slot": 0, "item_level": 0, "equipped_item_level": 0,
                "capacity_upgrade": False, "bag_slots": 0,
            },
            "party": {
                "in_group": False, "leader_guid": "0", "leader_name": "",
                "invite_pending": False, "invite_from": "", "members": [],
            },
            "units": [], "objects": [], "inventory_items": [], "equipment_items": [],
            "quest_objectives": [], "quest_log_progress": [],
            "used_quest_target_guids": [], "quest_log_quest_ids": [],
            "skipped_quest_ids": [], "unavailable_questgiver_guids": [],
            "completed_quest_ids": [], "rewarded_quest_ids": [],
        }

    # The v1 contract's fixed factor bounds (wow_sdk.nim_control constants).
    KINDS = (
        "noop", "move", "face", "target", "attack", "interact", "loot", "cast",
        "train_spell", "use_item", "release_spirit", "reclaim_corpse", "area_trigger",
        "sell_junk", "accept_quest", "turn_in_quest", "invite_party", "accept_party",
        "follow", "assist", "chat_say", "chat_yell", "chat_whisper", "chat_emote",
        "join_channel", "leave_channel", "channel_say", "add_friend", "remove_friend",
        "who_query", "guild_invite", "guild_accept", "guild_motd", "take_taxi",
        "bind_home", "interrupt_watch", "learn_talent", "buy_guild_charter",
        "sign_guild_charter", "offer_guild_charter", "turn_in_guild_charter",
        "spirit_healer_resurrect", "equip_item", "unequip_item", "stop_attack",
        "accept_resurrect", "pet_attack",
    )
    MAX_ENTITIES, MAX_SPELLS, MAX_ITEMS = 64, 128, 128
    MAX_EQUIP, MAX_QUESTS, MAX_CHOICE = 19, 32, 255
    MAX_TEXTS, MAX_TRIGGERS, MAX_DIALOGS = 32, 16, 16

    def _action_space(self) -> dict:
        return {
            "kinds": list(self.KINDS),
            "target_size": self.MAX_ENTITIES + 1,
            "spell_size": self.MAX_SPELLS + 1,
            "item_size": self.MAX_ITEMS + 1,
            "equipment_slot_size": self.MAX_EQUIP + 1,
            "quest_size": self.MAX_QUESTS + 1,
            "choice_size": self.MAX_CHOICE + 1,
            "recipient_size": self.MAX_TEXTS + 1,
            "text_size": self.MAX_TEXTS + 1,
            "trigger_size": self.MAX_TRIGGERS + 1,
            "dialog_size": self.MAX_DIALOGS + 1,
            "destination": "optional_world_point",
        }

    def _action_mask(self) -> dict:
        """Permissive mask in the exact fixed shapes: zero-index (unused) always legal,
        destinations legal for move, texts 0..N legal for chat_say."""
        n_kinds = len(self.KINDS)

        def per_kind(width: int, allow_nonzero: set[str] = frozenset()) -> list[list[bool]]:
            rows = []
            for kind in self.KINDS:
                row = [True] + [kind in allow_nonzero] * (width - 1)
                rows.append(row)
            return rows

        return {
            "kind": [True] * n_kinds,
            "target": per_kind(self.MAX_ENTITIES + 1),
            # spell mask is target-major: (entities+1) x (spells+1)
            "spell": [[True] + [False] * self.MAX_SPELLS
                      for _ in range(self.MAX_ENTITIES + 1)],
            "item": per_kind(self.MAX_ITEMS + 1),
            "equipment_slot": per_kind(self.MAX_EQUIP + 1),
            "quest": per_kind(self.MAX_QUESTS + 1),
            "choice": per_kind(self.MAX_CHOICE + 1),
            "recipient": per_kind(self.MAX_TEXTS + 1),
            "text": per_kind(self.MAX_TEXTS + 1, allow_nonzero={"chat_say"}),
            "trigger": per_kind(self.MAX_TRIGGERS + 1),
            "dialog": per_kind(self.MAX_DIALOGS + 1),
            "destination": [kind == "move" for kind in self.KINDS],
        }

    # ---- wire helpers ----
    def _send(self, conn: socket.socket, frame_type: int, request_id: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        conn.sendall(
            FRAME_HEADER.pack(FRAME_MAGIC, FRAME_VERSION, frame_type, request_id, len(body))
            + body
        )

    @staticmethod
    def _recv_exact(conn: socket.socket, count: int) -> bytes | None:
        data = b""
        while len(data) < count:
            chunk = conn.recv(count - len(data))
            if not chunk:
                return None
            data += chunk
        return data
