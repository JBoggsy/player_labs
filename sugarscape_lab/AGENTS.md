# Sugarscape lab guide

Read root [AGENTS](../AGENTS.md), [best practices](../best_practices.md), [preferences](../user_preferences.md), then the [lab README](README.md) and [working context](WORKING_CONTEXT.md).

The game owns simulation; these policies choose movement destinations. Source lives under [policies](policies/). Each policy's README and Dockerfile define its packaging. [Version log](version_log.md) and [evaluations](evals/) retain past results.

The hosted score is final living population wealth. Happiness is a broader world measure with components the policy cannot observe. Keep score/population outcomes separate from happiness hypotheses and account for fallback actions.

Use root experience-request/artifact tools for hosted evaluation. Match game/version, seed and seat assignment. No shared game-specific comparison adapter is claimed here; use the stored result schema for targeted analysis. Changes to simulation rules are outside policy optimization.

Record tentative findings in [TENTATIVE_LESSONS](TENTATIVE_LESSONS.md), archive/review using the [learning guide](../docs/learning.md), and keep the context concise. League submission needs explicit permission.
