# Getting started with a policy lab

The loop is **evaluate → understand → choose a change → implement → evaluate again**. The human sets strategic direction; the agent makes the evidence easy to inspect and carries out authorized work. Explain the gameplay decision and its evidence in plain language.

## 1. Find or choose the game and policy

Read root [AGENTS](../AGENTS.md), [preferences](../user_preferences.md), [best practices](../best_practices.md), and the selected game's guide in the [capability map](capabilities.md). Check its WORKING_CONTEXT and version log. A historical objective or permission is not a new instruction.

If no current policy/objective has been selected, present the available choices and recommend a starting point based on what the user wants to investigate. Do not automatically choose the first lab or rewrite a strategy before direction is established.

## 2. Prepare the project

```bash
uv sync --locked
uv run softmax login
uv run softmax status
uv run python -c "from importlib.metadata import version; print('coworld', version('coworld')); print('softmax-cli', version('softmax-cli'))"
```

Use the project environment, not global package installs. Authenticate interactively when needed. Fetch and inspect the relevant repository's branch/upstream before relying on its code; preserve local edits. Check current project-local CLI releases before diagnosing unexpected behavior. Docker is required for container policy builds; game-hosted files use their game's packaging contract.

## 3. Establish a useful baseline

Resolve the actual game version, policy-version UUID and current roster. State the question, metric, cohort/roles, intended count/stopping rule and available budget. Experience requests may incur costs. Do not run paid self-play. Existing evidence or local mechanism checks can answer narrower questions more cheaply.

Use [experience requests](../.claude/skills/coworld-experience-requests/SKILL.md) and stream [artifacts](../.claude/skills/coworld-episode-artifacts/SKILL.md) as games finish. Verify the resolved participants and output coverage. Use normal participant access; private opponent diagnostics remain unavailable.

## 4. Make the next decision concrete

Show the outcomes and a few decisive replay/trace moments. Separate what happened from the proposed cause. Present alternatives with a check that could refute each. Use the game's tools from the capability map; consult [tool building](tooling.md) when a necessary observation is missing.

The human chooses the strategic direction. Within an already authorized objective, carry out the investigation and experiment without requesting the same permission again. Ask when a new strategy, scope or budget decision is needed.

## 5. Improve and compare

Change one attributable component. [Build and upload](../.claude/skills/build-and-upload/SKILL.md) a new version and record its source/runtime configuration. The next hosted evaluation tests it; no routine pre-upload smoke gate. Use local runs to answer a concrete debugging/parity question.

Use fresh matched baseline/candidate batches for an [A/B comparison](../.claude/skills/coworld-ab/SKILL.md). An implementation milestone is not a win; retain inconclusive and negative results. Update the version log, experiment index and concise working context.

## 6. Close the loop

Record candidate lessons using the [learning guide](learning.md). Once improved behavior is demonstrated, submit to a league only with explicit permission. Public community writes and remote Git operations also require their own authorization. At the end of the requested task, present the next useful option and pause.
