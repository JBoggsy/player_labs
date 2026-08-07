from observation_text import (
    EntitySnapshot,
    ObservationSnapshot,
    bot_semantic_observation,
    is_bot_semantic_label,
    serialize_observation,
    split_label_numbers,
)
from measure_observation_lengths import evenly_sample_by_version, era_for, percentile


def test_extracts_numeric_label_formats_without_losing_structure() -> None:
    normalized, values = split_label_numbers(
        "handicap red 250 hp 2 lives 4 map 3211x1713 zone -20,40 ratio 2/3"
    )

    assert normalized == (
        "handicap red {number_0} hp {number_1} lives {number_2} map "
        "{number_3}x{number_4} zone {number_5},{number_6} ratio "
        "{number_7}/{number_8}"
    )
    assert values == ("250", "2", "4", "3211", "1713", "-20", "40", "2", "3")


def test_serialization_is_canonical_and_map_normalized() -> None:
    snapshot = ObservationSnapshot(
        game_version="35",
        frame=12,
        map_width=100,
        map_height=200,
        entities=(
            EntitySnapshot(9, "player blue left", 70, 40, 3, 1, 10, 20),
            EntitySnapshot(4, "own aim 128", 0, 0, 0, 0, 1, 1),
            EntitySnapshot(7, "self red right", 10, 20, 2, 1, 10, 20),
        ),
    )

    lines = serialize_observation(snapshot).splitlines()

    assert lines[0] == 'observation game_version="35" frame=12 map_width=100 map_height=200'
    assert 'semantic="self red right"' in lines[1]
    assert "x_permille=150" in lines[1]
    assert "y_permille=150" in lines[1]
    assert "dx_permille=0" in lines[1]
    assert "dy_permille=0" in lines[1]
    assert 'semantic="own aim {number_0}"' in lines[2]
    assert 'label_numbers=["128"]' in lines[2]
    assert 'semantic="player blue left"' in lines[3]
    assert "dx_permille=600" in lines[3]
    assert "dy_permille=100" in lines[3]


def test_bot_semantic_filter_removes_only_source_defined_human_visuals() -> None:
    labels = (
        "fog",
        "splatter red stage 2",
        "hit splat blue stage 1",
        "damage pop green -2 stage 0",
        "shot impact",
        "brand new semantic item 17",
    )
    snapshot = ObservationSnapshot(
        game_version="40",
        frame=1,
        map_width=100,
        map_height=100,
        entities=tuple(
            EntitySnapshot(index, label, index, index, 0, 0, 1, 1)
            for index, label in enumerate(labels)
        ),
    )

    filtered = bot_semantic_observation(snapshot)

    assert [entity.label for entity in filtered.entities] == [
        "shot impact",
        "brand new semantic item 17",
    ]
    assert is_bot_semantic_label("future pickup 99")
    assert "fog" not in serialize_observation(snapshot)
    assert 'semantic="fog"' in serialize_observation(
        snapshot, include_human_visuals=True
    )


def test_length_audit_era_boundaries_and_balanced_sampling() -> None:
    versions = ("16", "17", "24", "25", "30", "31", "35", "36")
    assert [era_for(version) for version in versions] == [
        "gv01-16",
        "gv17-24",
        "gv17-24",
        "gv25-30",
        "gv25-30",
        "gv31-35",
        "gv31-35",
        "gv36+",
    ]
    assert percentile([5, 1, 9, 3], 0.5) == 3

    snapshots = [
        ObservationSnapshot(str(version), frame, 10, 10, ())
        for version in (16, 36)
        for frame in range(4)
    ]
    sampled = evenly_sample_by_version(snapshots, 2)

    assert [(item.game_version, item.frame) for item in sampled] == [
        ("16", 0),
        ("16", 2),
        ("36", 0),
        ("36", 2),
    ]
