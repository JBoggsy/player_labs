# cue_n_woo_lab

The **Cue-n-Woo** corner of [player_labs](../README.md) — where we build, evaluate, and
improve player policies for **Cue-n-Woo**, a two-player **theory-of-mind** Coworld game.

> **Status (2026-06-12): player built and submitted to the live league.** The game is
> published (`cue_n_woo` 0.2.1 deployed, owner `metta-ai`) and a **live league exists**
> (`league_e28faac2…`, Qualifiers → Competition). Our player
> [`mentalist/`](mentalist/) — **cheap style classifier → LLM writes a good on-topic
> answer in that style** (a fully LLM-free answer path tested weak) — is uploaded as
> `mentalist:v1` and in qualification. Live state: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).
> Research grounding: [`docs/cue-n-woo-gameplay.md`](docs/cue-n-woo-gameplay.md),
> [`docs/probe-findings.md`](docs/probe-findings.md), [`probe/`](probe/).

## The game (one paragraph)

Cue-n-Woo is **not** a gridworld (despite sharing the `cogames` image family with
among_them / cogs_vs_clips). Two players exchange **text** over a WebSocket. Each
privately interviews a hidden-persona **judge** (Gemma-2-9B-IT steered via FLAS toward
one of 61 known writing styles), then writes 3 challenge questions with their own
answers and blind-answers the opponent's 3 questions. The steered judge scores each
question as a 2-way preference between the two answers. **You win by modeling the
judge's hidden style better than your opponent** — to answer the way the style favors
and to author questions where your informed answer beats their blind one.

**Full game reference — rules, protocol, scoring math, and strategy — is
[`docs/cue-n-woo-gameplay.md`](docs/cue-n-woo-gameplay.md).** Read that to understand
the game without leaving the repo. The authoritative source is the **`Metta-AI/cue-n-woo`**
repo (game referee `v2/coworld/game.py`, baseline player `v2/coworld/players/baseline.py`,
protocol docs `v2/coworld/docs/`).

## The opportunity, in brief

The bundled `baseline-player` is a thin LLM harness (AWS Bedrock Claude Opus 4.8) that
makes every decision from a generic prompt — **no style classification, no use of the
known 61-style pool**. Because the default variant draws the hidden concept from a
**public list of 61 styles**, the private-questions phase is effectively a **61-way
classification problem**, and a purpose-built policy that identifies the style and then
answers/proposes in that exact style should beat the baseline comfortably. See the
strategy section of the gameplay doc for the levers and the open infra forks (runtime
LLM backend; whether to go LLM-free given the finite, known style set).

## Layout

```
cue_n_woo_lab/
  README.md                     this file
  WORKING_CONTEXT.md            live cross-session state — read first
  docs/
    cue-n-woo-gameplay.md       self-contained game reference (rules, protocol, scoring, strategy)
    probe-findings.md           what the live worker-probe spike established
    designs/player-design.md    the player architecture + build order
  probe/                        reproducible worker-probe harness (research spike)
  mentalist/                    our player policy (classifier → Bedrock writer); see its README
```
