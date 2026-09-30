# pw_ab_requests.py — A/B request bodies (compose only)

Part of the [lab tool index](README.md) (dispatcher: `pw.py ab-requests`).
`paintbot_pw_lab/tools/pw_ab_requests.py` prints the experience-request bodies an A/B design
needs. **It never calls the API.** Creating them is a separate, human-authorized step with the
shared helper, one body per call. Analysis: [compare.md](compare.md). Procedure:
[`paintbot-pw-ab`](../../.claude/skills/paintbot-pw-ab/SKILL.md).

## Command

```bash
uv run python paintbot_pw_lab/tools/pw_ab_requests.py --design paired|field \
    --baseline NAME:vN --candidate NAME:vM [--opponent NAME:vK ...] [--seeds 1-30] \
    [--episodes 1] (--league-id L | --division-id D | --coworld-id C [--variant-id V]) \
    [--private] [--run-id ID] [--out DIR]
```

Stdout: a manifest `{tool, design, run_id, baseline, candidate, opponents, requests:
[{label, arm, policy, side, opponent, seed, body}]}`. stderr: the request and episode
totals. `--out DIR` also writes `DIR/manifest.json` and `DIR/bodies/<label>.json` (the files
`experience_request.py create` takes). Keep the manifest: pass it to `compare.py --requests`.
Passing the same policy as `--baseline` and `--candidate` composes one arm only (evaluate one
policy, no duplicate requests). `--private` sets `private: true` (explicit opponents may then
get HTTP 409). `--run-id` defaults to the current local time, `%Y%m%dT%H%M%S`.

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py ab-requests ... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | `--design`, `--baseline`, `--candidate`, `--opponent` (repeat), `--seeds`, `--episodes`, a target (`--league-id`, `--division-id` or `--coworld-id [--variant-id]`), `--private`, `--run-id`, `--out` |
| Outputs | `--out DIR`: `manifest.json` and `bodies/<label>.json` |
| `--json` result | the manifest: `{tool, design, run_id, baseline, candidate, opponents, requests: [{label, arm, policy, side, opponent, seed, body}]}`; `counts.processed` = requests, `counts.episodes` = episodes in all. Without `--json` the manifest itself is printed |
| Exit codes | 0 composed; 2 usage, failure code `usage_error` (no target, `--design h2h` (refused), a paired design without `--seeds`, a paired/field design without `--opponent`, bad `--seeds`, an invalid body, e.g. `--episodes` outside 1–100) |
| Idempotence / cache | no API call. A fixed `--run-id` gives identical bodies and idempotency keys on rerun; the default run id is the current time |
| Typical next step | create each body with the shared experience-request helper (costs XP credits; within lab authorization), then stream artifacts and run `compare sprt` |

## What each body pins

- `roster`: 16 entries, each `{"player": {"policy_ref": ...}, "slot": s}`. Our policy on the
  seats with parity = side (0 red/Ember even, 1 blue/Azure odd), the opponent on the rest.
- `target`: the given league/division/coworld (+variant) ids, all inside `target`.
- `game_config_overrides: {"seed": S}` when `--seeds` is given; `num_episodes` = `--episodes`.
- `idempotency_key`: `pwab-<run_id>-<label>` (safe retries of one run; a new run needs a new id).
- `notes`: design, run id, policy, side, opponent and seed; `private` only with `--private`.

| Design | Requests |
| --- | --- |
| `paired` | arms × opponents × 2 sides × seeds (`--seeds` required) |
| `h2h` | **refused**: candidate vs baseline is hosted self-play, which `user_preferences.md` forbids. Screen h2h locally (`pw.py local screen … --seeds 1-20 --record DIR --record-seeds 1-20`, then `pw.py compare compare DIR --design h2h`). |
| `field` | arms × opponents × 2 sides (× seeds when given) |

An explicit `game_config_overrides.seed` reaches the engine, so every episode of that request
plays the same world ([docs/field.md § Seeds](../field.md#seeds-what-actually-reaches-the-engine)); with deterministic policies on both sides,
`--episodes` > 1 with a seed replays one game (compare.py drops the copies as
`duplicate_game`). Default: one episode per seed; use more seeds, not more episodes per seed.

## Verified / not verified

- Unit tests (`tools/tests/test_pw_compare.py`): 16 slots by parity, seed override, unique
  keys, the h2h self-play refusal, paired needs seeds, validation rejects a 15-seat roster.
- A composed body passed the shared helper's live top-level key check
  (`experience_request.py create BODY --check-schema`, 2026-09-29). Its game-override check
  got HTTP 429 and was not retried, so `seed` inside `game_config_overrides` is validated
  only against the documented schema (field.md), not live.
- No request has been created from these bodies.
