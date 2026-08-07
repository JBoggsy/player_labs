#!/usr/bin/env python3
"""Fine-tune the initial cross-era semantic Qwen policy."""

from __future__ import annotations

import argparse
from pathlib import Path

from training import train


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--maps", type=Path, required=True)
    parser.add_argument("--validation-samples", type=Path)
    parser.add_argument("--validation-maps", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tuning", choices=("lora", "full"), default="lora")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--max-text-tokens", type=int, default=2048)
    parser.add_argument("--max-history-tokens", type=int, default=832)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mixed-precision", choices=("no", "fp16", "bf16"), default="no")
    parser.add_argument(
        "--action-change-weight",
        default="1",
        help="weight for changed control-slot targets, or 'balanced'",
    )
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--no-gradient-checkpointing", action="store_true")
    parser.add_argument("--log-every", type=int, default=10)
    args = parser.parse_args()
    if args.log_every <= 0:
        parser.error("--log-every must be positive")
    if (args.validation_samples is None) != (args.validation_maps is None):
        parser.error("--validation-samples and --validation-maps must be supplied together")
    if not 0 <= args.warmup_ratio < 1:
        parser.error("--warmup-ratio must be in [0, 1)")
    action_change_weight: float | str
    if args.action_change_weight == "balanced":
        action_change_weight = "balanced"
    else:
        try:
            action_change_weight = float(args.action_change_weight)
        except ValueError:
            parser.error("--action-change-weight must be positive or 'balanced'")
        if action_change_weight <= 0:
            parser.error("--action-change-weight must be positive or 'balanced'")
    train(
        args.samples,
        args.maps,
        args.output,
        validation_samples_path=args.validation_samples,
        validation_maps_path=args.validation_maps,
        tuning=args.tuning,
        epochs=args.epochs,
        batch_size=args.batch_size,
        gradient_accumulation=args.gradient_accumulation,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        max_text_tokens=args.max_text_tokens,
        max_history_tokens=args.max_history_tokens,
        seed=args.seed,
        mixed_precision=args.mixed_precision,
        action_change_weight=action_change_weight,
        resume_from=args.resume_from,
        gradient_checkpointing=not args.no_gradient_checkpointing,
        log_every=args.log_every,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
