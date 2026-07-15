---
name: coworld-hypothesis-miner
description: "Use to decide WHAT to change next when you have a batch of scored episodes but no specific suspect — mines the corpus for the behaviors that separate the policy's own wins from its own losses and emits a RANKED list of candidate hypotheses. Triggers: 'what should we improve next', 'mine the batch for hypotheses', 'why do our scores vary so much', 'which behavior is costing us points', 'rank the improvement candidates'. Game-agnostic engine; each lab supplies a small features.py adapter (same pattern as coworld-ab). Feeds coworld-experiment."
---

# Coworld Hypothesis Miner

Turn a corpus of scored episodes into a **ranked list of candidate hypotheses** by finding the
behaviors that explain the policy's **own score variance** — what its winning games do that its
losing games don't. Use it at the *diagnose* step when nothing specific is suspected yet: it
replaces eyeballing replays and guessing, and hands its top candidate to `coworld-experiment`.

Adapted from `Metta-AI/optimizer-skills`' replay-variance-miner, whose validated core insight is:

> **The behaviors a policy performs in *every* game — its invariant engine — explain how it beats
> *other* policies, but are useless for explaining its own variance,** because they're identical in
> its best and worst games. The score spread is driven by high-variance, load-bearing moves. The
> miner demotes the invariant engine automatically and ranks only what actually separates wins
> from losses.

## What it is (and is not)

- **Is:** a cheap, free re-analysis of data you already have (an eval batch you already pulled)
  that produces *candidates* — each with the feature evidence, a direction, and an estimated
  points-recoverable figure.
- **Is not:** a verdict. A mined candidate is a **correlation**; it goes through
  `coworld-experiment` (falsify the mechanism) and, if a change ships, `coworld-ab` (measure it).
  Never ship a change on miner output alone.

## Workflow

1. **Assemble the corpus** — ≥ ~8 scored episodes of the *same policy version* (more is better;
   the spread is the signal). One JSONL row per episode, in whatever shape your lab's adapter
   expects. Batches you pulled with `coworld-episode-artifacts` are the usual source; a lab's
   event warehouse (e.g. crewrift's) is ideal.
   **Decompose by role first** if the game has roles — mine crew episodes and imposter episodes
   separately; a mixed corpus attributes role identity, not behavior.

2. **Run the miner** with your lab's adapter:
   ```bash
   MINER=.claude/skills/coworld-hypothesis-miner/scripts
   uv run python "$MINER/mine_hypotheses.py" \
     --rows /tmp/mine/episodes.jsonl \
     --adapter <lab>/.claude/skills/<lab>-hypothesis-miner/scripts/features.py \
     --top 5 --out /tmp/mine/hypotheses.md
   ```

3. **Read the invariant list first.** Behaviors flagged `inv` are table-stakes — present in wins
   and losses alike. They are evidence of what NOT to spend a hypothesis on.

4. **Sanity-check the top candidates.** Before believing a ranked hypothesis: is the effect
   plausibly causal or is the feature a *consequence* of winning (e.g. "more kills" in a game
   where winners survive longer)? Reverse causation is the miner's known blind spot — the
   `Missing data` line in each emitted hypothesis exists for exactly this.

5. **Hand the best candidate to `coworld-experiment`** — the miner's output maps directly onto
   that skill's required input (mechanism + observable prediction). If the experiment confirms
   and a change ships, `coworld-ab` measures it.

**Not trustworthy when:** the corpus is < ~8 episodes; no feature clears the discriminative bar
(score spread is noise — the report says so); or failures are operational (crashes/disconnects
visible in logs) — fix ops first, mine gameplay second (taint-filter those episodes out of the
corpus before mining, per best practices).

## What your lab supplies — the adapter

The engine (`scripts/variance_miner.py`) knows **no** game. Each lab writes one `features.py`
module exporting exactly two names:

- **`adapter`** — a function `raw_row: dict -> Episode | None` (import `Episode` from
  `variance_miner`; the CLI puts it on `sys.path`). It maps one episode row to a flat
  `dict[str, float]` of behavioral features plus the seat's `score`. Return `None` to drop a row.
- **`METAS`** — a `dict[str, FeatureMeta]` describing each feature: `kind`
  (`timing`/`presence`/`count`), a human `blurb`, and a templated `change_hint` for the policy edit.

Feature design rules (so the miner finds real signal):

- **Include the invariant engine features on purpose** — the miner demotes them and reports them,
  which is itself evidence (table-stakes vs. what wins).
- **Make "never happened" a real worst-case value** (e.g. `LAST_TICK+1` for timings), not a
  missing key, so non-occurrence is comparable.
- **Prefer features tied to scoring and enabling milestones** (time-to-first-X, did-Y-at-all,
  count-of-Z in a scoring category); avoid raw per-action noise.

## See also

- **`coworld-experiment`** — where every mined candidate goes next (falsify before building).
- **`coworld-ab`** — measures a shipped fix; also the origin of the engine+adapter pattern used here.
- **`coworld-episode-artifacts`** — pulls the batches the corpus is built from.
