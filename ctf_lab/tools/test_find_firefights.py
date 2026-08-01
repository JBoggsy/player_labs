"""Focused synthetic checks for the replay-verified firefight detector."""

from __future__ import annotations

import json
import unittest

from find_firefights import DetectorConfig, detect_fights


def combat_row(
    *,
    seq: int,
    tick: int,
    slot: int,
    team: str,
    x: float,
    y: float,
    damage_slot: int | None = None,
    damage_team: str | None = None,
    amount: float = 0,
) -> dict:
    damages = []
    if damage_slot is not None:
        damages.append(
            {
                "slot": damage_slot,
                "team": damage_team,
                "amount": amount,
            }
        )
    action_id = 1000 + seq
    return {
        "episode_id": "ep",
        "seq": seq,
        "tick": tick,
        "slot": slot,
        "team": team,
        "key": "shot_impact",
        "value": json.dumps(
            {
                "action_id": action_id,
                "x": x,
                "y": y,
                "damages": damages,
            }
        ),
    }


class FirefightDetectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = DetectorConfig()

    def test_quick_reciprocal_duel_is_a_firefight(self) -> None:
        rows = [
            combat_row(seq=0, tick=10, slot=0, team="red", x=100, y=100),
            combat_row(seq=1, tick=12, slot=1, team="blue", x=130, y=100),
            combat_row(seq=2, tick=15, slot=0, team="red", x=100, y=100),
            combat_row(seq=3, tick=17, slot=1, team="blue", x=130, y=100),
            combat_row(seq=4, tick=20, slot=0, team="red", x=100, y=100),
        ]
        fights = detect_fights(rows, self.config)
        self.assertEqual(len(fights), 1)
        self.assertEqual(fights[0]["actions"], 5)
        self.assertEqual(fights[0]["scale"], "duel")

    def test_one_sided_fusillade_is_not_a_firefight(self) -> None:
        rows = [
            combat_row(seq=i, tick=10 + i, slot=0, team="red", x=100, y=100)
            for i in range(8)
        ]
        self.assertEqual(detect_fights(rows, self.config), [])

    def test_simultaneous_remote_fights_stay_separate(self) -> None:
        rows = []
        seq = 0
        for base_x, red_slot, blue_slot in ((100, 0, 1), (900, 2, 3)):
            for offset, slot, team in (
                (0, red_slot, "red"),
                (2, blue_slot, "blue"),
                (4, red_slot, "red"),
                (6, blue_slot, "blue"),
                (8, red_slot, "red"),
            ):
                rows.append(
                    combat_row(
                        seq=seq,
                        tick=100 + offset,
                        slot=slot,
                        team=team,
                        x=base_x,
                        y=100,
                    )
                )
                seq += 1
        fights = detect_fights(rows, self.config)
        self.assertEqual(len(fights), 2)

    def test_damage_and_breadth_raise_weight(self) -> None:
        duel = [
            combat_row(seq=0, tick=10, slot=0, team="red", x=100, y=100),
            combat_row(seq=1, tick=12, slot=1, team="blue", x=130, y=100),
            combat_row(seq=2, tick=15, slot=0, team="red", x=100, y=100),
            combat_row(seq=3, tick=17, slot=1, team="blue", x=130, y=100),
            combat_row(seq=4, tick=20, slot=0, team="red", x=100, y=100),
        ]
        teamfight = [
            combat_row(
                seq=i,
                tick=10 + i * 2,
                slot=(i % 4) * 2 if i % 2 == 0 else (i % 4) * 2 + 1,
                team="red" if i % 2 == 0 else "blue",
                x=100 + i,
                y=100,
                damage_slot=1 if i % 2 == 0 else 0,
                damage_team="blue" if i % 2 == 0 else "red",
                amount=20,
            )
            for i in range(12)
        ]
        self.assertGreater(
            detect_fights(teamfight, self.config)[0]["weight"],
            detect_fights(duel, self.config)[0]["weight"],
        )


if __name__ == "__main__":
    unittest.main()
