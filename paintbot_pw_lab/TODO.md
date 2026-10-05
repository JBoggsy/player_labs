# Deferred Paintbot PW work

- M2 hosted acceptance: the local audit is implemented. Before any hosted work, resolve the
  current teams league and engine release, agree the pin update and rerun qualification.
  The public directory still identifies `league_ae677105-0ab8-4561-81ec-c9cf6735821c`, but the
  current release has not been verified; 0.3.113 is historical. Obtain explicit authorization
  before upload or hosted evaluation. Confirm one episode's complete telemetry, then audit
  it with immutable upload identity evidence. The audit currently qualifies only 0.3.89/rules 48.
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
