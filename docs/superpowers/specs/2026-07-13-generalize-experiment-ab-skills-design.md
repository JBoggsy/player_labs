# Generalize the experiment + A/B skills for any Coworld lab

**Status:** approved design, pre-implementation
**Date:** 2026-07-13

## Problem

`crewrift-experiment` and `crewrift-ab` encode two reusable methodologies — rigorous
falsifiable-hypothesis testing, and matched-fresh A/B measurement — but they live under
`crewrift_lab/` and their scripts are coupled to crewborg. cue_n_woo and heartleaf have **no**
experiment/A/B tooling, so each new lab would re-derive the method and re-implement the statistics.

The coupling is not uniform. Inspection shows a clean seam:

- **Game-agnostic already:** the statistical engine in `compare.py` (two-proportion z-test,
  Welch-ish mean test, Cohen's d, the improved/regressed/noise `Delta` verdict, grouping); both
  report renderers (`compare_report.py`, `experiment_report.py`) — they consume only neutral JSON
  schemas and carry a single game-specific token each (a "Crewrift ·" eyebrow).
- **Genuinely game-specific (and un-generalizable):** the metrics themselves — crewrift's
  `Rec` fields, `results.json` column names, the `penalty` formula, the `METRICS` list, and the
  crew/imposter grouping. `kills_mean` cannot be made generic; it is crewrift's alone.

So "generalize" honestly means: **extract the reusable method + engine to the lab root, and let each
lab declare its own metrics via a thin adapter.**

## Goals

- Root-level `coworld-experiment` and `coworld-ab` skills usable by any lab.
- A shared, game-agnostic statistical engine (`ab_stats.py`) that per-lab adapters import.
- Crewrift becomes the **reference adapter**: its skills shrink to method-deferral + metric
  definitions; its A/B numbers are byte-identical before and after.
- Report renderers move to root, parameterized (title/eyebrow), consuming neutral schemas.

## Non-goals

- Writing cue_n_woo or heartleaf adapters now (YAGNI — crewrift is the worked example; a second
  adapter is written when that lab needs it, which is the point the abstraction earns its second use).
- A declarative/spec-file metric system (rejected in favor of per-lab Python adapters — Pythonic,
  type-checkable, matches how labs already vendor `tools/`).
- Any change to the experiment/A/B *methodology* itself.

## Architecture — three layers

### A. Root skills (`.claude/skills/`) — method + shared machinery

**`coworld-experiment/`**
- `SKILL.md` — the falsifiability method (design → adversarially criticize for construct
  validity/falsifiability/confounds/power → cheapest valid instrument → pre-registered verdict),
  ported from `crewrift-experiment` with crewrift examples replaced by a game-neutral running
  example and a **"What your lab supplies"** section (its instruments + adapter). Universal
  discipline lines kept verbatim.
- `scripts/experiment_report.py` — moved as-is except: `--title`/`--eyebrow` args replace the
  hardcoded "Crewrift ·" eyebrow (default generic). Schema already game-neutral.

**`coworld-ab/`**
- `SKILL.md` — the matched-fresh A/B method (fresh+matched principle, pin every seat, drop
  ops-fails, decompose by group, respect noise, one change at a time), ported from `crewrift-ab`
  with crewrift examples generalized and a **"What your lab supplies"** section.
- `scripts/ab_stats.py` — **the extracted engine** (see contract below). Zero game knowledge.
- `scripts/compare_report.py` — moved as-is except: `--title`/`--eyebrow` args; the "role grid"
  language becomes "group". Consumes the neutral JSON contract.

### B. Per-lab adapter — `<lab>/.claude/skills/<lab>-ab/scripts/compare.py`

Owns exactly the game-specific parts:
- `Rec` dataclass + `load_batch`/`_record` — extraction from *that lab's* `results.json`/`episode.json`.
- `METRICS` list — `(key, higher_is_better, kind∈{rate,mean}, applies_to_group|None)`.
- `value_fns` — `{metric_key → (recs → list[float])}` for the mean significance test.
- `by_group(recs) → {group_name → [rec]}` — the lab's grouping dimension.
- Imports `ab_stats` from the root skill via the established sibling `sys.path` pattern
  (precedent: `coworld-experience-requests/scripts/xp_dashboard.py` inserts a sibling skill's
  `scripts` dir). Calls `build_deltas`, prints the shared Markdown table, writes the JSON.

### C. Crewrift = reference adapter

- `crewrift-ab/SKILL.md` and `crewrift-experiment/SKILL.md` shrink to: "this is `coworld-ab` /
  `coworld-experiment` for crewrift — here are our metrics (crew/imposter, kills/tasks/penalty…)
  and our warehouse instrument," deferring the method to root.
- `crewrift-ab/scripts/compare.py` reduced to only the layer-B parts above; all statistics deleted
  and imported from `ab_stats` instead.
- `experiment_report.py` / `compare_report.py` deleted from crewrift (now called from root; crewrift
  invocations pass `--eyebrow "Crewrift · …"`).

## The adapter ↔ engine contract

**`ab_stats.py` public surface:**
- `two_sided_p(z)`, `rate_sig(p_a, n_a, p_b, n_b) → (z, p)`, `mean_sig(vals_a, vals_b) → (z, p, d)`
- `Delta` dataclass + `Delta.compute(base_recs, cand_recs)` — improved/regressed/noise verdict;
  `SIG_P`, `SMALL_N` module constants (overridable via optional args).
- `build_deltas(base_groups, cand_groups, metrics, value_fns) → list[Delta]` — generalization of
  today's `build_deltas`/`_values`; grouping opaque (`{group → [rec]}`; role-less games pass
  `{"all": …}`).
