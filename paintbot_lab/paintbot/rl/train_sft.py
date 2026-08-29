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
    parser.add_argument("--sample-indices", type=Path)
    parser.add_argument("--validation-indices", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tuning", choices=("lora", "full"), default="lora")
    parser.add_argument("--lora-rank", type=int, default=8)
    parser.add_argument(
        "--lora-target-modules",
        choices=("attention", "all-linear"),
        default="attention",
    )
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument(
        "--schedule-epochs",
        type=int,
        help="LR schedule horizon; defaults to --epochs and may be longer for a staged run",
    )
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--max-text-tokens", type=int, default=2048)
    parser.add_argument("--max-history-tokens", type=int, default=832)
    parser.add_argument("--spatial-semantics", action="store_true")
    parser.add_argument(
        "--action-encoding", choices=("absolute", "events"), default="absolute"
    )
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
    parser.add_argument("--checkpoint-every-updates", type=int, default=0)
    parser.add_argument("--keep-step-checkpoints", type=int, default=2)
    args = parser.parse_args()
    if args.log_every <= 0:
        parser.error("--log-every must be positive")
    if args.lora_rank <= 0:
        parser.error("--lora-rank must be positive")
    if args.schedule_epochs is not None and args.schedule_epochs < args.epochs:
        parser.error("--schedule-epochs cannot be less than --epochs")
    if (args.validation_samples is None) != (args.validation_maps is None):
        parser.error("--validation-samples and --validation-maps must be supplied together")
    if args.validation_indices is not None and args.validation_samples is None:
        parser.error("--validation-indices requires --validation-samples")
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
        sample_indices_path=args.sample_indices,
        validation_indices_path=args.validation_indices,
        tuning=args.tuning,
        epochs=args.epochs,
        schedule_epochs=args.schedule_epochs,
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
        lora_rank=args.lora_rank,
        lora_target_modules=args.lora_target_modules,
        include_spatial_semantics=args.spatial_semantics,
        action_encoding=args.action_encoding,
        resume_from=args.resume_from,
        gradient_checkpointing=not args.no_gradient_checkpointing,
        log_every=args.log_every,
        checkpoint_every_updates=args.checkpoint_every_updates,
        keep_step_checkpoints=args.keep_step_checkpoints,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
