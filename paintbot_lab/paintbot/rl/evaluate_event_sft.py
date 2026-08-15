#!/usr/bin/env python3
"""Evaluate teacher-forced press/release event prediction on canonical actions."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import torch

from actions import (
    EVENT_ACTION_TOKENS,
    ActionDecoder,
    canonical_action_mask,
    canonical_action_tokens,
)
from evaluate_sft import evaluation_device
from modeling import load_policy
from training import PolicyCollator, PolicyDataset


def empty_score() -> dict:
    return {
        "samples": 0,
        "tokens": 0,
        "constrained_correct": 0,
        "constrained_exact": 0,
        "previous_exact": 0,
        "invalid_sequences": 0,
        "constrained_slot_correct": [0] * 5,
        "changed_samples": 0,
        "constrained_changed_exact": 0,
    }


def update_event_metrics(
    score: dict,
    *,
    predicted_ids: torch.Tensor,
    label_ids: torch.Tensor,
    predicted_tokens: tuple[str, ...],
    previous_mask: int,
    target_mask: int,
) -> None:
    previous = canonical_action_mask(previous_mask)
    target = canonical_action_mask(target_mask)
    changed = previous != target
    sequence_exact = torch.equal(predicted_ids, label_ids)
    try:
        predicted_mask = ActionDecoder(previous).decode_events(predicted_tokens).mask
    except ValueError:
        predicted_mask = None

    score["samples"] += 1
    score["tokens"] += label_ids.numel()
    score["constrained_correct"] += (predicted_ids == label_ids).sum().item()
    score["previous_exact"] += not changed
    score["invalid_sequences"] += predicted_mask is None
    # Canonical target order makes token-sequence exact a conservative action-exact
    # criterion; decoding also guards against malformed event combinations.
    action_exact = sequence_exact and predicted_mask == target
    score["constrained_exact"] += action_exact
    target_slots = canonical_action_tokens(target)
    predicted_slots = (
        canonical_action_tokens(predicted_mask)
        if predicted_mask is not None
        else (None,) * 5
    )
    for slot, (predicted, label) in enumerate(
        zip(predicted_slots, target_slots, strict=True)
    ):
        score["constrained_slot_correct"][slot] += predicted == label
    if changed:
        score["changed_samples"] += 1
        score["constrained_changed_exact"] += action_exact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--maps", type=Path, required=True)
    parser.add_argument("--sample-indices", type=Path)
    parser.add_argument("--max-text-tokens", type=int, default=2048)
    parser.add_argument("--spatial-semantics", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    device = evaluation_device()
    tokenizer, model = load_policy(args.checkpoint, device=device)
    if model.action_encoding != "events":
        parser.error("checkpoint does not use event action encoding")
    dataset = PolicyDataset(args.samples, args.maps, args.sample_indices)
    collator = PolicyCollator(
        tokenizer,
        dataset.maps,
        max_text_tokens=args.max_text_tokens,
        include_spatial_semantics=args.spatial_semantics,
        action_encoding="events",
    )
    allowed_ids = torch.tensor(
        [tokenizer.convert_tokens_to_ids(token) for token in EVENT_ACTION_TOKENS],
        device=device,
    )
    totals = defaultdict(empty_score)
    with torch.no_grad():
        for sample in dataset:
            batch = collator([sample])
            batch = {
                key: [item.to(device) for item in value]
                if key == "maps"
                else value.to(device)
                if torch.is_tensor(value)
                else value
                for key, value in batch.items()
            }
            output = model(**batch)
            shifted_labels = torch.cat(
                (
                    batch["labels"].new_full(
                        (1, model.map_encoder.config.token_count), -100
                    ),
                    batch["labels"],
                ),
                dim=1,
            )[:, 1:]
            selected = shifted_labels != -100
            labels = shifted_labels[selected]
            selected_logits = output.logits[:, :-1][selected]
            constrained = allowed_ids[
                torch.argmax(selected_logits[:, allowed_ids], dim=1)
            ]
            tokens = tuple(
                tokenizer.convert_ids_to_tokens(int(token_id))
                for token_id in constrained
            )
            for key in ("all", sample.game_version):
                update_event_metrics(
                    totals[key],
                    predicted_ids=constrained,
                    label_ids=labels,
                    predicted_tokens=tokens,
                    previous_mask=sample.previous_mask,
                    target_mask=sample.target_mask,
                )

    result = {
        "device": str(device),
        "max_text_tokens": args.max_text_tokens,
        "include_spatial_semantics": args.spatial_semantics,
        "action_encoding": "events",
        "groups": {},
    }
    for key, score in totals.items():
        result["groups"][key] = {
            **score,
            "constrained_token_accuracy": score["constrained_correct"]
            / score["tokens"],
            "constrained_exact_action_accuracy": score["constrained_exact"]
            / score["samples"],
            "constrained_slot_accuracy": dict(
                zip(
                    ("movement", "turn", "fire", "grenade", "stop"),
                    (
                        correct / score["samples"]
                        for correct in score["constrained_slot_correct"]
                    ),
                    strict=True,
                )
            ),
            "previous_mask_exact_action_accuracy": score["previous_exact"]
            / score["samples"],
            "changed_action_samples": score["changed_samples"],
            "constrained_changed_exact_action_accuracy": (
                score["constrained_changed_exact"] / score["changed_samples"]
                if score["changed_samples"]
                else None
            ),
        }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