- `emit_json(base_spec, cand_spec, target, deltas) → dict` and `render_markdown(deltas, target)` —
  both group-agnostic.

**Neutral JSON contract** (produced by every adapter, read by `compare_report.py`) — today's shape
with `role` → `group`:
```json
{"baseline": "...", "candidate": "...", "target": "...",
 "deltas": [{"metric","group","base","cand","n_base","n_cand","p","effect","verdict"}]}
```
`group` renamed from `role` so it reads honestly for role-less games; crewrift's adapter places
crew/imposter into `group`.

## Testing & validation

- **Behavior-preservation gate (key risk):** run the *reduced* crewrift `compare.py` on an existing
  episode dir; diff its JSON + Markdown against the current script's output on the same dir. Must be
  identical (same stats, same verdicts, same target handling). This is the regression test that the
  extraction changed nothing.
- Smoke-render `experiment_report.py` and `compare_report.py` on sample JSON (with and without
  `--eyebrow`); open the HTML to confirm the Ink & Print styling survived.
- No new-lab adapter is exercised (none written); the root SKILLs document how to author one.

## Affected files

- **New:** `.claude/skills/coworld-experiment/{SKILL.md,scripts/experiment_report.py}`,
  `.claude/skills/coworld-ab/{SKILL.md,scripts/ab_stats.py,scripts/compare_report.py}`.
- **Reduced:** `crewrift_lab/.claude/skills/crewrift-ab/{SKILL.md,scripts/compare.py}`,
  `crewrift_lab/.claude/skills/crewrift-experiment/SKILL.md`.
- **Deleted:** `crewrift_lab/.claude/skills/crewrift-ab/scripts/compare_report.py`,
  `crewrift_lab/.claude/skills/crewrift-experiment/scripts/experiment_report.py` (+ their pyc).
- **Docs:** update the crewrift `AGENTS.md` skills index + root `AGENTS.md`/`README.md` skills list
  to name the two new root skills and the adapter pattern.

## Open questions / risks

- **`sys.path` sibling import across lab→root:** precedent is intra-root
  (`xp_dashboard.py`). Crewrift→root is one directory deeper; the adapter must compute the root
  `.claude/skills/coworld-ab/scripts` path robustly (via `Path(__file__).resolve().parents[...]` to
  the repo root, then down). Verify the depth constant at implementation time and comment it, per the
  `build_warehouse.py REPO = HERE.parents[5]` precedent.
- **`--eyebrow` default:** pick a neutral default ("Coworld · A/B comparison") so an un-parameterized
  render is still clean.
