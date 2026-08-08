from shard_expert_manifest import select_episodes


def episode(identifier: str, player: str) -> dict:
    return {
        "episode_id": identifier,
        "coworld_name": "ctf",
        "game_version": "41",
        "expert_policies": [{"player_id": player}],
    }


def test_limited_selection_retains_rare_expert_coverage() -> None:
    episodes = [episode(f"common-{index}", "common") for index in range(20)]
    episodes.append(episode("rare-only", "rare"))

    selected = select_episodes(episodes, maximum=2, seed=1)

    players = {
        policy["player_id"]
        for item in selected
        for policy in item["expert_policies"]
    }
    assert players == {"common", "rare"}


def test_unlimited_selection_preserves_every_episode() -> None:
    episodes = [episode("one", "a"), episode("two", "b")]

    assert select_episodes(episodes, maximum=None, seed=1) == episodes
