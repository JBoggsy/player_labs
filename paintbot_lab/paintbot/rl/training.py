"""Accelerate SFT loop with validation, scheduling, and resumable state."""

from __future__ import annotations

import random
import time
import json
import math
import shutil
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, Sampler

from actions import canonical_action_tokens
from corpus_store import load_arrow_dataset
from dataset import SFTSample, read_maps, read_samples
from modeling import SemanticPolicyModel, load_base_model, save_policy


class PolicyDataset(Dataset):
    def __init__(self, samples_path: Path, maps_path: Path, indices_path: Path | None = None) -> None:
        self.samples = None
        self.arrow = None
        if samples_path.is_dir():
            self.arrow = load_arrow_dataset(samples_path)
        else:
            self.samples = read_samples(samples_path)
        self.indices = np.load(indices_path, mmap_mode="r") if indices_path else None
        self.maps = read_maps(maps_path)
        if self.samples is not None:
            missing = {sample.map_hash for sample in self.samples} - self.maps.keys()
            if missing:
                raise ValueError(f"samples reference missing maps: {sorted(missing)}")

    def __len__(self) -> int:
        if self.indices is not None:
            return len(self.indices)
        return len(self.samples) if self.samples is not None else len(self.arrow)

    def __getitem__(self, index: int) -> SFTSample:
        if self.indices is not None:
            index = int(self.indices[index])
        if self.samples is not None:
            return self.samples[index]
        return SFTSample.from_dict(json.loads(self.arrow[index]["sample_json"]))

    def __iter__(self):
        for index in range(len(self)):
            yield self[index]


class EpochSampler(Sampler[int]):
    """Deterministic per-epoch shuffle so a mid-epoch resume can skip safely."""

    def __init__(self, dataset: Dataset, seed: int) -> None:
        self.dataset = dataset
        self.seed = seed
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __iter__(self):
        generator = torch.Generator().manual_seed(self.seed + self.epoch)
        yield from torch.randperm(len(self.dataset), generator=generator).tolist()

    def __len__(self) -> int:
        return len(self.dataset)


class PolicyCollator:
    def __init__(
        self,
        tokenizer,
        maps,
        *,
        max_text_tokens: int = 2048,
        action_change_weight: float = 1.0,
        max_history_tokens: int = 832,
    ) -> None:
        self.tokenizer = tokenizer
        self.maps = maps
        self.max_text_tokens = max_text_tokens
        self.action_change_weight = action_change_weight
        self.max_history_tokens = max_history_tokens

    def __call__(self, samples: list[SFTSample]) -> dict:
        encoded: list[tuple[list[int], list[int], list[float]]] = []
        for sample in samples:
            target_ids = self.tokenizer.encode(sample.target(), add_special_tokens=False)
            prompt_ids = self._prompt_ids(sample, len(target_ids))
            prompt_ids = prompt_ids[: max(0, self.max_text_tokens - len(target_ids))]
            previous = canonical_action_tokens(sample.previous_mask)
            target = canonical_action_tokens(sample.target_mask)
            target_weights = [
                self.action_change_weight if slot < 4 and target[slot] != previous[slot] else 1.0
                for slot in range(5)
            ]
            encoded.append(
                (
                    prompt_ids + target_ids,
                    [-100] * len(prompt_ids) + target_ids,
                    [0.0] * len(prompt_ids) + target_weights,
                )
            )

        width = max(len(ids) for ids, _, _ in encoded)
        input_ids = []
        labels = []
        loss_weights = []
        attention = []
        for ids, target, weights in encoded:
            padding = width - len(ids)
            input_ids.append(ids + [self.tokenizer.pad_token_id] * padding)
            labels.append(target + [-100] * padding)
            loss_weights.append(weights + [0.0] * padding)
            attention.append([1] * len(ids) + [0] * padding)
        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
            "loss_weights": torch.tensor(loss_weights, dtype=torch.float32),
            "attention_mask": torch.tensor(attention, dtype=torch.long),
            "maps": [torch.from_numpy(self.maps[item.map_hash].mask()).float() for item in samples],
            "positions": [item.position() for item in samples],
        }

    def _prompt_ids(self, sample: SFTSample, target_length: int) -> list[int]:
        if not sample.history:
            return self.tokenizer.encode(sample.prompt(), add_special_tokens=False)
        history, observation, suffix = sample.prompt_parts()
        history_ids = self.tokenizer.encode(history + "\n", add_special_tokens=False)
        observation_ids = self.tokenizer.encode(observation + "\n", add_special_tokens=False)
        suffix_ids = self.tokenizer.encode(suffix, add_special_tokens=False)
        budget = max(0, self.max_text_tokens - target_length)
        if len(suffix_ids) >= budget:
            return suffix_ids[-budget:]
        history_budget = min(self.max_history_tokens, budget - len(suffix_ids))
        # The most recent deltas are at the end of the history serialization.
        history_ids = history_ids[-history_budget:]
        observation_budget = budget - len(suffix_ids) - len(history_ids)
        return history_ids + observation_ids[:observation_budget] + suffix_ids


