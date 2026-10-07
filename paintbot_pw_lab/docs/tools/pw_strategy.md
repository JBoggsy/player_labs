# Strategy compilation

`pw.py strategy` turns committed strategy Markdown and authored BASIC skills into
an immutable BASIC build. It runs locally and never uploads or submits a policy.
The [source format](../designs/2026-09-30-strategy-file-format.md) and
[compilation design](../designs/2026-09-30-strategy-compilation.md) define the contract.
For Python interfaces, provenance, implementation limits and cross-game extraction, read the
[maintainer guide](../strategy-compiler-maintainers.md). `--source` selects a source document;
it does not select a different game backend.

The checked-in `strategy/STRATEGY.md` is restored to foundation build `3d0f8a4f-1`.
M3 communications are inactive and recoverable from commit `2184fc64`. The compiler targets Bassy at 0.3.123 with integer division and explicit 0/1 flags.
Use `--full` when rebuilding pre-Bassy units: their arithmetic cannot be reused unchanged.
The frozen baseline [M1 build report](../../strategy/compiled/b41ef1fc-1/report.md) records passing G1–G5;
the side-balanced 28-seed screen reports identical play, and all 16 candidate-seat recordings
pass telemetry parsing and coverage on the original 0.3.89 release.
[Build `567feb38-1`](../../strategy/compiled/567feb38-1/report.md) requalifies the same
baseline on the active 0.3.115 pin.
The five-level audit (M2) is qualified locally and with hosted telemetry on 0.3.115. M3 is qualified locally and hosted, with an inconclusive performance comparison and explicit
failed/unmeasurable truth checks ([evidence](../designs/2026-10-05-m3-qualification.md)). Codec components opt in with
`Encoding: comms-v1 N` (wire type 0–8), declare `packet[2]`, and use `Log: packet`.
Generated code owns this packet and the send/receive status fields. Mixing codec and legacy
COM components or duplicate wire types is rejected. The compiler includes the authored codec
only for opted-in builds; the map records wire types, constants and compact batch format.
See [comms](../../strategy/comms.md) for the current implementation and acceptance status.

## Commands

From the repository root:

```bash
uv run python paintbot_pw_lab/tools/pw.py strategy lint --json
uv run python paintbot_pw_lab/tools/pw.py strategy compile --agent claude --json
uv run python paintbot_pw_lab/tools/pw.py strategy compile --agent codex --full --json
uv run python paintbot_pw_lab/tools/pw.py strategy compile --agent codex --json
uv run python paintbot_pw_lab/tools/pw.py strategy trace <build-id> --json
```

The default source is `paintbot_pw_lab/strategy/STRATEGY.md`. `lint` accepts a
positional source path; `prepare` and `compile` accept `--source FILE` for committed
fixtures. `--model MODEL` overrides the selected agent's default in
`strategy/compiler/config.json`. `--from ID` chooses a previous passed build.
Without it, the driver selects the latest passed build for this source whose commit
is an ancestor of HEAD. `--full` regenerates every LLM component.

`prepare` creates a work order under `paintbot_pw_lab/tmp/strategy/<id>/`.
`assemble ID` assembles staged units. `verify ID` runs the gates and finalizes the
build, successful or failed. These commands support inspecting individual steps;
`compile` owns the complete agent/repair cycle and is the normal entry point.
There is no `generate` subcommand; programmatic generation uses
`strategy_build.generate(order, errors=None, timeout=900)`. `verify` runs gates and finalizes
without repairs. Check the finalized `report.json.status`: the manual `verify` envelope
currently reflects gate failures but can miss a finalization failure from unresolved guesses.
`compile` propagates the finalized status correctly.

`--milestone m1` compares against the verbatim upstream Bassy starter at `28030de6`,
`reference/base-bassy-28030de6.bas`. That starter also changes targeting, HP handling and
items, so exact play identity is not expected from a semantics-only foundation port.
Do not use it for the current M3 behavior change. `--milestone m0` has no special gate override.
`trace` reports component text/interface changes; it does not verify artifact hashes or
all input drift (for example changed runtime or skill implementation bytes).
`compile --agent-timeout SECONDS` bounds each agent call (default 900).

