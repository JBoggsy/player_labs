# Deferred Paintbot PW work

- Before performance A/B or M3 hosted comparisons, requalify the ranking metric: the current
  league reports `algorithm: openskill`, `margin_scale: 600`, `round_scoring_rule: mean`
  (authenticated 2026-10-05 league lookup; `tmp/collab/strategy/m2/hosted-league.json`).
  Verify current backend semantics and update the Elo-based adapter and guidance. M2
  telemetry checks do not use ranking scores.

- Reverify the wider neural ZIP/oracle references before using those surfaces on 0.3.115;
  `PW_DOCS_SHA` intentionally remains 118e1619. Raw BASIC/rules49 changes are documented.
- Source/evidence decisions after M2: private motor/self-motion/pickup memory values
  are unlogged; cover “near” is undefined; Situation True checks are absent; Result checks
  have no thresholds. Resolve with James before changing source or telemetry. Do not infer
  correct execution from a raw outcome or G5 coverage.
- `pw_intent record --out RELATIVE_PATH` raises from `Path.as_uri`; an absolute `--out` works.
  Normalize the output path in the recorder with a focused regression test when fixing it.
- M3: implement the comms v1 codec and evaluate it under the design's local and hosted gates.
  M1 preserves only baseline literal shouts.
- Audit partial-load accounting: a late seat I/O failure retains valid earlier-seat evidence
  with `input_failures` and exit 1, but the episode summary can be absent. Preserve those
  verified rows while exposing an explicit partial episode summary in a future refinement.
