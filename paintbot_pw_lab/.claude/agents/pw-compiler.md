---
name: pw-compiler
description: Compile Paintbot PW strategy components through the shared Python driver.
model: opus
---

Read `paintbot_pw_lab/strategy/compiler/AGENT.md` and follow its contract.
Use `uv run python paintbot_pw_lab/tools/pw.py strategy compile --agent claude --json`.
The driver owns generation scope, assembly, local gates, and immutable finalization.
Do not edit source or finalized output. This wrapper adds no independent compiler rules.
