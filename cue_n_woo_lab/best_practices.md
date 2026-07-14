# Cue-n-Woo best practices

Cue-n-Woo-specific practices for the improvement loop — layered on top of the
**game-agnostic** [`../best_practices.md`](../best_practices.md) (read that first;
these are additions, not replacements). Distilled from real work in this lab; treat
as defaults and **warn the human if a request would contravene one** before
proceeding. Add to this file as we learn more about *this game's* failure modes.

The graduation pipeline fills this in: candidate lessons accumulate in
[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md), and `/lessons-review` promotes the
ones that recur across sessions into durable practices here. Era-bound strategy
knowledge (which judge is live, what the field plays, what wins right now) does
NOT belong here — that lives in [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md) and
[`docs/`](docs/). These are the practices that survived judge changes.

## Verify the current game mechanism before any strategy work

The judge and scoring mechanism have been replaced out from under us repeatedly —
61 named styles → 4-of-15 `axis_combo`; FLAS-Gemma context-free delta-of-delta
logit scoring → prompt-steered Bedrock Claude Sonnet sampled forced-choice — and
each swap invalidated the entire reigning strategy (passphrase plants, then the
phlogiston flood) overnight. Before diagnosing or iterating strategy, re-read
`v2/coworld/game.py` at HEAD in the authoritative cue-n-woo checkout
(`~/coding/coworlds/cue-n-woo`) and confirm the
canonical deployed package version. `/tmp` extracts and old images are stale;
strategy conclusions inherit the era they were measured in. When the mechanism
changes, treat all prior strategy lessons as suspect until re-verified.

## Only live experience requests judge a strategy — probes screen, and they lie

This is the single most re-learned lesson in the lab. Offline probes against the
judge repeatedly produced confident deltas that washed out or reversed live:
fantasy questions, injection-wording generations, probe-composition "winners,"
the injection duel bake-off, the offline rare-word basket. The recurring failure
modes:

- **Never use the judge's own generated answer as the opponent** — it is the
  unbeatable ceiling and compresses all variants together. Synthetic opponent
  answers are barely better. The only valid probe comparison uses **real field
  answers harvested from replays**, and even that omits author-side dynamics.
- **Replicate on a second independent concept seed before believing any probe
  delta.** Concept-seed variance fabricates ±7pt "effects" from a single seed;
  candidates have both gained and lost multi-point swings on seed change. A
  probe-significant, multi-seed-robust win has *still* washed out at the live
  gate — probe mean_p is a necessary screen, never a verdict.
- **A probe that fixes the opponent measures only the half of the game we
  influence.** It cannot predict win rate against an adversarial authoring field.

Live evaluation discipline for this game specifically:

- **The judge is non-reproducible across time.** It scores the same
  (concept, context, answers) differently hours later. Recorded `results.json`
  is ground truth for what happened at game time; never re-score old episodes
  and compare to recorded. Run A/B arms **time-tight** (fire all arms within
  minutes) so both face the same judge state.
- **Check the probe reporter's `reproduction_error` before trusting any of its
  attributions**; re-probe when the fleet worker is healthy. The analyst (no
  judge calls) is the cheap first-pass tool; the probe is expensive and
  load-sensitive.
- **Score finished episodes only, and report timeout rate separately.** A
  timeout is -100 to both players and is infra, not skill. Clustered failures
  in one time window are one infra event, not a rate. Check participants before
  labeling episodes (self-play = qualifier).
- **Hold the opponent mix constant when comparing arms**, and compare
  per-opponent — a hard-matchup-weighted sample makes any arm look worse in
  aggregate.

## Completion beats excellence — the 600s timer and DQ mechanics

A fresh submission lands in Qualifiers with a short window; if its mean round
score is ≤ 0 it is disqualified as "inactive," and a single timeout is -100 — so
a player that cannot reliably *finish* episodes never qualifies, regardless of
strategy strength. Several strong versions DQ'd purely on this.

- **Satisfy every phase quota exactly**: 3 private questions, 3 proposals, 3
  answers. Asking *fewer* probes than `private_questions_per_player` stalls the
  global phase forever → inactive -100 → DQ. Latency savings must come from
  making each action fast, never from doing fewer required actions. Probe asks
  cannot be pipelined — the server handles player actions serially — so 3
  sequential judge generations are a mandatory latency floor.
- **Our probe wording controls judge latency.** Long multi-part probes make the
  Sonnet judge generate long answers and blow the timer; probes demanding
  one-to-few-word answers preserve most persona signal at a fraction of the
  latency. Keep judge-facing text terse and cap requested output.
- **Never let an in-flight guard outlive its phase.** The per-slot view
  (`me.judge`) lags across phase boundaries; a pending guard keyed on "did my
  action's effect appear in my own view" wedged us out of proposals → inactive
  DQ, and never reproduced in isolated fast-judge races. Clear pending guards on
  phase advance. A mirror match (own both slots) is the cheapest reproduction of
  a league-only stall and gives both slots' logs.
- **Fleet saturation gates completion.** Under a loaded shared judge nothing
  completes; the same player goes 6/6 in a light window and 0/12 in a saturated
  one. Time submissions to observably healthy fleet windows (recent division
  episodes completing with low duration); a re-submission buys a fresh qualifier
  window.

## Upload flags are load-bearing — verify the hosted pod, not local runs

- **`--run python --run=-m --run <player>` is mandatory on upload and local
  runs**; without it the manifest's stub argv applies and the image crashes.
- **`--use-bedrock` must be passed at upload time** for any LLM/Titan-dependent
  player — it sets `USE_BEDROCK` and grants the pod IRSA access. Uploads that
  silently dropped it shipped a brain-dead fallback player through two league
  versions, and the A/B run on top of them compared two degraded arms.
- **Local Gate-1 proves nothing about the hosted pod's LLM access** (local runs
  inject `--aws-profile` credentials the pod doesn't have), and the stub-worker
  cert smoke never exercises the LLM writer at all. After every upload, pull a
  hosted episode log and grep for the success line (`backend=bedrock`, a real
  call latency) — verify success, not capability or coherent-looking output.
  Coherent output has repeatedly turned out to be a deterministic fallback.

## Game rules that shape every strategy

- **Duplicate-conflict**: a casefold exact-or-prefix match between the two
  answers gives both sides ~40 points. This is simultaneously a floor (echoing a
  dominant answer converts a sure loss into a tie), a trap (matching an
  opponent-emphasized word guarantees the collision), and a defense constraint
  (don't commit an answer that is a prefix of what the opponent will say).
- **The answer limit is characters, not words**: "simple tokens" =
  `ceil(len/4)`, so 12 tokens = 48 characters. A word-based validator passes
  answers the server rejects, costing retry round-trips under the timer.
- **The judge scores the complete answer text**, not a magic first token — the
  continuation carries most of the signal.

## Reading results — the data contracts

- `results.json` `rows[]` is the per-question scoring ground truth: owner /
  opponent, literal answers, per-side points, `average_secret_probability`,
  `duplicate_conflict`. `owner==0` rows are our authored questions; `owner==1`
  are our blind-answer rows. Attribute every point from here before opening a
  replay.
- For experience requests, the real scores live in `episodes[].scores` joined to
  `episodes[].participants` on `policy_version_id` — never by list position; the
  convenience score fields are null. The xreq `completed_count` counts timeouts
  as terminal — read per-episode `results.json` status.
- `random`/`top_n` opponent selectors resolve **once per request**: fire many
  small requests, not one big one, to get an opponent spread.
