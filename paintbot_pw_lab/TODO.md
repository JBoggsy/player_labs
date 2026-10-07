# Deferred Paintbot PW work

- Reverify the wider neural ZIP/oracle references before using those surfaces on 0.3.115;
  `PW_DOCS_SHA` intentionally remains 118e1619. Raw BASIC/rules49 changes are documented.
- Source/evidence decisions after M2: private motor/self-motion/pickup memory values
  are unlogged; cover “near” is undefined; Situation True checks are absent; Result checks
  have no thresholds. Resolve with James before changing source or telemetry. Do not infer
  correct execution from a raw outcome or G5 coverage.
- `pw_intent record --out RELATIVE_PATH` raises from `Path.as_uri`; an absolute `--out` works.
  Normalize the output path in the recorder with a focused regression test when fixing it.
- Complete hosted qualification of grenade continuity (candidate2a539036-1 / jb-pw-opt:v3)
  after shared API allowance recovers. Local short throws fell73→0 across matched24 games;
  this does not establish field strength. Disguised teammates and ordinary gun friendly fire
  remain separate hypotheses. M3 comms stays inactive; no receiver-effectiveness inference.
- Audit partial-load accounting: a late seat I/O failure retains valid earlier-seat evidence
  with `input_failures` and exit 1, but the episode summary can be absent. Preserve those
  verified rows while exposing an explicit partial episode summary in a future refinement.

- Compiler maintenance: manual `strategy verify` can return gate success when finalization
  rejects high-severity guesses; propagate final report status as `compile` already does.
  Also make the assembled source banner reflect `--source` rather than the fixed default path.
  These findings are documented in the [maintainer guide](docs/strategy-compiler-maintainers.md);
  this documentation audit does not change compiler behavior.

- Before reactivating M3, port its inactive codec runtime and regenerate its units for Bassy.
  Only the foundation baseline is qualified on 0.3.123; use a separate source-directed change.
