from types import SimpleNamespace

import cramjam
import numpy as np
import pytest
import torch

from actions import (
    FIRE,
    GRENADE,
    LEFT,
    RIGHT,
    TURN_CCW,
    TURN_CW,
    UP,
    ActionDecoder,
    BUTTONS,
    PRESS_TOKENS,
    RELEASE_TOKENS,
    action_event_tokens,
    action_text,
    canonical_action_mask,
    canonical_action_tokens,
    canonical_event_candidates,
)
from dataset import ActionChange, ActionTimeline, SFTSample, build_samples
from episode_map import EpisodeMap, decode_walkability_sprite
from evaluate_event_sft import empty_score, update_event_metrics
from evaluate_sft import update_metrics
from modeling import MapEncoderConfig, SpatialMapEncoder, adaptive_mean_pool2d
from measure_action_alignment import measure
from observation_text import EntitySnapshot, ObservationSnapshot
from training import PolicyCollator, resolve_action_change_weight


def test_action_round_trip_and_transition_edges() -> None:
    mask = UP | RIGHT | TURN_CCW | FIRE | GRENADE
    tokens = canonical_action_tokens(mask)
    assert tokens == (
        "<MOVE_NE>",
        "<TURN_CCW>",
        "<FIRE_HELD>",
        "<GRENADE_HELD>",
        "<STOP>",
    )

    decoder = ActionDecoder()
    pressed = decoder.decode(tokens)
    released = decoder.decode(canonical_action_tokens(0))
    assert pressed.mask == mask
    assert pressed.pressed_mask == mask
    assert released.released_mask == mask
    assert action_text(0) == (
        "<MOVE_IDLE><TURN_NONE><FIRE_RELEASED><GRENADE_RELEASED><STOP>"
    )


def test_event_action_codec_emits_only_canonical_transitions() -> None:
    previous = UP | FIRE
    target = RIGHT | FIRE | GRENADE
    tokens = action_event_tokens(previous, target)

    assert tokens == (
        "<UP_RELEASE>",
        "<RIGHT_PRESS>",
        "<GRENADE_PRESS>",
        "<STOP>",
    )
    decoded = ActionDecoder(previous).decode_events(tokens)
    assert decoded.mask == target
    assert decoded.released_mask == UP
    assert decoded.pressed_mask == RIGHT | GRENADE
    assert ActionDecoder(target).decode_events(("<STOP>",)).mask == target


def test_event_action_codec_rejects_redundant_or_contradictory_events() -> None:
    with pytest.raises(ValueError, match="does not change"):
        ActionDecoder(UP).decode_events(("<UP_PRESS>", "<STOP>"))
    with pytest.raises(ValueError, match="contradictory"):
        ActionDecoder(UP).decode_events(("<DOWN_PRESS>", "<STOP>"))


def test_every_event_target_follows_the_generation_grammar() -> None:
    masks = {canonical_action_mask(mask) for mask in range(256)}
    for previous in masks:
        for target in masks:
            mask = previous
            touched = 0
            press_phase = False
            release_from = 0
            press_from = 0
            for token in action_event_tokens(previous, target):
                assert token in canonical_event_candidates(
                    mask,
                    touched,
                    press_phase=press_phase,
                    release_from=release_from,
                    press_from=press_from,
                )
                if token == "<STOP>":
                    continue
                pressed = token in PRESS_TOKENS
                index = (
                    PRESS_TOKENS.index(token)
                    if pressed
                    else RELEASE_TOKENS.index(token)
                )
                bit = BUTTONS[index][0]
                touched |= bit
                mask ^= bit
                if pressed:
                    press_phase = True
                    press_from = index + 1
                else:
                    release_from = index + 1


def test_event_generation_grammar_excludes_out_of_order_events() -> None:
    after_fire_release = canonical_event_candidates(
        UP,
        FIRE,
        press_phase=False,
        release_from=BUTTONS.index((FIRE, "FIRE")) + 1,
        press_from=0,
    )
    assert "<UP_RELEASE>" not in after_fire_release

    after_fire_press = canonical_event_candidates(
        UP | FIRE,
        FIRE,
        press_phase=True,
        release_from=0,
        press_from=BUTTONS.index((FIRE, "FIRE")) + 1,
    )
    assert "<UP_RELEASE>" not in after_fire_press
    assert "<RIGHT_PRESS>" not in after_fire_press


def test_contradictory_controls_are_canonicalized() -> None:
    tokens = canonical_action_tokens(LEFT | RIGHT | TURN_CCW | TURN_CW)
    assert tokens[:2] == ("<MOVE_IDLE>", "<TURN_NONE>")


