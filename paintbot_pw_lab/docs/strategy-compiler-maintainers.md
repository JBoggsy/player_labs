# Strategy compiler: maintainer and generalization guide

This is the implementation map for the compiler currently owned by the Paintbot PW lab.
Read it before adapting the compiler to another Polyworld game. **There is no generic
Polyworld backend or game-adapter API yet.** The boundaries below describe existing code
and propose what a future extraction must separate; they are not interfaces already shipped.

## Reading path and authority

1. [Command reference](tools/pw_strategy.md): operation, gates, audit outputs and exit codes.
2. [Source format](designs/2026-09-30-strategy-file-format.md): grammar, layering, selection,
   checks and telemetry. [Compilation design](designs/2026-09-30-strategy-compilation.md):
   accepted invariants and process. Markdown is authoritative; adjacent HTML is an older render.
3. [Compiler instructions](../strategy/compiler/AGENT.md): the generation agent's exact ABI.
4. This guide: code ownership, Python interfaces, artifacts, limitations and porting checklist.
5. [M3 qualification](designs/2026-10-05-m3-qualification.md): what has actually been tested.
   [WORKING_CONTEXT](../WORKING_CONTEXT.md) and [TODO](../TODO.md) hold current work and gaps.

`STRATEGY.md` is policy source; `AGENT.md` instructs the compiler agent. Do not confuse them.
The opening strategy glossary, linked pages and prose after the component field list are
not expanded into the generation work order. Put required definitions inside component
fields. `comms.md` is tracked provenance and design, not an automatically included prompt.
The driver supplies the whole policy-surface reference, lessons and frozen starter separately.

## Ownership and data flow

All paths below are relative to `paintbot_pw_lab/`. Follow source symbols rather than line
numbers. These are internal Python interfaces, not a separately versioned library API.

| Owner | Responsibility and boundary |
| --- | --- |
| `tools/pw.py`, `tools/pw_cli.py` | Dispatch/catalog and shared JSON envelope/errors. `pw_strategy.py:parser/run` owns strategy command arguments and the three-round compile loop. |
| `tools/strategy_format.py` | `parse_strategy(Path) -> Strategy`; `lint_strategy(Strategy) -> list[Diagnostic]`. Parses fixed Markdown into components, rules, roles and commitment; validates references, field grammar, usage and print budget. Content errors become diagnostics; filesystem errors can still raise. |
| `tools/strategy_basic.py` | `unit_contract(strategy, id) -> dict`, `check_unit(strategy, id, text) -> list[Diagnostic]`, `assemble(strategy, units, runtime_dir, build_id, source_commit) -> dict`. Owns BASIC structural checks, ABI permissions, deterministic tables, map and static budgets. Assembly returns `policy`, `units`, `map`, `budget`, or raises `BuildError` with diagnostics. |
| `tools/strategy_build.py` | Input inventory/Git checks, previous-build selection, work orders, agent invocation/scope checks, assembly I/O, guess carry-forward, immutable finalization. Constants `LAB`, `REPO`, `COMPILER`, `BUILDS`, `STAGING` bind it to this checkout. |
| `tools/strategy_gates.py` | `verify(build_id) -> dict` computes G1–G5 for staging. Calls Paintbot local compile/screen, headless peaks and intent recorder. It does not itself finalize. The `verify` CLI does. |
| `strategy/compiler/runtime/lib.bas`, `main.bas` | Authored selection, adaptation arithmetic, activation lifecycle, telemetry and tick order. Python mirrors: `reference_select` and `reference_priority` in `strategy_basic.py`. |
| `strategy/compiler/runtime/comms.bas`, `tools/strategy_comms.py` | Optional Paintbot comms-v1 runtime and Python codec/transport model. Compiler integration is in `strategy_basic.py`; this is not a generic Polyworld protocol. |
| `tools/pw_intent.py` | Shared recorder, legacy PWI parser/audit, strategy v2 parser, compact PWC v3 expansion and G5 coverage. Use `parse_telemetry_line(line, mapping)` for v2/v3; `parse_v2_line` only handles ordinary v2. |
| `tools/strategy_audit.py`, `strategy_audit_runtime.py` | Build/source/episode identity, evidence rows and summaries, runtime reconstruction. Uses dense replay tables from `pw_episodes.py`. |
| `tools/strategy_audit_baseline.py`, `strategy_audit_comms.py` | Reviewed Paintbot semantic predicates. These encode game mechanics and exact source meanings; they are not a natural-language assertion interpreter. |

