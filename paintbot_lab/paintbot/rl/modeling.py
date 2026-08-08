"""Qwen policy wrapper with a once-per-episode convolutional map cache."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import torch
from torch import nn
from torch.nn import functional as F

from actions import ACTION_TOKEN_SLOTS, ACTION_TOKENS, STOP_TOKEN


MODEL_ID = "Qwen/Qwen3-0.6B-Base"
MODEL_REVISION = "da87bfb608c14b7cf20ba1ce41287e8de496c0cd"


@dataclass(frozen=True)
class MapEncoderConfig:
    """Conservative baseline dimensions; all remain experiment knobs."""

    patch_stride: int = 8
    feature_channels: int = 32
    global_grid: int = 4
    local_grid: int = 4
    local_radius_cells: int = 8

    @property
    def token_count(self) -> int:
        return self.global_grid**2 + self.local_grid**2


@dataclass
class StaticMapCache:
    feature_grid: torch.Tensor
    global_features: torch.Tensor
    map_width: int
    map_height: int


class SpatialMapEncoder(nn.Module):
    def __init__(self, lm_hidden_size: int, config: MapEncoderConfig | None = None) -> None:
        super().__init__()
        self.config = config or MapEncoderConfig()
        channels = self.config.feature_channels
        stride = self.config.patch_stride
        self.backbone = nn.Sequential(
            nn.Conv2d(1, channels, kernel_size=stride, stride=stride),
            nn.GELU(),
            nn.Conv2d(channels, channels, kernel_size=3, padding=1),
            nn.GELU(),
        )
        self.projection = nn.Linear(channels, lm_hidden_size)
        self.position = nn.Parameter(torch.zeros(self.config.token_count, lm_hidden_size))
        nn.init.normal_(self.position, std=0.02)

    def encode_static(self, mask: torch.Tensor) -> StaticMapCache:
        """Run convolutions once. Mask shape is [height, width]."""
        if mask.ndim != 2:
            raise ValueError("map mask must have shape [height, width]")
        features = self.backbone(mask.to(dtype=self.backbone[0].weight.dtype)[None, None])
        global_features = adaptive_mean_pool2d(
            features, self.config.global_grid, self.config.global_grid
        )
        return StaticMapCache(
            feature_grid=features,
            global_features=global_features,
            map_width=mask.shape[1],
            map_height=mask.shape[0],
        )

    def gather(self, cache: StaticMapCache, position: tuple[float, float]) -> torch.Tensor:
        """Gather fresh local tokens from cached features at the current position."""
        _, _, feature_height, feature_width = cache.feature_grid.shape
        x = min(feature_width - 1, max(0, int(position[0] * feature_width / cache.map_width)))
        y = min(feature_height - 1, max(0, int(position[1] * feature_height / cache.map_height)))
        radius = self.config.local_radius_cells
        padded = F.pad(cache.feature_grid, (radius, radius, radius, radius))
        local = padded[:, :, y : y + 2 * radius + 1, x : x + 2 * radius + 1]
        local = adaptive_mean_pool2d(local, self.config.local_grid, self.config.local_grid)
        features = torch.cat((cache.global_features.flatten(2), local.flatten(2)), dim=2)
        tokens = self.projection(features.transpose(1, 2))
        return tokens + self.position[None]

    def forward(self, mask: torch.Tensor, position: tuple[float, float]) -> torch.Tensor:
        return self.gather(self.encode_static(mask), position)


def adaptive_mean_pool2d(tensor: torch.Tensor, rows: int, columns: int) -> torch.Tensor:
    """Adaptive average pooling using primitive means supported by MPS."""
    height, width = tensor.shape[-2:]
    pooled_rows = []
    for row in range(rows):
        top = row * height // rows
        bottom = ((row + 1) * height + rows - 1) // rows
        pooled_columns = []
        for column in range(columns):
            left = column * width // columns
            right = ((column + 1) * width + columns - 1) // columns
            pooled_columns.append(
                tensor[..., top:bottom, left:right].mean(dim=(-2, -1), keepdim=True)
            )
        pooled_rows.append(torch.cat(pooled_columns, dim=-1))
    return torch.cat(pooled_rows, dim=-2)


class SemanticPolicyModel(nn.Module):
    def __init__(self, language_model: nn.Module, map_config: MapEncoderConfig | None = None) -> None:
        super().__init__()
        self.language_model = language_model
        self.map_encoder = SpatialMapEncoder(language_model.config.hidden_size, map_config)
        self.map_encoder.to(dtype=language_model.get_input_embeddings().weight.dtype)

    def forward(
        self,
        *,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: torch.Tensor,
        loss_weights: torch.Tensor | None = None,
        maps: Sequence[torch.Tensor],
        positions: Sequence[tuple[float, float]],
    ):
        token_embeddings = self.language_model.get_input_embeddings()(input_ids)
        map_embeddings = torch.cat(
            [self.map_encoder(mask, position) for mask, position in zip(maps, positions, strict=True)]
        )
        inputs_embeds = torch.cat((map_embeddings, token_embeddings), dim=1)
        map_attention = attention_mask.new_ones((attention_mask.shape[0], map_embeddings.shape[1]))
        map_labels = labels.new_full((labels.shape[0], map_embeddings.shape[1]), -100)
        combined_labels = torch.cat((map_labels, labels), dim=1)
        output = self.language_model(
            inputs_embeds=inputs_embeds,
            attention_mask=torch.cat((map_attention, attention_mask), dim=1),
            labels=combined_labels,
        )
        if loss_weights is not None:
            map_weights = loss_weights.new_zeros(
                (loss_weights.shape[0], map_embeddings.shape[1])
            )
            combined_weights = torch.cat((map_weights, loss_weights), dim=1)
            shifted_labels = combined_labels[:, 1:].contiguous()
            token_losses = F.cross_entropy(
                output.logits[:, :-1].contiguous().view(-1, output.logits.shape[-1]),
                shifted_labels.view(-1),
                ignore_index=-100,
                reduction="none",
            ).view_as(shifted_labels)
            shifted_weights = combined_weights[:, 1:]
            valid_weights = shifted_weights * (shifted_labels != -100)
            output.loss = (token_losses * valid_weights).sum() / valid_weights.sum()
        return output

    @torch.no_grad()
    def greedy_action(
        self,
        tokenizer,
        prompt_ids: torch.Tensor,
        map_cache: StaticMapCache,
        position: tuple[float, float],
    ) -> tuple[str, str, str, str, str]:
        """Constrained baseline decoding; deliberately simple, with no KV cache yet."""
        map_embeddings = self.map_encoder.gather(map_cache, position)
        text_embeddings = self.language_model.get_input_embeddings()(prompt_ids)
        embeddings = torch.cat((map_embeddings, text_embeddings), dim=1)
        generated: list[str] = []
        for allowed in (*ACTION_TOKEN_SLOTS, (STOP_TOKEN,)):
            logits = self.language_model(inputs_embeds=embeddings).logits[0, -1]
            allowed_ids = torch.tensor(
                [tokenizer.convert_tokens_to_ids(token) for token in allowed],
                device=logits.device,
            )
            selected_id = allowed_ids[torch.argmax(logits[allowed_ids])]
            token = tokenizer.convert_ids_to_tokens(selected_id.item())
            generated.append(token)
            next_embedding = self.language_model.get_input_embeddings()(selected_id.reshape(1, 1))
            embeddings = torch.cat((embeddings, next_embedding), dim=1)
        return tuple(generated)  # type: ignore[return-value]


def load_base_model(*, tuning: str = "lora", dtype: torch.dtype | None = None):
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    tokenizer.add_special_tokens({"additional_special_tokens": list(ACTION_TOKENS)})
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    language_model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        torch_dtype=dtype or "auto",
    )
    language_model.resize_token_embeddings(len(tokenizer))
    if tuning == "lora":
        action_token_ids = [tokenizer.convert_tokens_to_ids(token) for token in ACTION_TOKENS]
        language_model = get_peft_model(
            language_model,
            LoraConfig(
                r=8,
                lora_alpha=16,
                lora_dropout=0.05,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                trainable_token_indices={"embed_tokens": action_token_ids},
                task_type="CAUSAL_LM",
            ),
        )
    elif tuning != "full":
        raise ValueError("tuning must be 'lora' or 'full'")
    return tokenizer, SemanticPolicyModel(language_model)


def save_policy(model: SemanticPolicyModel, tokenizer, output: Path, tuning: str) -> None:
    import json

    output.mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(output / "tokenizer")
    save_kwargs = {"save_embedding_layers": False} if tuning == "lora" else {}
    model.language_model.save_pretrained(
        output / ("adapter" if tuning == "lora" else "model"), **save_kwargs
    )
    torch.save(model.map_encoder.state_dict(), output / "map_encoder.pt")
    (output / "policy_config.json").write_text(
        json.dumps(
            {
                "model_id": MODEL_ID,
                "model_revision": MODEL_REVISION,
                "tuning": tuning,
                "map_encoder": asdict(model.map_encoder.config),
            },
            indent=2,
        )
        + "\n"
    )


def load_policy(output: Path, *, device: torch.device):
    import json

    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    config = json.loads((output / "policy_config.json").read_text())
    tokenizer = AutoTokenizer.from_pretrained(output / "tokenizer")
    if config["tuning"] == "lora":
        language_model = AutoModelForCausalLM.from_pretrained(
            config["model_id"], revision=config["model_revision"], torch_dtype="auto"
        )
        language_model.resize_token_embeddings(len(tokenizer))
        language_model = PeftModel.from_pretrained(language_model, output / "adapter")
    else:
        language_model = AutoModelForCausalLM.from_pretrained(output / "model")
    model = SemanticPolicyModel(language_model, MapEncoderConfig(**config["map_encoder"]))
    model.map_encoder.load_state_dict(
        torch.load(output / "map_encoder.pt", map_location="cpu", weights_only=True)
    )
    model.to(device).eval()
    return tokenizer, model
