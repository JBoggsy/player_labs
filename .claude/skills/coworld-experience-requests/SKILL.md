---
name: coworld-experience-requests
description: "Create and monitor hosted Coworld evaluation batches against selected opponents. Resolve the live target and versions, compose a question-driven request, create within existing authorization, and stream artifacts while episodes run."
---

# Coworld experience requests

Hosted XP is the primary competitive evaluation instrument. It consumes the owning user's [granted credits](../../../docs/xp-credits.md) and runs under separate API and job-capacity limits. Read [user preferences](../../../user_preferences.md), the [platform reference](../../../docs/platform-reference.md), and the selected game's evaluation guide.

Within the human's authorized objective, announce the question, cohort, count and budget considerations; do not ask again merely to run a targeted evaluation. New strategic directions or material scope/budget changes need the human's decision. Use local runs for own-policy self-play, not hosted XP.

## 1. Choose the experiment

| Question | Design |
| --- | --- |
| Where does the policy struggle against the current field? | Subject in one seat; eligible `random` or `top_n` opponents; game-appropriate natural roles |
| Did this change help? | Exact baseline/candidate versions, matched explicit opponents, seat treatment, game version and seed design |
| Is one role or mechanism broken? | Game-supported role/config overrides; confirm broader effects separately |
| Does the policy function under local self-play? | Local mechanism/debugging tools; not a hosted XP request |

Do not equate a random XP field with every league's matchmaking. Current sampling is rank-weighted without replacement until pool refill; duplicates can then appear. `slot: -1` rotates open seats, but incomplete rotations and game-specific role assignment can leave imbalance. Record actual seats and opponents.

Choose **1–100 episodes per request**. Larger batches need multiple requests and remain subject to the shared allowance/queue caps. An explicit integer `game_config_overrides.seed` repeats that seed throughout a request; omitting it does not produce matched seeds across independent requests.

Preregister operational-failure handling. Do not classify all nonpositive scores as infrastructure faults or silently drop player failures: report failures and coverage separately, then apply the game's justified gameplay metric rules.

## 2. Resolve the target and versions

Read the current league participation guide and Coworld manifest. Recheck name-to-ID mappings; IDs identify resources, while canonical versions and active leagues can change.

```bash
S=.claude/skills/coworld-experience-requests/scripts/experience_request.py
uv run python "$S" resolve --policy POLICY --version N
uv run python "$S" resolve --division div_... --top N
```

The resolver uses exact version labels on the primary leaderboard. A visibility or undersized-roster failure is not permission to silently substitute a different field. Use [the API reference](references/api.md) for body fields and their limits.

## 3. Compose and create

Record the exact request body with the experiment. Choose visibility deliberately: `private` defaults false, and a private request can exclude opponents that have not consented to requests hidden from their owners. A selection-consent rejection does not authorize changing the experiment to public.

```bash
uv run python "$S" create /tmp/request.json --check-schema
uv run python "$S" create /tmp/request.json
```

`--check-schema` makes no POST. It checks top-level keys plus game overrides when the helper resolves their schema; it does not fully validate every nested field, estimate credits, or prove admission will succeed. The server applies those contracts. A `state` selector only works when the game supports the corresponding persistence contract.

The creator prints the returned creation-only `cost_preview`. Save it with the body and returned ID. After creation, verify the resolved Coworld/version, variant, participant versions, seats and episode count. For ambiguous errors, inspect existing work before retrying; reuse the same supported idempotency key and payload.

## 4. Stream immediately

Start artifact collection in the background as soon as the request exists, so downloading and analysis overlap execution:

```bash
uv run python .claude/skills/coworld-episode-artifacts/scripts/fetch_artifacts.py \
  --xreq xreq_... --watch --out /tmp/evaluation-evidence
```

Use a game-specific streaming integration when the [capability map](../../../docs/capabilities.md) identifies one. Reruns resume existing evidence; inspect exhausted retry state before retrying it deliberately.

For **more than 16 episodes**, start the XP dashboard and give the human its localhost URL in the creation update:

```bash
uv run python .claude/skills/coworld-experience-requests/scripts/xp_dashboard.py \
  --port PORT xreq_...
```

For a quick status view use `uv run python "$S" monitor xreq_... --once`. A parent `failed`/`cancelled` label is not proof every child stopped. Both monitoring and collection must inspect child completion. Terminal failures may legitimately lack results/replays; report them as coverage gaps.

Use ordinary access. Honor API rate-limit response headers and bounded retries. Missing opponent diagnostics remain unavailable; never elevate to retrieve them for optimization. Link the request and evidence from the lab's experiment record, then report results and return the next strategic choice to the human.