Flow: committed inputs → parse/lint → staged work order → isolated generation → checked
units + authored skills/runtime → deterministic assembly → local gates → final report and
version → immutable build. Separately: build + upload receipt + replay + seat logs → audit.
Uploading, hosted evaluation, league submission and Git publication are outside the compiler.

## Source model and hashes

`Strategy` has `path`, `root`, `name`, ordered `components`, `rules`, `roles`, `commitment`
and `diagnostics`; `of_kind`, `llm_components` and `codes` are the main accessors.
`Component` holds parsed fields, `uses`, params, inputs, outputs, conditions, log schedule,
checks, effect, code path, directions, prefix, code, interface and compiler text/hash.
`Diagnostic` exposes level, code, message, component and line; use `to_dict()` for CLI output.
The dataclasses and `FIELDS`, `LAYERS`, `CAPS` in `strategy_format.py` are the exact schema.
Current limits are 63 rules, 124 Situations, 63 Capabilities, 31 Adaptations, 63 Knowledge
components, 15 COM components and three capability inputs. Declared output arrays have
2–64 cells. Situation flags use 31 bits per word. These are format/runtime constraints,
not just game settings; changing one requires matching generated/runtime/parser changes.

- LLM kinds: K, S, C, A, COM. SK is authored BASIC. ST is deterministic. P has no unit.
- Codes are assigned in source order within each kind; zero means none. They are local to a
  build, not stable cross-build IDs. Rules/roles/conditions have their own code spaces.
- `compiled_text` includes the ID and fields in source order, excluding Evidence, Status and
  Rationale. Checks contribute only level/Reads entries when Reads are present, not claim prose.
  `Summary`, `Accepts`, encoding and other nonmetadata fields do affect the hash.
- `declared_interface` contains outputs and array sizes, parameter names, capability inputs
  and condition codes, skill SUB signatures (name → argument count), and COM directions.
- `prepare` marks new/changed/reused/removed components; a changed declared interface also
  invalidates its direct `Uses` consumers. It does not recursively regenerate all callers
  merely because dependency implementation bytes changed.
- Current skill bytes are copied into agent context even if a previous build exists. Requested
  generated outputs start absent; their previous text is under `context/previous/`.
- Runtime, instructions, model, engine or compiler-tool changes are recorded inputs but do not
  automatically regenerate all LLM units. Use `--full` when regeneration is intended.
  `--full` can retain a previous-build reference for context and comparison.
- Build intent is separate from regeneration: source component/interface changes, skill-tree
  changes or `comms.md` changes mean behavior change; `--milestone m1` overrides intent.
  A runtime-only change counts as no behavior change and gets the corresponding G4 rule.
- Audit binding hashes include check text/level/Reads separately. Editing check prose must
  never inherit a semantic pass just because the compiler text hash stayed the same.

`trace` compares current component text/interfaces with a stored map. It is **not** a complete
input-drift or artifact-integrity check: it does not compare runtime, compiler tools, skill
implementation hashes or all provenance. `checked_build` verifies stored artifact hashes;
`committed_inputs` and `assert_inputs` protect compilation inputs.

## Build and agent contracts

`source_files` is the definitive input inventory. It includes the source, its entire skills
subtree, adjacent `comms.md` when present, compiler directory, `strategy_*.py`, dispatcher,
intent/local/release/terrain/CLI tools, release.env, policy-surface and reference/base.bas.
All must be tracked, committed regular files; unrelated dirty files are allowed. The work
order stores repo-relative path → SHA256 values. Checks before generation, assembly and
finalization reject changes to those recorded files. This is not a hermetic environment:
agent executables, installed packages and every transitive replay dependency are not frozen
by that inventory. Record toolchain versions when qualifying a port.

`prepare` requires an installed selected agent even for a reuse-only build, since it records
its version. Defaults are in `strategy/compiler/config.json`; `--agent`/`--model` override
those values. Agent authentication is external to this repository. No dependency installation
or login happens in the driver.

Two work orders exist:

- Staging `work_order.json`: build/source/provenance, previous build, all component metadata,
  unit statuses, intent, compiler/engine identities and diagnostics.
- Disposable agent repository `work_order.json`: generate list, compiler text and unit contracts
  for requested components, all declared interfaces, previous guesses and repair errors.
  It does not expose the whole staging order as the prompt contract.

