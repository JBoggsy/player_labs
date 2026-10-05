# Deferred Paintbot PW work

- M2 hosted acceptance: local migration and full audit qualification on 0.3.115 (`244dc62b`,
  rules 49) are complete with build `567feb38-1`; see WORKING_CONTEXT. Recheck the live
  release/roster and obtain explicit upload/evaluation authorization before one hosted
  confirmation episode. Retain immutable upload identity and played-release evidence.
  No M3 or publishing authorization is implied by local pin migration.
- Reverify the wider neural ZIP/oracle references before using those surfaces on 0.3.115;
  `PW_DOCS_SHA` intentionally remains 118e1619. Raw BASIC/rules49 changes are documented.
- Source/evidence decisions after M2-local: private motor/self-motion/pickup memory values
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
