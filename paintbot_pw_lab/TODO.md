# Deferred Paintbot PW work

- Reverify the wider neural ZIP/oracle references before using those surfaces on the current release;
  `PW_DOCS_SHA` intentionally remains 118e1619. Raw BASIC/rules49 changes are documented.
- Source/evidence decisions after M2: private motor/self-motion/pickup memory values
  are unlogged; cover “near” is undefined; Situation True checks are absent; Result checks
  have no thresholds. Resolve with James before changing source or telemetry. Do not infer
  correct execution from a raw outcome or G5 coverage.
- `pw_intent record --out RELATIVE_PATH` raises from `Path.as_uri`; an absolute `--out` works.
  Normalize the output path in the recorder with a focused regression test when fixing it.
- Audit partial-load accounting: a late seat I/O failure retains valid earlier-seat evidence
  with `input_failures` and exit 1, but the episode summary can be absent. Preserve those
  verified rows while exposing an explicit partial episode summary in a future refinement.

- Compiler maintenance: manual `strategy verify` can return gate success when finalization
  rejects high-severity guesses; propagate final report status as `compile` already does.
  Also make the assembled source banner reflect `--source` rather than the fixed default path.
  These findings are documented in the [maintainer guide](docs/strategy-compiler-maintainers.md);
  this documentation audit does not change compiler behavior.

- Before reactivating M3, port its inactive codec runtime and regenerate its units for Bassy.
  Current v10 qualification does not cover M3; use a separate source-directed change.

- VERDICT-32 authorizes the new Richard campaign. I33 central opening is in preparation;
  pipeline visible-teammate blast spacing locally while its hosted comparison runs.
  See WORKING_CONTEXT and REPORT-33. Only finite cohort workers, no independent field cron.
