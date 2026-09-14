# Choosing and building analysis tools

Start from the decision the human needs to make. A tool is useful when it shortens a repeated path from evidence to that decision.

1. **Find what exists.** Read the [capability map](capabilities.md), game AGENTS/tool index and the installed CLI's help. Inspect an existing adapter before inventing an interface. Search established libraries for a common problem; use existing dependencies first.
2. **Name the missing observation.** Examples: which decision caused an objective loss; whether an ability actually fired; whether a slow call missed its deadline. Distinguish replay truth, what the policy perceived, and what the evaluator received.
3. **Inspect real data.** Pin game/version/config, episode ID and policy-version UUID. Verify seat mapping from explicit positions. Missing values stay missing; a missing log is not evidence an action never happened.
4. **Build the smallest useful tool.** A saved query or small report may suffice. Keep game parsing and mechanics in the lab. Share transport, statistics and presentation only when there is a concrete second consumer.
5. **Validate the boundary.** Use representative fixtures for parsing, sparse/multi-seat identity, partial downloads and failure filtering. These checks protect analysis correctness; they are not a pre-upload player gate.
6. **Connect it.** Add a link from the lab guide and capability map. Document input/schema, invocation, outputs, assumptions, exclusions and a known example. Link the experiment that motivated it.

## Shared contracts

- **Artifacts:** [downloader](../.claude/skills/coworld-episode-artifacts/SKILL.md) stores raw source metadata plus results/replay and accessible diagnostics. Check its completion markers and exclusions before analysis.
- **Comparisons:** [A/B engine](../.claude/skills/coworld-ab/SKILL.md) consumes metric/group records. Its independent-sample tests require independent episodes, not repeated seats. Multi-seat averages are continuous means, not binary rates. Matching and sufficient power are experiment-design responsibilities.
- **Hypothesis mining:** [miner](../.claude/skills/coworld-hypothesis-miner/SKILL.md) consumes `Episode` feature records. Ranking is descriptive association, never expected recoverable points or causal proof. Filter one comparable policy/game/cohort before mining; test the proposed mechanism separately.
- **Progress dashboard:** descriptive seat-level counts and scores from accessible results. It is not a significance test or game-specific diagnosis.

## Keep evidence inspectable

Store raw observations beside decoded fields and stable tick/event keys. Provide a machine-readable output and a useful human inspection path when both are needed. Prefer event/state-change logs to repeated noise, preserving periodic snapshots where reconstruction needs them. Record tracing configuration and missing coverage; instrumentation itself can change latency.

## Verification sources

Current API fields come from the [Observatory OpenAPI](https://softmax.com/api/observatory/openapi.json), checked 2026-09-14. The shared comparison reuses existing SciPy [Fisher exact](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.fisher_exact.html), [Welch t-test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html) and [false discovery correction](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html), avoiding handwritten distribution approximations. No new production dependency was needed.
