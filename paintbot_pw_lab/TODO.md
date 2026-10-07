# Deferred Paintbot PW work

- Reverify the wider neural ZIP/oracle references before using those surfaces on 0.3.115;
  `PW_DOCS_SHA` intentionally remains 118e1619. Raw BASIC/rules49 changes are documented.
- Source/evidence decisions after M2: private motor/self-motion/pickup memory values
  are unlogged; cover “near” is undefined; Situation True checks are absent; Result checks
  have no thresholds. Resolve with James before changing source or telemetry. Do not infer
  correct execution from a raw outcome or G5 coverage.
- `pw_intent record --out RELATIVE_PATH` raises from `Path.as_uri`; an absolute `--out` works.
  Normalize the output path in the recorder with a focused regression test when fixing it.
- Complete iteration3 candidate seat-status coverage after shared API allowance recovers;
  all144 score outcomes are available, but v4 seat health is only partially verified.
  Optional coverage must not block iteration4; VERDICT-3 closes iteration3 on its scores.
  Score gain+.007222 is inconclusive; retain v3. Grenade continuity hosted qualification
  is complete. Disguise retention remains a separate hypothesis; M3 comms stays inactive.
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

- VERDICT-11 reactivates opening c85230af-1 and spray-safety51fe35f4-1 for independent
  hosted A/Bs rebased on submitted v8. Local losses are not vetoes. Gun-corridor v4 follows
  if credits allow. Record identities and outcomes in optimizer reports.
