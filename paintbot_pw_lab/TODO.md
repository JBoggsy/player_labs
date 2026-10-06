# Deferred Paintbot PW work

- Reverify the wider neural ZIP/oracle references before using those surfaces on 0.3.115;
  `PW_DOCS_SHA` intentionally remains 118e1619. Raw BASIC/rules49 changes are documented.
- Source/evidence decisions after M2: private motor/self-motion/pickup memory values
  are unlogged; cover “near” is undefined; Situation True checks are absent; Result checks
  have no thresholds. Resolve with James before changing source or telemetry. Do not infer
  correct execution from a raw outcome or G5 coverage.
- `pw_intent record --out RELATIVE_PATH` raises from `Path.as_uri`; an absolute `--out` works.
  Normalize the output path in the recorder with a focused regression test when fixing it.
- Next human-led edit-loop decision after M3: address false grenade warnings (charging while
  disarmed; early release/changed aim) and disguised teammates reported as enemies. M3's
  A/B is inconclusive, so retain the baseline as the competitive reference. See
  `docs/designs/2026-10-05-m3-qualification.md`. Do not silently retune the baseline or
  infer receiver effectiveness from successful decoding.
- Audit partial-load accounting: a late seat I/O failure retains valid earlier-seat evidence
  with `input_failures` and exit 1, but the episode summary can be absent. Preserve those
  verified rows while exposing an explicit partial episode summary in a future refinement.