`generate` invokes Claude or Codex synchronously, timeout default 900 seconds per call.
Only requested `units/<ID>.bas` and `report_draft.json` may change. Scope checks include
ignored files, deletions, symlinks, Git HEAD/refs/index. They detect changes within the scratch
repository, not arbitrary writes elsewhere on the machine. This is not a hostile-code sandbox.
The CLI configuration and exact invocation live in `agent_command`.

There is no `strategy generate` CLI subcommand. For normal operation use `compile`; low-level
`prepare`/`assemble`/`verify` are debugging interfaces. Programmatic generation is
`strategy_build.generate(order, errors=None, timeout=900)`.

`assemble` writes policy, map, unit copies and budget in staging. `verify` CLI runs gates and
finalizes once, without an agent repair loop. `compile` orchestrates up to three rounds,
then finalizes. Scope violations stop repairs. G4 does not request gameplay repair.
Failures before a work order exists have no finalized build; interruption or exceptional I/O
can leave staging behind. A failed finalized build cannot be reused; prepare a new build after
fixing inputs. Do not delete reservations or edit a finalized build to retry it.

### Artifact reference

| Artifact | Consumer contract |
| --- | --- |
| `units/*.bas` | Normalized headers for LLM units; exact authored SK/runtime text; `generated.tables.bas` contains deterministic code. Policy block separators/header are added around these units. |
| `map.json` (`pw-strategy-map/1`) | Components with code/prefix/text hash/interface/uses/unit/hash/checks/log fields; rule arguments/conditions, roles, priorities, adaptations, commitment, flag words, telemetry shape/bounds/offsets, runtime hashes, skill paths/hashes, optional comms map. Generated by `build_map`. |
| `version.json` | Build/source path and commit, input hashes, previous build, compiler/model/instruction hashes, engine, creation time, intent, status, gates, driver identity, policy hash and artifact hashes. Written by finalization. No separate schema discriminator today. |
| `report.json`, `report.md` | Status, unit changes, guesses, gaps, gate results, budget, failure. `report_draft.json` is the generation agent's input to reporting, not final authority. |
| `verify/`, `gates.json`, `budget.json` | Local gate envelopes/summaries and budget evidence. `.log` diagnostics are excluded from artifact hashes; raw recordings stay in gitignored `tmp/strategy-evidence/<id>/`. |
| `compiled/uploads.jsonl` | Append-only receipt outside immutable builds: build ID, exact policy-version UUID, policy SHA256, human policy ref/date. Required for hosted audit identity. Upload tooling/caller writes it, not `compile`. |
| Audit `audit.json`, `evidence.jsonl`, `report.md` | `pw-strategy-audit/1` summary, complete selected-check evidence rows and human report. Reports are overwriteable analysis outputs, never written into `compiled/`. |

`version.json` does not hash itself, and hashes are provenance/integrity checks, not signed
attestations. Retain source Git history and referenced baseline builds: the audit loads source
with `git show` and checks frozen baseline/runtime maps, not only the candidate directory.

Guesses close only through exact IDs in source `Accepts`. An agent's `resolved` becomes
`possibly resolved`; `kept` remains open unless already accepted. Unclosed high-severity guesses
block tested/proven status at finalization. Never rewrite an old report to close a guess.

## Runtime and validation limits

The exact tick sequence is in `runtime/main.bas`: initialize once; reset print accounting;
detect a skipped-tick death gap; receive; Knowledge; Situations; Adaptations; rule conditions;
select; bind inputs; capability start/tick; send; decision/belief logs; priority snapshots;
compact batch flush. Start and tick both run on an activation's first tick. Inputs rebind
every tick. Death ends an activation, but does not reset all policy memory.

The BASIC scanner is structural, not a complete compiler or control-flow proof. In particular,
required assignment checks establish that a name is assigned somewhere, not on every path;
unprefixed function calls are left for the engine to validate. G2 is still necessary.
BASIC int32 overflow, truncating division, non-short-circuit logic, top-level SUB/DIM,
no SUB return values, transient string handles and host-reserved names must remain explicit
in any target's verified policy-surface and compiler lessons.

