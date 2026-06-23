# Lens experiments — optimizing how we LOOK at the game

A parallel optimization track to the policy beam search. The policy loop asks
"which params win?"; this track asks **"which way of looking at replays most
effectively tells us what to change?"** (James, 2026-06-23). Observability is
itself a search space — we don't assume which lens matters, we measure it.

## The unit: a "lens"
A **lens** is a function over a set of replays that produces a *finding* — a
specific, actionable claim about why we won/lost. Three things vary independently:
1. **What signals it reads** (from SIGNALS.md): score decomposition, begging-by-
   harvest, family-growth timing, bread baked, beaten-to-a-space, card timing, ...
2. **How it combines them** into a finding (e.g. "grew at r12 but starved r14" fuses
   family-timeline + harvest-ledger).
3. **Which games it selects to look at** (the sampling lens — equally important):
   our losses; closest games; games vs the leader (terra); games where we begged;
   games where we were beaten to the family-growth space; random sample.

Example lenses (James's seeds + the catalog):
- `score-decomp` — final points by category, ours vs winner. (Where do points/−points come from?)
- `begging-by-harvest` — which harvest rounds we went short, by how much.
- `family-timeline` — when each seat grew + "was it fed?" verdict.
- `bread-baked` — grain sown vs baked vs begged (the §1.3 food-engine question).
- `beaten-to-a-spot` — spaces our policy ranked high that an opponent took first, by round.
- `card-timing` — when we (and the winner) played occupations/improvements.
- `tempo` — placements/round, idle turns.
- Sampling lenses: `our-losses`, `closest-games`, `vs-leader`, `we-begged`, `random`.

## The metric: diagnostic YIELD (how we score a lens)
A lens is effective if looking through it changes what we do AND that change helps.
We log, per lens application:
- **finding**: the claim it produced (text + the signal values behind it).
- **novelty**: did it surface something not already obvious / already-known? (dedup
  against prior findings — a lens that keeps reporting the same thing has low marginal yield.)
- **actionability**: did it map to a concrete beam mutation (a param/lever to change)?
- **→ outcome (the real score)**: when that mutation was beam-tested, did it WIN
  (Δ/seat > 0 vs champion)? A lens earns yield only when its finding leads to a
  confirmed improvement. This closes the loop: lenses are scored by the downstream
  win-rate of the mutations they inspire.
- **cost**: tokens/time to compute + read (cheap shell lens vs LLM-read replay).

Lens score ≈ (confirmed-win findings) / (applications), with novelty and cost as
tie-breakers. Like the policy beam: keep the high-yield lenses, retire the ones that
only ever restate the obvious, and *propose new lenses* (new signal combinations /
new game-selection rules) over time.

## The loop (parallel to beam_round)
Each diagnosis pass (after a batch of league/beam episodes):
1. **Select games** via the current best sampling lens(es) (e.g. our 5 worst losses).
2. **Apply the active lenses** to those replays → findings (each tagged with the
   signals it used).
3. **Log** every finding to lens-log.jsonl with novelty + which lens produced it.
4. **Promote findings → beam mutations**: an actionable finding becomes a candidate
   param change fed to the next beam round (evidence-directed search, not blind perturb).
5. **Attribute back**: when a mutation resolves (win/lose), credit/debit the lens
   that inspired it in lens-state.json. Update lens scores.
6. **Evolve the lens set**: occasionally propose a NEW lens (a new signal combo from
   SIGNALS.md, or a new game-selection rule) — the observability analogue of a beam
   mutation. Retire low-yield lenses.

## Relationship to Cronkite's reporter
Cronkite is building a structured post-mortem reporter (the heavy, rich lens).
These lenses are the lightweight, composable, *experimented-on* layer: cheap shell/
python views I can run every diagnosis pass and A/B against each other. When the
reporter lands, it becomes one (high-cost, high-detail) lens in the registry, scored
by the same yield metric as the rest. Findings from either feed the same beam.

## Files
- `tools/lenses.py` — the lens registry + runners (each lens = signals + combine + select).
- `tools/lens-log.jsonl` — append-only: every finding, its lens, signals, novelty.
- `tools/lens-state.json` — per-lens yield scores + the open findings queued for the beam.
- This doc — the framework + the why.

## Status
DESIGN. Next: implement starter lenses in tools/lenses.py, run them on real
replays (our recent league losses), log findings, and wire the actionable ones into
the beam runner's mutation proposals.