def train(
    samples_path: Path,
    maps_path: Path,
    output: Path,
    *,
    validation_samples_path: Path | None = None,
    validation_maps_path: Path | None = None,
    sample_indices_path: Path | None = None,
    validation_indices_path: Path | None = None,
    tuning: str = "lora",
    epochs: int = 1,
    batch_size: int = 1,
    gradient_accumulation: int = 8,
    learning_rate: float | None = None,
    weight_decay: float = 0.01,
    warmup_ratio: float = 0.03,
    max_text_tokens: int = 2048,
    max_history_tokens: int = 832,
    seed: int = 1,
    gradient_checkpointing: bool = True,
    mixed_precision: str = "no",
    action_change_weight: float | str = 1.0,
    lora_rank: int = 8,
    lora_target_modules: str = "attention",
    resume_from: Path | None = None,
    log_every: int = 10,
    checkpoint_every_updates: int = 0,
    keep_step_checkpoints: int = 2,
) -> None:
    from accelerate import Accelerator
    from transformers import get_scheduler

    random.seed(seed)
    torch.manual_seed(seed)
    started = time.monotonic()
    accelerator = Accelerator(
        gradient_accumulation_steps=gradient_accumulation,
        mixed_precision=None if mixed_precision == "no" else mixed_precision,
    )
    tokenizer, model = load_base_model(
        tuning=tuning,
        lora_rank=lora_rank,
        lora_target_modules=lora_target_modules,
    )
    if gradient_checkpointing:
        model.language_model.gradient_checkpointing_enable()
        model.language_model.enable_input_require_grads()
        model.language_model.config.use_cache = False
    dataset = PolicyDataset(samples_path, maps_path, sample_indices_path)
    if not len(dataset):
        raise ValueError("training dataset is empty")
    resolved_action_change_weight = resolve_action_change_weight(
        dataset, action_change_weight
    )
    sampler = EpochSampler(dataset, seed)
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        sampler=sampler,
        collate_fn=PolicyCollator(
            tokenizer,
            dataset.maps,
            max_text_tokens=max_text_tokens,
            action_change_weight=resolved_action_change_weight,
            max_history_tokens=max_history_tokens,
        ),
    )
    validation_dataset = None
    validation_loader = None
    if validation_samples_path is not None or validation_maps_path is not None:
        if validation_samples_path is None or validation_maps_path is None:
            raise ValueError("validation samples and maps must be supplied together")
        validation_dataset = PolicyDataset(
            validation_samples_path, validation_maps_path, validation_indices_path
        )
        if len(validation_dataset):
            validation_loader = DataLoader(
                validation_dataset,
                batch_size=batch_size,
                shuffle=False,
                collate_fn=PolicyCollator(
                    tokenizer,
                    validation_dataset.maps,
                    max_text_tokens=max_text_tokens,
                    max_history_tokens=max_history_tokens,
                ),
            )
    resolved_learning_rate = learning_rate or (2e-4 if tuning == "lora" else 2e-5)
    optimizer = torch.optim.AdamW(
        (parameter for parameter in model.parameters() if parameter.requires_grad),
        lr=resolved_learning_rate,
        weight_decay=weight_decay,
    )
    updates_per_epoch = math.ceil(len(loader) / gradient_accumulation)
    total_updates = max(1, updates_per_epoch * epochs)
    scheduler = get_scheduler(
        "cosine",
        optimizer=optimizer,
        num_warmup_steps=round(total_updates * warmup_ratio),
        num_training_steps=total_updates,
    )
    if validation_loader is None:
        model, optimizer, loader, scheduler = accelerator.prepare(
            model, optimizer, loader, scheduler
        )
    else:
        model, optimizer, loader, validation_loader, scheduler = accelerator.prepare(
            model, optimizer, loader, validation_loader, scheduler
        )
    start_epoch = 0
    start_batch = 0
    global_updates = 0
    best_validation_loss = float("inf")
    best_epoch = None
    if resume_from is not None:
        accelerator.load_state(resume_from)
        state_path = resume_from / "training_state.json"
        if not state_path.exists():
            raise FileNotFoundError(f"resume state has no {state_path.name}: {resume_from}")
        saved_state = json.loads(state_path.read_text())
        start_epoch = int(saved_state.get("epoch", saved_state["completed_epochs"]))
        start_batch = int(saved_state.get("completed_batches_in_epoch", 0))
        global_updates = int(saved_state.get("global_updates", 0))
        if saved_state.get("best_validation_loss") is not None:
            best_validation_loss = float(saved_state["best_validation_loss"])
        best_epoch = saved_state.get("best_epoch")
    history = []
    for epoch in range(start_epoch, epochs):
        sampler.set_epoch(epoch)
        model.train()
        epoch_loader = (
            accelerator.skip_first_batches(loader, start_batch)
            if epoch == start_epoch and start_batch
            else loader
        )
        for step, batch in enumerate(epoch_loader, start=start_batch + 1):
            with accelerator.accumulate(model):
                loss = model(**batch).loss
                accelerator.backward(loss)
                optimizer.step()
                if accelerator.sync_gradients:
                    scheduler.step()
                    global_updates += 1
                optimizer.zero_grad()
            reduced_loss = accelerator.reduce(loss.detach(), reduction="mean").item()
            history.append(
                {
                    "epoch": epoch + 1,
                    "step": step,
                    "loss": reduced_loss,
                    "learning_rate": scheduler.get_last_lr()[0],
                }
            )
            if accelerator.is_main_process and step % log_every == 0:
                print(f"epoch={epoch + 1} step={step} loss={reduced_loss:.6f}", flush=True)
            if (
                checkpoint_every_updates
                and accelerator.sync_gradients
                and global_updates % checkpoint_every_updates == 0
            ):
                save_training_state(
                    accelerator,
                    output,
                    name=f"step-{global_updates}",
                    completed_epochs=epoch,
                    epoch=epoch,
                    completed_batches_in_epoch=step,
                    global_updates=global_updates,
                    best_validation_loss=best_validation_loss,
                    best_epoch=best_epoch,
                )
                if accelerator.is_main_process:
                    prune_step_checkpoints(output, keep_step_checkpoints)
        start_batch = 0
        validation_loss = None
        if validation_loader is not None:
            model.eval()
            losses = []
            with torch.no_grad():
                for batch in validation_loader:
                    losses.append(
                        accelerator.reduce(model(**batch).loss.detach(), reduction="mean").item()
                    )
            validation_loss = sum(losses) / len(losses)
            history.append({"epoch": epoch + 1, "validation_loss": validation_loss})
            if accelerator.is_main_process:
                print(
                    f"epoch={epoch + 1} validation_loss={validation_loss:.6f}", flush=True
                )
                if validation_loss < best_validation_loss:
                    best_validation_loss = validation_loss
                    best_epoch = epoch + 1
                    save_policy(
                        accelerator.unwrap_model(model), tokenizer, output / "best", tuning
                    )
        save_training_state(
            accelerator,
            output,
            name=f"epoch-{epoch + 1}",
            completed_epochs=epoch + 1,
            epoch=epoch + 1,
            completed_batches_in_epoch=0,
            global_updates=global_updates,
            best_validation_loss=best_validation_loss,
            best_epoch=best_epoch,
        )
    accelerator.wait_for_everyone()
    if accelerator.is_main_process:
        unwrapped: SemanticPolicyModel = accelerator.unwrap_model(model)
        save_policy(unwrapped, tokenizer, output, tuning)
        (output / "training_run.json").write_text(
            json.dumps(
                {
                    "samples": len(dataset),
                    "validation_samples": len(validation_dataset) if validation_dataset else 0,
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "gradient_accumulation": gradient_accumulation,
                    "learning_rate": resolved_learning_rate,
                    "weight_decay": weight_decay,
                    "warmup_ratio": warmup_ratio,
                    "max_text_tokens": max_text_tokens,
                    "max_history_tokens": max_history_tokens,
                    "seed": seed,
                    "tuning": tuning,
                    "gradient_checkpointing": gradient_checkpointing,
                    "mixed_precision": mixed_precision,
                    "action_change_weight": action_change_weight,
                    "resolved_action_change_weight": resolved_action_change_weight,
                    "lora_rank": lora_rank if tuning == "lora" else None,
                    "lora_target_modules": (
                        lora_target_modules if tuning == "lora" else None
                    ),
                    "sample_indices": str(sample_indices_path) if sample_indices_path else None,
                    "validation_indices": (
                        str(validation_indices_path) if validation_indices_path else None
                    ),
                    "checkpoint_every_updates": checkpoint_every_updates,
                    "resumed_from": str(resume_from) if resume_from else None,
                    "best_validation_loss": (
                        best_validation_loss if best_validation_loss != float("inf") else None
                    ),
                    "best_epoch": best_epoch,
                    "device": str(accelerator.device),
                    "duration_seconds": time.monotonic() - started,
                    "history": history,
                },
                indent=2,
            )
            + "\n"
        )