def test_decoder_rejects_wrong_slot_even_for_known_token() -> None:
    with pytest.raises(ValueError, match="invalid in this action slot"):
        ActionDecoder().decode(
            ("<TURN_NONE>", "<MOVE_IDLE>", "<FIRE_RELEASED>", "<GRENADE_RELEASED>", "<STOP>")
        )


def test_evaluation_tracks_persistence_and_changed_actions() -> None:
    score = {
        "samples": 0,
        "tokens": 0,
        "vocab_correct": 0,
        "constrained_correct": 0,
        "constrained_exact": 0,
        "autoregressive_correct": 0,
        "autoregressive_exact": 0,
        "previous_correct": 0,
        "previous_exact": 0,
        "changed_components": 0,
        "changed_component_correct": 0,
        "predicted_change_components": 0,
        "true_positive_changes": 0,
        "autoregressive_changed_component_correct": 0,
        "autoregressive_predicted_change_components": 0,
        "autoregressive_true_positive_changes": 0,
        "constrained_slot_correct": [0] * 5,
        "autoregressive_slot_correct": [0] * 5,
        "changed_samples": 0,
        "changed_tokens": 0,
        "constrained_changed_correct": 0,
        "constrained_changed_exact": 0,
        "autoregressive_changed_correct": 0,
        "autoregressive_changed_exact": 0,
    }
    labels = torch.tensor([1, 2, 3, 4, 5])
    previous = torch.tensor([1, 2, 0, 4, 5])
    predicted = torch.tensor([1, 2, 3, 0, 5])

    update_metrics(score, predicted, predicted, labels, labels, previous)

    assert score["changed_samples"] == 1
    assert score["previous_correct"] == 4
    assert score["previous_exact"] == 0
    assert score["constrained_changed_correct"] == 4
    assert score["constrained_changed_exact"] == 0
    assert score["autoregressive_exact"] == 1
    assert score["autoregressive_changed_exact"] == 1
    assert score["constrained_slot_correct"] == [1, 1, 1, 0, 1]
    assert score["changed_components"] == 1
    assert score["changed_component_correct"] == 1
    assert score["predicted_change_components"] == 2
    assert score["true_positive_changes"] == 1
    assert score["autoregressive_slot_correct"] == [1, 1, 1, 1, 1]


def test_event_evaluation_requires_a_valid_canonical_sequence() -> None:
    score = empty_score()
    update_event_metrics(
        score,
        teacher_forced_ids=torch.tensor([1, 2]),
        label_ids=torch.tensor([1, 2]),
        teacher_forced_tokens=("<UP_PRESS>", "<STOP>"),
        autoregressive_tokens=("<UP_PRESS>", "<STOP>"),
        previous_mask=0,
        target_mask=UP,
    )
    update_event_metrics(
        score,
        teacher_forced_ids=torch.tensor([3]),
        label_ids=torch.tensor([2]),
        teacher_forced_tokens=("<UP_PRESS>",),
        autoregressive_tokens=("<UP_PRESS>",),
        previous_mask=UP,
        target_mask=UP,
    )

    assert score["constrained_exact"] == 1
    assert score["constrained_changed_exact"] == 1
    assert score["invalid_sequences"] == 1
    assert score["teacher_forced_exact"] == 1
    assert score["teacher_forced_invalid_sequences"] == 1


def test_changed_component_weights_and_class_balance() -> None:
    observation = ObservationSnapshot(
        game_version="40",
        frame=10,
        map_width=20,
        map_height=20,
        entities=(EntitySnapshot(1, "self red right", 1, 2, 0, 0, 2, 2),),
        tick=10,
    ).to_dict()
    changed = SFTSample("a", "40", 0, 10, 10, "map", observation, 0, UP)
    held = SFTSample("b", "40", 0, 11, 11, "map", observation, 0, 0)

    assert resolve_action_change_weight([changed, held], "balanced") == 7
    assert resolve_action_change_weight([changed, held], 3) == 3

    tokenizer = SimpleNamespace(
        pad_token_id=0,
        encode=lambda text, add_special_tokens: (
            [10, 11, 12, 13, 14] if text.startswith("<MOVE") else [1, 2]
        ),
    )
    maps = {"map": EpisodeMap.from_mask(np.ones((20, 20), dtype=bool))}
    batch = PolicyCollator(tokenizer, maps, action_change_weight=3)([changed])

    assert batch["loss_weights"][0, -5:].tolist() == [3, 1, 1, 1, 1]

    event_tokenizer = SimpleNamespace(
        pad_token_id=0,
        encode=lambda text, add_special_tokens: (
            [20, 21] if text.startswith("<UP_PRESS>") else [1, 2]
        ),
    )
    event_batch = PolicyCollator(
        event_tokenizer, maps, action_encoding="events"
    )([changed])
    assert event_batch["labels"][0, -2:].tolist() == [20, 21]
    assert event_batch["loss_weights"][0, -2:].tolist() == [1, 1]

    def encode_with_long_prompt(text: str, add_special_tokens: bool) -> list[int]:
        if text.startswith("<UP_PRESS>"):
            return [20, 21]
        if text == "<STOP>":
            return [21]
        return list(range(100, 120))

    leak_safe_batch = PolicyCollator(
        SimpleNamespace(pad_token_id=0, encode=encode_with_long_prompt),
        maps,
        max_text_tokens=12,
        action_encoding="events",
    )([changed, held])
    assert (leak_safe_batch["labels"] != -100).sum(dim=1).tolist() == [2, 1]
    # Both prompts reserve the same worst-case nine-token action suffix. Their
    # visible lengths differ only by the emitted target, not by target-aware truncation.
    assert leak_safe_batch["attention_mask"].sum(dim=1).tolist() == [5, 4]