## Source and agent boundaries

Commit strategy source, skills, compiler instructions/runtime, and compiler tools
before preparing a build. Unrelated working changes are allowed. The driver records
input hashes, source commit, agent CLI version/model, compiler instruction hashes,
and the engine pin. It checks inputs again before assembly and verification.

Only generation uses an LLM. The agent receives component text and declared
interfaces in an independent temporary Git repository. It may write the requested
`units/<ID>.bas` files and `report_draft.json`. The driver checks all files, including
ignored files and symlinks, and Git HEAD/refs/index after the call. Out-of-scope
changes fail the build. The temporary repository is discarded; the user's checkout
is never reverted. This is repository write-scope detection, not a guarantee against
writes elsewhere on the machine. Codex additionally uses its workspace sandbox;
Claude receives only file-reading/editing tools.

Unchanged units are copied from the previous build. Changed components also receive
their previous unit under read-only `context/previous/` as the agent's starting point.
Requested output files start absent, so an untouched previous unit cannot masquerade as
a freshly compiled result. Source-declared interface changes
invalidate their direct consumers. Python generates rules, constants, roles,
commitment and tables. Skills and runtime files are copied verbatim.

## Gates and reports

- G1: source lint.
- G2: compile and run all 16 seats for 720 ticks through `pw.py local compile`.
- G3: per-seat instruction/work peaks in one full-length seed-7 headless match,
  plus the runtime's static print bounds. Limits: 40,000 instructions, 100,000 work
  units, 512 printed bytes and 64 print events per tick.
- G4: full-length local screen on seeds 1–28, both sides. Bad seats always fail.
  Scores are advisory for behavior changes. No-behavior-change builds require the
  interval's upper bound ≥ 0.5. M1 compares against the pinned Bassy reference and requires the interval upper bound
  to reach 0.5 (no demonstrated local regression); this is a screen, not statistical proof
  of non-inferiority or competitive improvement.
- G5: two bounded local recordings through `pw_intent`, with seat logs. V2 lines
  must parse and decode with this build's map. Every candidate seat must supply its
  unconditional declared fields and initial rule-priority snapshots. Legacy builds require
  all declared fields per seat. Codec builds require send and receive paths across the
  recording set; absent rare message types are reported as `not_exercised`, not failed
  coverage or semantic passes. Missing unconditional fields fail coverage.
  This checks wire format and coverage, not whether gameplay checks are true.

The compile driver allows at most three generation/gate rounds. G4 never requests a
behavior repair. Peak coverage is sampled; one full-length peak run does not prove
that all possible gameplay paths stay below the lower G3 threshold. G4 additionally
catches actual engine budget overruns across its screen.

Final builds live in `strategy/compiled/<source-sha>-<n>/`. Each contains units,
`policy.bas`, `map.json`, `version.json`, `report.json`, `report.md`, and gate evidence.
Raw telemetry recordings stay under `tmp/strategy-evidence/<id>/`; the build keeps
their parsed summaries. Diagnostic `.log` files are local and excluded from artifact
hashes so a committed build can be reused in a fresh checkout.
Build IDs are reserved before work starts. Repairs happen in staging; finalization
renames the directory once. Finalized builds cannot be reassembled or overwritten.
Failed builds are retained for diagnosis and are never selected for incremental reuse.

The caller commits completed builds after reviewing reports. The driver does not
commit. Resolve guesses in the source and recompile. `Accepts` matches complete guess IDs;
`kept` guesses remain open, and unresolved high-severity guesses block `tested` or
`proven` component status. Report quotes are checked against compiler-read text. Tuning output is experimental:
write accepted values back into `Params`, commit, and compile a new build.

## Agent CLI contract

Every command supports `--json`, producing the shared `pw_cli.py` envelope. Human
progress and child output go to stderr or gate log files. Exit 0 means success,
1 means build/gate failure, 2 means invalid arguments or source/configuration, and
3 means a required tool is unavailable. The envelope lists output paths and failures.

The Claude wrapper and lab compile skill point to the same
[`compiler/AGENT.md`](../../strategy/compiler/AGENT.md). Codex uses the same driver
and instruction file; neither wrapper owns separate compilation rules.

