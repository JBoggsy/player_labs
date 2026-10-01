---
name: paintbot-pw-compile
description: Compile committed Paintbot PW strategy source into an immutable BASIC build with local gates.
---

# Compile a strategy

Read `paintbot_pw_lab/strategy/compiler/AGENT.md` for the compiler contract and
`paintbot_pw_lab/docs/tools/pw_strategy.md` for commands. Use the Python driver:

```bash
uv run python paintbot_pw_lab/tools/pw.py strategy lint --json
uv run python paintbot_pw_lab/tools/pw.py strategy compile --agent claude --json
```

Source, skills, compiler instructions/runtime, and compiler tools must be committed.
The driver owns preparation, the isolated agent call, assembly, gates, repairs and reports.
Do not generate a monolithic policy yourself or edit finalized builds.

Read the JSON envelope and `report.md`. A failed build is evidence to diagnose, not
an artifact to upload. Resolve guesses in the source; repeat compilation after committing.
For M1 use `--milestone m1`; its reference is `reference/base.bas`.

This skill performs local compilation only. Uploads, league entry, hosted evaluations,
and strategy improvements are separate work.
