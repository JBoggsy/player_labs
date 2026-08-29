import torch
from transformers import Qwen3Config, Qwen3ForCausalLM

from actions import (
    ACTION_TOKEN_SLOTS,
    ACTION_TOKENS,
    BUTTONS,
    EVENT_TOKENS,
    PRESS_TOKENS,
    RELEASE_TOKENS,
    STOP_TOKEN,
    canonical_action_mask,
    canonical_event_candidates,
)
from modeling import MapEncoderConfig, SemanticPolicyModel


class Tokenizer:
    def __init__(self, token_ids: dict[str, int]) -> None:
        self.token_ids = token_ids
        self.tokens = {token_id: token for token, token_id in token_ids.items()}

    def convert_tokens_to_ids(self, token: str) -> int:
        return self.token_ids[token]

    def convert_ids_to_tokens(self, token_id: int) -> str:
        return self.tokens[token_id]


def tiny_policy():
    torch.manual_seed(7)
    language_model = Qwen3ForCausalLM(
        Qwen3Config(
            vocab_size=64,
            hidden_size=32,
            intermediate_size=64,
            num_hidden_layers=2,
            num_attention_heads=4,
            num_key_value_heads=2,
            head_dim=8,
            max_position_embeddings=128,
        )
    )
    policy = SemanticPolicyModel(
        language_model,
        MapEncoderConfig(
            patch_stride=2,
            feature_channels=4,
            global_grid=1,
            local_grid=1,
            local_radius_cells=1,
        ),
    ).eval()
    prompt_ids = torch.tensor([[0, 1, 2, 3]])
    map_cache = policy.map_encoder.encode_static(torch.ones((8, 8)))
    embeddings = torch.cat(
        (
            policy.map_encoder.gather(map_cache, (4.0, 4.0)),
            language_model.get_input_embeddings()(prompt_ids),
        ),
        dim=1,
    )
    with torch.no_grad():
        logits = language_model(
            inputs_embeds=embeddings, use_cache=False, logits_to_keep=1
        ).logits[0, -1]
    ranked_ids = torch.argsort(logits, descending=True).tolist()
    stop_id = ranked_ids[-1]
    available = [token_id for token_id in ranked_ids if token_id != stop_id]
    tokens = (*EVENT_TOKENS, *(token for token in ACTION_TOKENS if token != STOP_TOKEN))
    token_ids = {
        token: token_id
        for token, token_id in zip(tokens, available[: len(tokens)], strict=True)
    }
    token_ids[STOP_TOKEN] = stop_id
    return policy, Tokenizer(token_ids), prompt_ids, map_cache


def uncached_action(policy, tokenizer, prompt_ids, map_cache):
    map_embeddings = policy.map_encoder.gather(map_cache, (4.0, 4.0))
    text_embeddings = policy.language_model.get_input_embeddings()(prompt_ids)
    embeddings = torch.cat((map_embeddings, text_embeddings), dim=1)
    generated = []
    for allowed in ACTION_TOKEN_SLOTS:
        logits = policy.language_model(
            inputs_embeds=embeddings, use_cache=False, logits_to_keep=1
        ).logits[0, -1]
        allowed_ids = torch.tensor(
            [tokenizer.convert_tokens_to_ids(token) for token in allowed]
        )
        selected_id = allowed_ids[torch.argmax(logits[allowed_ids])]
        generated.append(tokenizer.convert_ids_to_tokens(int(selected_id)))
        embeddings = torch.cat(
            (
                embeddings,
                policy.language_model.get_input_embeddings()(
                    selected_id.reshape(1, 1)
                ),
            ),
            dim=1,
        )
    return (*generated, STOP_TOKEN)


def uncached_event_action(policy, tokenizer, prompt_ids, map_cache, previous_mask):
    map_embeddings = policy.map_encoder.gather(map_cache, (4.0, 4.0))
    text_embeddings = policy.language_model.get_input_embeddings()(prompt_ids)
    embeddings = torch.cat((map_embeddings, text_embeddings), dim=1)
    mask = canonical_action_mask(previous_mask)
    touched = 0
    press_phase = False
    release_from = 0
    press_from = 0
    generated = []
    for _ in BUTTONS:
        allowed = canonical_event_candidates(
            mask,
            touched,
            press_phase=press_phase,
            release_from=release_from,
            press_from=press_from,
        )
        logits = policy.language_model(
            inputs_embeds=embeddings, use_cache=False, logits_to_keep=1
        ).logits[0, -1]
        allowed_ids = torch.tensor(
            [tokenizer.convert_tokens_to_ids(token) for token in allowed]
        )
        selected_id = allowed_ids[torch.argmax(logits[allowed_ids])]
        token = tokenizer.convert_ids_to_tokens(int(selected_id))
        generated.append(token)
        if token == STOP_TOKEN:
            return tuple(generated)
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
        embeddings = torch.cat(
            (
                embeddings,
                policy.language_model.get_input_embeddings()(
                    selected_id.reshape(1, 1)
                ),
            ),
            dim=1,
        )
    return (*generated, STOP_TOKEN)


def test_cached_absolute_decoding_matches_full_prefix_recomputation() -> None:
    policy, tokenizer, prompt_ids, map_cache = tiny_policy()

    expected = uncached_action(policy, tokenizer, prompt_ids, map_cache)
    actual = policy.greedy_action(tokenizer, prompt_ids, map_cache, (4.0, 4.0))

    assert actual == expected


def test_batched_cached_absolute_decoding_matches_individual_decoding() -> None:
    policy, tokenizer, prompt_ids, map_cache = tiny_policy()
    second_prompt = prompt_ids.flip(dims=(1,))

    expected = (
        policy.greedy_action(tokenizer, prompt_ids, map_cache, (4.0, 4.0)),
        policy.greedy_action(tokenizer, second_prompt, map_cache, (3.0, 5.0)),
    )
    actual = policy.greedy_actions(
        tokenizer,
        torch.cat((prompt_ids, second_prompt)),
        (map_cache, map_cache),
        ((4.0, 4.0), (3.0, 5.0)),
    )

    assert actual == expected


def test_evaluation_logit_slice_matches_full_forward() -> None:
    policy, _, prompt_ids, _ = tiny_policy()
    labels = torch.tensor([[-100, -100, -100, -100, 4, 5, 6, 7, 8]])
    inputs = torch.tensor([[0, 1, 2, 3, 4, 5, 6, 7, 8]])
    kwargs = {
        "input_ids": inputs,
        "attention_mask": torch.ones_like(inputs),
        "labels": labels,
        "loss_weights": torch.ones_like(inputs, dtype=torch.float32),
        "maps": (torch.ones((8, 8)),),
        "positions": ((4.0, 4.0),),
    }

    with torch.no_grad():
        full = policy(**kwargs)
        sliced = policy(**kwargs, logits_to_keep=6)

    torch.testing.assert_close(sliced.logits, full.logits[:, -6:])
    torch.testing.assert_close(sliced.loss, full.loss)


def test_cached_event_decoding_matches_full_prefix_recomputation() -> None:
    policy, tokenizer, prompt_ids, map_cache = tiny_policy()

    expected = uncached_event_action(policy, tokenizer, prompt_ids, map_cache, 0)
    actual = policy.greedy_event_action(
        tokenizer, prompt_ids, map_cache, (4.0, 4.0), 0
    )

    assert len(expected) > 1
    assert actual == expected
