# Deferred Paintbot PW work

- M2 hosted acceptance: local audit is implemented. On 2026-10-05 authenticated reads
  resolved teams league `league_ae677105-0ab8-4561-81ec-c9cf6735821c` to 0.3.114/rules 49
  (`4d670eca2b5f74d722f7630e94eed7f9449d979a`). Obtain James's agreement to the
  [local migration proposal](docs/designs/2026-09-30-strategy-compilation.md#m2-live-release-requalification-proposal)
  before moving the 0.3.89 pin. The smaller alternative keeps that pin and qualifies unchanged
  policy telemetry using isolated 0.3.114 tools. The literal M2 hosted criterion is line arrival,
  not a five-level audit on rules 49. Obtain separate explicit upload/evaluation authorization
  after local qualification; retain immutable upload identity and played-release evidence.
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