def save_training_state(
    accelerator,
    output: Path,
    *,
    name: str,
    completed_epochs: int,
    epoch: int,
    completed_batches_in_epoch: int,
    global_updates: int,
    best_validation_loss: float,
    best_epoch: int | None,
) -> None:
    state_output = output / "trainer_state" / name
    accelerator.save_state(state_output)
    if accelerator.is_main_process:
        (state_output / "training_state.json").write_text(
            json.dumps(
                {
                    "completed_epochs": completed_epochs,
                    "epoch": epoch,
                    "completed_batches_in_epoch": completed_batches_in_epoch,
                    "global_updates": global_updates,
                    "best_validation_loss": (
                        best_validation_loss
                        if best_validation_loss != float("inf")
                        else None
                    ),
                    "best_epoch": best_epoch,
                }
            )
            + "\n"
        )


def prune_step_checkpoints(output: Path, keep: int) -> None:
    checkpoints = sorted(
        (output / "trainer_state").glob("step-*"),
        key=lambda path: int(path.name.removeprefix("step-")),
    )
    for checkpoint in checkpoints[: max(0, len(checkpoints) - keep)]:
        shutil.rmtree(checkpoint)


def resolve_action_change_weight(samples: Iterable[SFTSample], configured: float | str) -> float:
    if configured != "balanced":
        weight = float(configured)
        if weight <= 0:
            raise ValueError("action_change_weight must be positive")
        return weight

    changed = 0
    unchanged = 0
    for sample in samples:
        previous = canonical_action_tokens(sample.previous_mask)
        target = canonical_action_tokens(sample.target_mask)
        for slot in range(4):
            if target[slot] == previous[slot]:
                unchanged += 1
            else:
                changed += 1
    if not changed:
        raise ValueError("cannot class-balance a dataset with no action changes")
    return unchanged / changed