G1–G5 establish local build validity and sampled behavior/budgets; G5 is transport/coverage,
not semantic truth. See the [gate reference](tools/pw_strategy.md#gates-and-reports).
The local screen retains its historical margin-1000 metric; it is not the current league
ranking metric. Hosted A/B must independently resolve scoring and opponents.

Audit exit 0 means analysis completed, even with failed or unknown checks. A caller must inspect
`input_failures`, per-check statuses/coverage, runtime issues and raw outcomes. Runtime
reconstruction is distinct from strategy truth; Results need measured upstream belief and
execution evidence. Unknown prose gets no evaluator and no pass. The current auditor accepts
only the exact release/rules contracts listed in `ENGINE_CONTRACTS` and reviewed runtime hashes.
It also requires frozen M1 and foundation builds; moving just `strategy_audit.py` is insufficient.

## Generalizing to another Polyworld game

This is a **proposed extraction checklist**, not an implemented plugin design. Research the
second game's current host/VM/replay contracts before choosing abstractions. Sharing the engine
family does not establish identical host names, rules, seat layout, scoring or telemetry.
Reuse the existing deterministic compiler where its contract fits; do not copy Paintbot facts
into a game-neutral module or add a framework without a concrete second use.

| Boundary to separate | Current coupling to verify/replace |
| --- | --- |
| Paths and input provenance | `strategy_build` constants and `source_files`; `pw_strategy.DEFAULT_SOURCE`; hardcoded Paintbot policy banner in `assemble`; prompt policy-surface/starter paths. `--source` changes the document, not the backend or build root. |
| VM dialect and host surface | `strategy_basic.HOST_DATA`, `KEYWORDS`, `LIMITS`, print limits and scanner assumptions; compiler AGENT/LESSONS and policy-surface. Host function validation is deferred to the target engine. |
| Seat/lifecycle model | `strategy_format.SEATS=16`, static role partitions, generated role data, runtime `worldTick` death-gap assumption; gate peak arrays and audit parity/team identity. |
| Local verification | `strategy_gates` imports of `pw_local`, `pw_release`, `pw_terrain`, `pw_intent`; 16 seats, 14,400 ticks, seeds, glory settings, comparison metric, native and hosted-handoff executables. G1–G5 names need not imply identical game-specific instruments. |
| Release/toolchain | `release.env`, `pw_release`, build scripts and binary/cache naming. A port needs its own game/release identity; same tag text across games must not collide in caches. |
| Telemetry | Generic event concepts can transfer, but schemas, numeric codes, sampling offsets, print accounting and v3 comms payload decoding must remain tied to a build map. |
| Communication | Nine wire types, 16-seat packing, map cells, byte inbox filter, range, cooldown, priority, checksum, COM/K/SK permissions and receiver effects are Paintbot-specific. Codec is optional; do not require it in a game without this channel. |
| Replay and identity | `pw_episodes` discovery/dense tables/cache receipts, `pw_trace.nim`, hosted version UUIDs and upload receipts, actual played release and command t→t+1 alignment. Supply equivalent verified evidence rather than relabeling another replay format. |
| Semantic audit | Baseline IDs, exact source/check bindings, runtime hashes, observed-identity model, hearts/supplies/gun/grenade predicates. Start new game checks as unmeasurable until independently implemented and tested. |
| Operations | CLI catalog, skill, documentation navigation, upload artifact contract, player identity, hosted roster/scoring and evaluation authorization. Raw BASIC upload is not universal. |

Recommended order for the generalizing agent:

1. Inventory a real second game and write a short contract/differences table. Agree consequential
   format changes separately; do not silently allow K→K, SK→SK or dynamic roles.
2. Separate paths/input inventory, engine facts and gate invocations with the smallest interfaces
   that both games actually need. Keep Paintbot strategy, motor, codec, semantic predicates and
   evidence in this lab. Shared root code/docs must be game-neutral.
3. Preserve the existing Paintbot CLI and immutable build reader. Do not move old artifacts or
   rewrite their recorded source paths/hashes. Version any changed serialized contract and test
   historical reads explicitly. Retain unknown/partial evidence and exit-code meanings.
4. Prove the extraction without gameplay changes: deterministic fixture output/runtime behavior,
   unit reuse and authored-byte preservation, both agent backends, real-engine compile, budgets,
   side-balanced unchanged-play screening and telemetry/audit regression.
5. Qualify the second game separately with a minimal strategy and a faithful reference baseline.
   Test its replay timing, source identity and negative/unknown audit cases. Only then claim
   cross-game support. No Paintbot semantic acceptance transfers automatically.

### Parallel work with the Paintbot agent

James intends Paintbot policy work to continue while another agent generalizes the compiler.
Use separate worktrees/branches. The Paintbot agent owns strategy components, authored motor,
comms policy and their evidence; the generalizing agent owns the proposed shared compiler and
adapter extraction. Coordinate edits to `strategy_*.py`, `pw_intent.py`, runtime files,
compiler instructions, release/build scripts and canonical designs before changing them.
These files participate in compilation identity: do not change them underneath an active build.

Record the source commit and chosen previous build for each experiment. Integrate extraction
at a committed boundary, then prepare a new build and requalify; never splice new compiler
files into an old work order. A source change needed for a compiler port must be explicit and
kept separate from a gameplay hypothesis. This guide does not assign another agent's task or
start the extraction.

## Commands, tests and troubleshooting

Run from the repository root using `uv`. Python dependencies are supplied by the existing
project environment. The engine tools also need the documented Nim/native setup in
[release](tools/pw_release.md) and [local runner](tools/pw_local.md). Read build scripts before
running them: use a writable scratch clone through `PW_CLONE`, preserving the original engine
checkout. Reuse the terrain cache and check disk space before generating recordings.

Read-only orientation (no generation or hosted evaluation):

```bash
uv run python paintbot_pw_lab/tools/pw.py strategy --help
uv run python paintbot_pw_lab/tools/pw.py strategy lint --json
uv run python paintbot_pw_lab/tools/pw.py strategy lint paintbot_pw_lab/tools/tests/fixtures/strategy_trivial/STRATEGY.md --json
uv run python paintbot_pw_lab/tools/pw.py strategy trace 18e0aa1f-1 --json
uv run python paintbot_pw_lab/tools/pw.py doctor --offline --json
```

An offline doctor checks local setup; it is not a live league compatibility check. Before
hosted work, resolve the current release and requalify changes to the active pin. Compilation
and upload examples are in the command reference and game skills; they are separate actions.

| Test files under `tools/tests/` | What a port must preserve |
| --- | --- |
| `test_strategy_format.py` | Grammar, layering, hash exclusions, role/rule/effect validation, read coverage. |
| `test_strategy_basic.py` | ABI, deterministic assembly, verbatim skills/runtime, budget calculations, selection/adaptation parity in the real engine. |
| `test_strategy_build.py` | Reuse, current skill context, missing generated output, scope violations, hashes, finalization, guess handling, G4 intent rules. |
| `test_strategy_telemetry.py`, `test_strategy_batch.py`, `test_strategy_batch_budget.py` | v2/v3 parsing, per-seat vs event coverage, ordering, malformed streams, static and measured print bounds. |
| `test_strategy_comms.py`, `test_strategy_audit_comms.py`, `test_strategy_motor_comms.py` | Codec/engine agreement, delivery, claim truth, grenade lifecycle and receiver behavior; mostly Paintbot-owned tests. |
| `test_strategy_audit.py`, `test_strategy_baseline.py`, `test_pw_intent.py` | Source/episode identity, runtime reconstruction, semantic binding, unknowns, conditional Results, baseline and replay timing. |

Focused deterministic checks:

```bash
uv run python -m pytest paintbot_pw_lab/tools/tests/test_strategy_format.py paintbot_pw_lab/tools/tests/test_strategy_build.py
```

Compiler/audit regression and full shared-tool validation:

```bash
uv run python -m pytest paintbot_pw_lab/tools/tests tools/tests
```

Engine-backed tests can skip when the handoff binary is absent. A green run with those skips
is not engine qualification. Preserve the explicit test counts/skips and build reports.
See the committed trivial fixture for a complete valid source; fragments in the design are
illustrations, not standalone strategies.

Common failures: uncommitted inputs → commit the named inputs; changed input after prepare →
new build; missing binary → follow doctor/release fix command; missing generated unit → inspect
agent.log, never fill it with an old output; over-budget assembly → fix source/compiler and
rebuild; unknown audit predicate/runtime → review and qualify it, never whitelist merely to
get a pass. `pw_intent record --out` currently needs an absolute path (known TODO).

Current portability limitations include the hardcoded policy banner even for `--source`,
non-hermetic toolchain capture, and manual `verify` reporting gate success even when
finalization's high-severity-guess check makes `report.json.status` failed. Read the finalized
report as well as the envelope; normal `compile` propagates final status. These are code
limitations documented here, not changed by this documentation audit.
