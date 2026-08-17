#!/usr/bin/env python3
"""Evaluate autoregressive actions plus teacher-forced diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

from actions import ACTION_TOKEN_SLOTS, STOP_TOKEN, canonical_action_tokens
from evaluation_uncertainty import replay_cluster_bootstrap
from modeling import load_policy
from training import PolicyCollator, PolicyDataset


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(path: Path) -> str:
    if not path.is_dir():
        raise ValueError(f"checkpoint is not a directory: {path}")
    digest = hashlib.sha256()
    files = sorted(item for item in path.rglob("*") if item.is_file())
    if not files:
        raise ValueError(f"checkpoint contains no files: {path}")
    for item in files:
        digest.update(item.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        with item.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def dataset_fingerprint(dataset: PolicyDataset, samples_path: Path) -> str:
    if dataset.arrow is not None:
        return str(dataset.arrow._fingerprint)
    return sha256_file(samples_path)


def maps_fingerprint(maps: dict) -> str:
    """Bind the validated map set without re-hashing multi-gigabyte rasters."""
    digest = hashlib.sha256()
    for map_hash in sorted(maps):
        digest.update(map_hash.encode())
        digest.update(b"\n")
    return digest.hexdigest()


def update_sample_fingerprint(digest, sample) -> None:
    payload = json.dumps(
        asdict(sample), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    digest.update(len(payload).to_bytes(8, "little"))
    digest.update(payload)


def evaluation_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def update_metrics(
    score: dict, predicted, constrained, autoregressive, labels, previous
) -> None:
    """Accumulate model scores alongside the held-action persistence baseline."""
    changed = not torch.equal(previous, labels)
    score["samples"] += 1
    score["tokens"] += labels.numel()
    score["vocab_correct"] += (predicted == labels).sum().item()
    score["constrained_correct"] += (constrained == labels).sum().item()
    score["constrained_exact"] += torch.equal(constrained, labels)
    score["autoregressive_correct"] += (autoregressive == labels).sum().item()
    score["autoregressive_exact"] += torch.equal(autoregressive, labels)
    score["previous_correct"] += (previous == labels).sum().item()
    score["previous_exact"] += not changed
    target_changes = previous[:4] != labels[:4]
    predicted_changes = previous[:4] != constrained[:4]
    autoregressive_changes = previous[:4] != autoregressive[:4]
    score["changed_components"] += target_changes.sum().item()
    score["changed_component_correct"] += (
        (constrained[:4] == labels[:4]) & target_changes
    ).sum().item()
    score["predicted_change_components"] += predicted_changes.sum().item()
    score["true_positive_changes"] += (target_changes & predicted_changes).sum().item()
    score["autoregressive_changed_component_correct"] += (
        (autoregressive[:4] == labels[:4]) & target_changes
    ).sum().item()
    score["autoregressive_predicted_change_components"] += (
        autoregressive_changes.sum().item()
    )
    score["autoregressive_true_positive_changes"] += (
        target_changes & autoregressive_changes
    ).sum().item()
    for slot, correct in enumerate((constrained == labels).tolist()):
        score["constrained_slot_correct"][slot] += correct
    for slot, correct in enumerate((autoregressive == labels).tolist()):
        score["autoregressive_slot_correct"][slot] += correct
    if changed:
        score["changed_samples"] += 1
        score["changed_tokens"] += labels.numel()
        score["constrained_changed_correct"] += (constrained == labels).sum().item()
        score["constrained_changed_exact"] += torch.equal(constrained, labels)
        score["autoregressive_changed_correct"] += (
            autoregressive == labels
        ).sum().item()
        score["autoregressive_changed_exact"] += torch.equal(
            autoregressive, labels
        )


@torch.no_grad()
def decode_autoregressive_batch(model, tokenizer, collator, device, rows) -> None:
    """Fill equal-length rows using the policy's padding-free batch decoder."""
    prompt_ids = torch.from_numpy(np.stack([row["prompt_ids"] for row in rows])).to(
        device=device, dtype=torch.long
    )
    map_caches = []
    positions = []
    for row in rows:
        map_tensor = torch.from_numpy(collator.maps[row["map_hash"]].mask()).float()
        map_caches.append(model.map_encoder.encode_static(map_tensor.to(device)))
        positions.append(row["position"])
    if len(rows) == 1:
        generated = (
            model.greedy_action(tokenizer, prompt_ids, map_caches[0], positions[0]),
        )
    else:
        generated = model.greedy_actions(tokenizer, prompt_ids, map_caches, positions)
    for row, tokens in zip(rows, generated, strict=True):
        row["autoregressive"] = torch.tensor(
            [tokenizer.convert_tokens_to_ids(token) for token in tokens]
        )
        del row["prompt_ids"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--maps", type=Path, required=True)
    parser.add_argument("--sample-indices", type=Path)
    parser.add_argument("--max-text-tokens", type=int, default=2048)
    parser.add_argument("--autoregressive-batch-size", type=int, default=8)
    parser.add_argument("--spatial-semantics", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--logits-out",
        type=Path,
        help="Optional compressed per-example action logits for validation-only calibration",
    )
    args = parser.parse_args()
    if args.autoregressive_batch_size <= 0:
        parser.error("--autoregressive-batch-size must be positive")

    device = evaluation_device()
    tokenizer, model = load_policy(args.checkpoint, device=device)
    if model.action_encoding != "absolute":
        parser.error("checkpoint does not use absolute action encoding")
    dataset = PolicyDataset(args.samples, args.maps, args.sample_indices)
    collator = PolicyCollator(
        tokenizer,
        dataset.maps,
        max_text_tokens=args.max_text_tokens,
        include_spatial_semantics=args.spatial_semantics,
    )
    totals = defaultdict(
        lambda: {
            "samples": 0,
            "loss": 0.0,
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
    )
    allowed_ids = [
        torch.tensor(
            [tokenizer.convert_tokens_to_ids(token) for token in allowed], device=device
        )
        for allowed in (*ACTION_TOKEN_SLOTS, (STOP_TOKEN,))
    ]
    logit_rows: list[np.ndarray] = []
    previous_rows: list[np.ndarray] = []
    label_rows: list[np.ndarray] = []
    replay_ids: list[str] = []
    game_versions: list[str] = []
    selected_samples_digest = hashlib.sha256()
    replay_outcomes: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    evaluation_rows = []
    pending_by_length: dict[int, list[dict]] = defaultdict(list)
    with torch.no_grad():
        for sample in dataset:
            update_sample_fingerprint(selected_samples_digest, sample)
            batch = collator([sample])
            batch = {
                key: [item.to(device) for item in value] if key == "maps" else value.to(device) if torch.is_tensor(value) else value
                for key, value in batch.items()
            }
            target_length = len(ACTION_TOKEN_SLOTS) + 1
            output = model(**batch, logits_to_keep=target_length + 1)
            labels = batch["labels"][:, -target_length:].reshape(-1)
            selected_logits = output.logits[:, -target_length - 1 : -1].reshape(
                target_length, -1
            )
            predicted = selected_logits.argmax(dim=-1)
            constrained = torch.stack(
                [ids[torch.argmax(logits[ids])] for logits, ids in zip(selected_logits, allowed_ids, strict=True)]
            )
            prompt_ids = collator._prompt_ids(sample, target_length)
            prompt_ids = prompt_ids[
                : max(0, args.max_text_tokens - target_length)
            ]
            previous = torch.tensor(
                [
                    tokenizer.convert_tokens_to_ids(token)
                    for token in canonical_action_tokens(sample.previous_mask)
                ],
                device=device,
            )
            if args.logits_out:
                width = max(len(ids) for ids in allowed_ids)
                row = np.full((len(allowed_ids), width), -np.inf, dtype=np.float32)
                for slot, (logits, ids) in enumerate(
                    zip(selected_logits, allowed_ids, strict=True)
                ):
                    row[slot, : len(ids)] = logits[ids].float().cpu().numpy()
                logit_rows.append(row)
                previous_rows.append(previous.cpu().numpy())
                label_rows.append(labels.cpu().numpy())
                replay_ids.append(sample.replay_id)
                game_versions.append(sample.game_version)
            row = {
                "replay_id": sample.replay_id,
                "game_version": sample.game_version,
                "map_hash": sample.map_hash,
                "position": sample.position(),
                "prompt_ids": np.asarray(prompt_ids, dtype=np.int32),
                "loss": output.loss.item(),
                "predicted": predicted.cpu(),
                "constrained": constrained.cpu(),
                "labels": labels.cpu(),
                "previous": previous.cpu(),
            }
            evaluation_rows.append(row)
            pending = pending_by_length[len(prompt_ids)]
            pending.append(row)
            if len(pending) == args.autoregressive_batch_size:
                decode_autoregressive_batch(
                    model, tokenizer, collator, device, pending
                )
                pending.clear()
        for pending in pending_by_length.values():
            if pending:
                decode_autoregressive_batch(model, tokenizer, collator, device, pending)

    for row in evaluation_rows:
        autoregressive = row["autoregressive"]
        labels = row["labels"]
        replay_outcome = replay_outcomes[row["replay_id"]]
        replay_outcome[0] += int(torch.equal(autoregressive, labels))
        replay_outcome[1] += 1
        for key in ("all", row["game_version"]):
            score = totals[key]
            score["loss"] += row["loss"]
            update_metrics(
                score,
                row["predicted"],
                row["constrained"],
                autoregressive,
                labels,
                row["previous"],
            )

    result = {
        "device": str(device),
        "max_text_tokens": args.max_text_tokens,
        "autoregressive_batch_size": args.autoregressive_batch_size,
        "checkpoint_sha256": sha256_tree(args.checkpoint),
        "sample_dataset_fingerprint": dataset_fingerprint(dataset, args.samples),
        "selected_samples_sha256": selected_samples_digest.hexdigest(),
        "sample_indices_sha256": (
            sha256_file(args.sample_indices) if args.sample_indices else None
        ),
        "maps_fingerprint": maps_fingerprint(dataset.maps),
        "maps_count": len(dataset.maps),
        "include_spatial_semantics": args.spatial_semantics,
        "action_encoding": "absolute",
        "autoregressive_exact_action_cluster_bootstrap": replay_cluster_bootstrap(
            {key: tuple(value) for key, value in replay_outcomes.items()}
        ),
        "groups": {},
    }
    for key, score in totals.items():
        result["groups"][key] = {
            **score,
            "mean_loss": score["loss"] / score["samples"],
            "vocab_token_accuracy": score["vocab_correct"] / score["tokens"],
            "constrained_token_accuracy": score["constrained_correct"] / score["tokens"],
            "constrained_exact_action_accuracy": score["constrained_exact"] / score["samples"],
            "teacher_forced_constrained_exact_action_accuracy": score[
                "constrained_exact"
            ]
            / score["samples"],
            "autoregressive_token_accuracy": score["autoregressive_correct"]
            / score["tokens"],
            "autoregressive_exact_action_accuracy": score["autoregressive_exact"]
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
            "autoregressive_slot_accuracy": dict(
                zip(
                    ("movement", "turn", "fire", "grenade", "stop"),
                    (
                        correct / score["samples"]
                        for correct in score["autoregressive_slot_correct"]
                    ),
                    strict=True,
                )
            ),
            "previous_mask_token_accuracy": score["previous_correct"] / score["tokens"],
            "previous_mask_exact_action_accuracy": score["previous_exact"] / score["samples"],
            "changed_component_accuracy": (
                score["changed_component_correct"] / score["changed_components"]
                if score["changed_components"]
                else None
            ),
            "change_precision": (
                score["true_positive_changes"] / score["predicted_change_components"]
                if score["predicted_change_components"]
                else None
            ),
            "change_recall": (
                score["true_positive_changes"] / score["changed_components"]
                if score["changed_components"]
                else None
            ),
            "autoregressive_changed_component_accuracy": (
                score["autoregressive_changed_component_correct"]
                / score["changed_components"]
                if score["changed_components"]
                else None
            ),
            "autoregressive_change_precision": (
                score["autoregressive_true_positive_changes"]
                / score["autoregressive_predicted_change_components"]
                if score["autoregressive_predicted_change_components"]
                else None
            ),
            "autoregressive_change_recall": (
                score["autoregressive_true_positive_changes"]
                / score["changed_components"]
                if score["changed_components"]
                else None
            ),
            "changed_action_samples": score["changed_samples"],
            "constrained_changed_token_accuracy": (
                score["constrained_changed_correct"] / score["changed_tokens"]
                if score["changed_tokens"]
                else None
            ),
            "constrained_changed_exact_action_accuracy": (
                score["constrained_changed_exact"] / score["changed_samples"]
                if score["changed_samples"]
                else None
            ),
            "autoregressive_changed_exact_action_accuracy": (
                score["autoregressive_changed_exact"] / score["changed_samples"]
                if score["changed_samples"]
                else None
            ),
        }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
    if args.logits_out:
        args.logits_out.parent.mkdir(parents=True, exist_ok=True)
        token_ids = np.full(
            (len(allowed_ids), max(len(ids) for ids in allowed_ids)), -1, dtype=np.int64
        )
        valid_counts = np.asarray([len(ids) for ids in allowed_ids], dtype=np.int64)
        for slot, ids in enumerate(allowed_ids):
            token_ids[slot, : len(ids)] = ids.cpu().numpy()
        np.savez_compressed(
            args.logits_out,
            logits=np.stack(logit_rows),
            previous=np.stack(previous_rows),
            labels=np.stack(label_rows),
            token_ids=token_ids,
            valid_counts=valid_counts,
            replay_ids=np.asarray(replay_ids),
            game_versions=np.asarray(game_versions),
        )
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