## Five-level audit (M2)

```bash
uv run python paintbot_pw_lab/tools/pw.py strategy audit EPISODE_DIR --build b41ef1fc-1 --json
uv run python paintbot_pw_lab/tools/pw.py strategy audit EPISODE_DIR --build b41ef1fc-1 --check K.contacts --level True --json
```

`audit` accepts one or more roots, requires an explicit finalized `--build`, and supports
`--check COMPONENT` or `--check COMPONENT.N` (one-based source order within that component),
`--level 'Acted properly'` (or any of the five levels), `--out DIR`, and `--refresh`.
Unknown or empty selectors exit 2 and list valid checks. The command only reads existing
episodes; it does not create hosted requests. It does not modify a build or the strategy.

Outputs are `audit.json`, `report.md`, and full `evidence.jsonl`, by default under
`analysis/strategy_audit/<build>-<roots-and-options-hash>/`. Re-running overwrites those outputs.
The JSON includes every selected check, a five-level matrix (`not_declared` where source has
no check), per-episode checks, seat coverage, raw outcomes, input failures, and input hashes.
Evidence rows identify the check, episode, seat, decision tick, result and reason. Summary
rows retain five examples; the JSONL contains all observations. Output paths inside
`strategy/compiled/` are refused.

### Identity and evidence

The auditor verifies build artifact hashes and loads `STRATEGY.md` from its committed git
blob, verifying its source hash. It cross-checks the source rules, roles, commitment, codes
and checks against the map. It reuses `pw_intent.parse_v2_line`, `pw_episodes` dense
hash-verified replay loading, and `strategy_basic.reference_select`.

Local candidate seats come from `a_side` and the policy SHA256 in recording metadata;
file basenames are not identities. If both sides have the build hash, both are audited.
Hosted identities require a matching upload receipt in `strategy/compiled/uploads.jsonl`
with `build_id`, `policy_version_id`, and `policy_sha256`. These additional receipt fields
are required for auditing; the earlier display-only `policy_ref` and date remain useful.
The hosted episode's `coworld_version` must match the build release. The trace tool's
release alone does not prove which engine played a hosted episode.

The audit accepts exact engine contracts: `coworld-v0.3.89` / `118e1619` / rules 48 and
`coworld-v0.3.115` / `244dc62b` / rules 49, teams with 16 seats. Other engine/rules
combinations fail identity validation. Rules49 qualification is recorded in build `567feb38-1` and
[WORKING_CONTEXT.md](../../WORKING_CONTEXT.md): G1–G5 and six local audit recordings pass
with the nine declared evidence limits remaining unmeasurable. Hosted request
`xreq_b602c137-06ad-4696-b334-3e99a02d0de2` confirms the same audit on 19,829 living
decision ticks, 17 passing checks and nine unchanged unknowns, with zero failures. All eight
candidate logs pass existing G5 coverage (5,800 lines); 56/56 status sends align at t+1.
Upload provenance is recorded in `uploads.jsonl`: the CLI completes with the local content
hash, but the platform version-detail endpoint did not expose a hash for independent readback.

Runtime reconstruction accepts exact reviewed hashes: the M1 skeleton, the compact-print
foundation skeleton in `3d0f8a4f-1`, and that skeleton with the engine-tested comms codec.
Other runtime hashes report `runtime_model_mismatch`. Baseline prose predicates bind to
the component and its transitive compiled references, exact authored skill bytes, the
global Adaptation set, and the check's text/level/Reads. Changed dependencies stay
unmeasurable; unrelated changes do not invalidate independent replay-relative predicates.
New strategies still receive generic runtime consistency counts separately from prose checks.
Transport reconstruction uses the engine's byte-based inbox filter. A replay text whose
byte count cannot be reconstructed leaves that receive tick unknown; send evidence and
other ticks are retained, and no complete decode ratio is claimed.

