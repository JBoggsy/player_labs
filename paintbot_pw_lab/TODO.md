# Deferred Paintbot PW work

- Reverify the wider neural ZIP/oracle references before using those surfaces on 0.3.115;
  `PW_DOCS_SHA` intentionally remains 118e1619. Raw BASIC/rules49 changes are documented.
- Source/evidence decisions after M2: private motor/self-motion/pickup memory values
  are unlogged; cover “near” is undefined; Situation True checks are absent; Result checks
  have no thresholds. Resolve with James before changing source or telemetry. Do not infer
  correct execution from a raw outcome or G5 coverage.
- `pw_intent record --out RELATIVE_PATH` raises from `Path.as_uri`; an absolute `--out` works.
  Normalize the output path in the recorder with a focused regression test when fixing it.
- M3 hosted qualification in progress: final build `18e0aa1f-1` and local audit are complete;
  finish the fixed 64-episode A/B and hosted telemetry audit. Track the current evidence in
  `docs/designs/2026-10-05-m3-qualification.md`. Keep the two failed truth checks separate
  from passing transport. Use `compare --target score_outcome --margin-scale 600` for this
  preregistered comparison; historical `elo_outcome` stays the default.
- Audit partial-load accounting: a late seat I/O failure retains valid earlier-seat evidence
  with `input_failures` and exit 1, but the episode summary can be absent. Preserve those
  verified rows while exposing an explicit partial episode summary in a future refinement.