def test_episode_map_round_trip_and_sprite_decode() -> None:
    mask = np.array([[False, True, True], [True, False, True]], dtype=bool)
    item = EpisodeMap.from_mask(mask)
    assert np.array_equal(item.mask(), mask)
    assert EpisodeMap.from_dict(item.to_dict()) == item

    rgba = np.zeros((2, 3, 4), dtype=np.uint8)
    rgba[..., 3] = mask * 255
    sprite = SimpleNamespace(
        label="walkability map",
        width=3,
        height=2,
        data=bytes(cramjam.snappy.compress_raw(rgba.tobytes())),
    )
    assert decode_walkability_sprite(sprite).map_hash == item.map_hash


def test_dataset_alignment_keeps_previous_and_next_held_states() -> None:
    snapshot = ObservationSnapshot(
        game_version="40",
        frame=10,
        map_width=100,
        map_height=100,
        entities=(EntitySnapshot(1, "self red right", 10, 20, 0, 0, 10, 10),),
        tick=10,
    )
    timeline = ActionTimeline((ActionChange(3, FIRE), ActionChange(11, FIRE | UP)))
    sample = build_samples(
        [snapshot], timeline, replay_id="episode", pov=0, map_hash="abc"
    )[0]
    assert sample.observation_tick == 10
    assert sample.action_tick == 10
    assert sample.previous_mask == FIRE
    assert sample.target_mask == FIRE
    assert "previous_action" in sample.prompt()


def test_dataset_persists_only_bot_semantic_entities() -> None:
    snapshot = ObservationSnapshot(
        game_version="40",
        frame=10,
        map_width=100,
        map_height=100,
        entities=(
            EntitySnapshot(1, "self red right", 10, 20, 0, 0, 10, 10),
            EntitySnapshot(2, "fog", 0, 0, 0, 0, 100, 100),
            EntitySnapshot(3, "future useful item 7", 30, 40, 0, 0, 5, 5),
        ),
        tick=10,
    )

    sample = build_samples(
        [snapshot], ActionTimeline(()), replay_id="episode", pov=0, map_hash="abc"
    )[0]

    assert [entity["label"] for entity in sample.observation["entities"]] == [
        "self red right",
        "future useful item 7",
    ]


def test_map_encoder_has_fixed_token_budget_for_variable_maps() -> None:
    config = MapEncoderConfig(
        patch_stride=4, feature_channels=8, global_grid=2, local_grid=3, local_radius_cells=2
    )
    encoder = SpatialMapEncoder(lm_hidden_size=12, config=config)
    for shape, position in (((33, 41), (20.0, 15.0)), ((80, 20), (0.0, 79.0))):
        cache = encoder.encode_static(torch.ones(shape))
        assert encoder.gather(cache, position).shape == (1, 13, 12)


def test_portable_adaptive_pool_matches_pytorch() -> None:
    tensor = torch.arange(7 * 11, dtype=torch.float32).reshape(1, 1, 7, 11)
    expected = torch.nn.functional.adaptive_avg_pool2d(tensor, (3, 4))
    assert torch.allclose(adaptive_mean_pool2d(tensor, 3, 4), expected)


def test_alignment_measure_identifies_action_that_drives_next_observation() -> None:
    def snapshot(tick: int, aim: int) -> ObservationSnapshot:
        return ObservationSnapshot(
            game_version="40",
            frame=tick,
            map_width=100,
            map_height=100,
            entities=(
                EntitySnapshot(1, "self red right", 0, 0, 0, 0, 10, 10),
                EntitySnapshot(2, f"own aim {aim}", 0, 0, 0, 0, 1, 1),
            ),
            tick=tick,
        )

    timeline = ActionTimeline((ActionChange(10, TURN_CCW), ActionChange(11, 0)))
    result = measure([snapshot(10, 100), snapshot(11, 105)], timeline)
    assert result["offsets"][0]["accuracy"] == 1
    assert result["offsets"][1]["accuracy"] == 0
