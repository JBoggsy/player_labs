# Strategy compilation

`pw.py strategy` turns committed strategy Markdown and authored BASIC skills into
an immutable BASIC build. It runs locally and never uploads or submits a policy.
The [source format](../designs/2026-09-30-strategy-file-format.md) and
[compilation design](../designs/2026-09-30-strategy-compilation.md) define the contract.

## Commands

From the repository root:

```bash
uv run python paintbot_pw_lab/tools/pw.py strategy lint --json
uv run python paintbot_pw_lab/tools/pw.py strategy compile --agent claude --json
uv run python paintbot_pw_lab/tools/pw.py strategy compile --agent codex --full --json
uv run python paintbot_pw_lab/tools/pw.py strategy compile --milestone m1 --json
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
  interval's upper bound ≥ 0.5. M1 compares against `reference/base.bas` and requires
  the interval to contain 0.5.
- G5: two bounded local recordings through `pw_intent`, with seat logs. V2 lines
  must parse and decode with this build's map, and each candidate seat must supply
  its declared check/log fields and every initial rule-priority snapshot. Missing fields
  are unmeasurable and fail coverage.
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