Replay state at `t` describes the decision; commands and shouts execute at `t+1`.
On the four full local M1 recordings, all 170 telemetry sends match replay shouts at
that offset; offsets 0 and 2 each miss all 170.
PWD is a change log with a 24-tick heartbeat, so unchanged fields can be carried inside
verified coverage. PWB is sampled: only scheduled living ticks are audited, and a missing
scheduled sample is unmeasurable. No belief is filled between samples. Priority defaults
come from source before the initial PWP snapshot finishes arriving. PWP transitions check
arithmetic and versions; an adaptation's private trigger is not thereby verified.

Activation windows distinguish same-tick start/done, preemption, death and truncation.
The runtime emits its death event at respawn; the audit closes the window at the actual
replay death tick. A still-open activation at recording end is truncated, not successful.
Malformed, missing, duplicate or out-of-order logs, missing heartbeat/snapshot evidence,
and a changed runtime conservatively make dependent seat checks unmeasurable.
Heartbeat checks cannot detect every deleted interior line; reconstruction relies on
the qualified emitter's change-complete contract as well as observed coverage.

### Reading results

| Status | Meaning |
| --- | --- |
| `pass` | At least one measurable opportunity, no violations and no missing applicable evidence. |
| `fail` | A deterministic predicate was violated on measured evidence. |
| `measured` | A statistic with no acceptance threshold; it is not a pass. |
| `not_exercised` | No applicable opportunities. |
| `unmeasurable` | Required data, a defined criterion, or a reviewed evaluator is missing. |

A check with partial coverage never passes. Seat-wide unknowns are counted separately as
`unmeasurable_seats`; coverage is null when they prevent a comparable denominator. Other
opportunities are decision ticks, scheduled belief samples, or activation windows, according
to the check. They are observations, not independent experimental replicates.

**Exit 0 means the audit ran, not that the strategy passed.** Gameplay findings, missing
logs and unmeasurable checks exit 0. Unreadable files, failed replay verification or episode
identity failures exit 1 with partial results and input failures. Invalid build/source/hash
or selectors exit 2. Missing replay tools exit 3 with the build command.

Conditional `Result` requires measured belief correctness and full correct execution,
including called skills. Missing declarations do not establish those prerequisites.
The baseline motor's private gun wait and firing guards are not logged, so baseline
Results remain unmeasurable. `raw_outcomes` separately reports survival, pickups, captures
of sampled targets, and shot hit rates. Target samples do not establish an exact target
throughout an activation. Shot range bins use the trace's inferred target distance, not
an asserted intended target. Wilson intervals are descriptive shot-level intervals;
shots within an episode are correlated, so these are not competitive-performance tests.

The baseline also cannot verify unlogged self-motion or remembered pickup kind/position,
the undefined cover distance “near”, or the private full-charge flag behind the grenade
callout. A pickup's fixed map slot does not prove that the compiled memory held that
slot's values. “Was at” is not silently reinterpreted as “ready now”. Situation truth
checks are not declared in M1; logged flags alone do not prove their truth.

Implementations: `strategy_audit.py` (identity, CLI/report), `strategy_audit_runtime.py`
(change-log reconstruction), `strategy_audit_baseline.py` (frozen baseline predicates), and
`strategy_audit_comms.py` (source-bound codec message checks). Codec checks compare payloads
with replay state and next-tick delivery to verified same-build teammates. Missing map bounds,
untraced facts, unknown execution, and unsupported check text remain unmeasurable.
Absent message types are not exercised. Receiver effects are not proven by transport success.
For grenade landing claims, the evaluator follows the warned charge through its actual lifecycle,
including a continuously held command before charging can start. It does not impose a deadline
from the packet's release estimate. A stopped command that never charged, death, or a reset
without a throw fails the landing claim; an unfinished lifecycle or missing trace is unmeasurable.
A newer warning supersedes the old one. An associated throw needs a matching recorded
`grenade_blast`; its observed position must be within 150 cm of the reported cell center.
Projected landings after episode end, missing blasts and ambiguous matches are unmeasurable.
Self-destruct blasts do not satisfy this check. The release estimate error is diagnostic,
not a hidden pass criterion.
Add an evaluator and negative tests when adding a check; never let unknown prose fall
through to a pass. The immutable M1 report and its five compiler guesses remain unchanged.
