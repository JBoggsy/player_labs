# Improvement Loop — alpha (2026-07-28)

**Status:** alpha — first autonomous multi-loop run dispatched 2026-07-28. This document is
the operating spec for that run and the template to revise from afterwards.

The 9-step, tournament-scale improvement loop for crewborg, as specified by James, with
each step bound to the lab tooling that executes it. One **loop** = steps 1→9 (or an
early exit where the evidence says stop). The runner executes ~5 loops back-to-back.

## The pipeline

| # | Step | Tooling | Output |
|---|---|---|---|
| 1 | Fresh field data: hundreds of episodes vs the live roster | `coworld-experience-requests` (create) + `crewrift-event-warehouse/stream_eval.py` (stream) | xreq ids; episodes + warehouse building live |
| 2 | Pull episode artifacts + crewborg's traced player artifacts | `coworld-episode-artifacts` (`--elevated`), bundled into step 1's streaming | episode dirs with `artifacts/policy_artifact_<slot>.zip` |
| 3 | Sync ground truth + beliefs into one event log | `crewrift-belief-audit/build_belief_log.py` | `belief_*` warehouse partitions + `belief_sync_report.json` |
| 4 | Mine stats that correlate/anti-correlate with winning (excluding trivial) | `coworld-hypothesis-miner` + crewrift `features.py`; NEW: belief-divergence rates as features | ranked win/loss separators |
| 5 | Scan for belief-vs-truth divergences | `crewrift-belief-audit/scan_divergences.py` | `belief_divergences.jsonl` + per-kind rates |
| 6 | Mechanistic hypotheses from 4+5 | `crewrift-diagnose` (belief-accuracy fixes ← step 5; deficient-stat levers ← step 4) | 2–4 varied hypotheses, each pinned to code |
| 7 | Design + run one falsifiable experiment per chosen hypothesis | `crewrift-experiment` (design → adversarial critique → **prereg BEFORE firing**) → `crewrift-ab` / probe builds | prereg doc + experiment arms |
| 8 | Verdict against the prereg | prereg gates; ops-profile check both arms first | SHIP / NO-SHIP / RERUN per the written decision rule |
| 9 | Ship: build → upload → confirmatory A/B → submit | `build-and-upload` → `crewrift-ab` (confirmatory, in-composition) → `coworld-policy-lifecycle` (submit) | new competing version |

## Operating parameters (this run)

- **Scale per loop (step 1):** 300–400 episodes (3–4 xreqs × 100), Thread-1 pinned roster,
  crewborg slot 0, natural roles — matched to the standing baseline arms so cross-loop
  comparisons stay clean. Pace ≤400 concurrent episodes (hard rule; above it opponent pods
  connect-timeout and the shared Bedrock pool collapses).
- **Baseline discipline:** every A/B uses fresh matched arms per `coworld-ab`; never compare
  against stale batches across platform windows. Ops-profile both arms before reading any A/B.
- **Submit authority:** James granted standing permission for THIS run (2026-07-28:
  "you totally have my permission; I want to see this run, I'm not worried about tanking my
  leaderboard score"). Procedure stays disciplined regardless: the loop runner does NOT
  submit directly — it reports the clean pre-registered verdict to the orchestrator
  (main session) and asks; the orchestrator approves iff all prereg gates passed.
  Retire the incumbent membership FIRST, then submit, then targeted-poll to competing/active.
- **Upload freely** (probes, candidates); probes are never submitted.
- **Experiment firing:** auto-fire on a complete prereg (design criticized, gates written,
  registered in a docs/designs prereg doc BEFORE the arms launch). No human gate per
  experiment for this run.

## Known results — do not rediscover

- Belief-clock lag under meeting load: FIXED (v111; spend-read cache + auto-submit 96).
  `clock_desync` now only catches residual reconnect stalls.
- Bimodal posterior: softer posterior bars unlock nothing; separation lives in social
  counters (W2). The open lever there is a suspicion-v5 refit (ML ceiling AUC 0.82).
- Refuted levers: post-kill flee, fabricated counter-accuse, witness-gate tuning (3×),
  chat-evidence without trust floor. Vote-coordination combo (push+retime) interferes.
- Current champion: v116 (retime ON). Its WATCH item — crew WR + ballot→ejection
  conversion — folds into loop 1's step-1 data read.
- Fresh smoke signals worth first-loop attention: census death-belief lag 300–650 ticks;
  crew-topped rankings at p≈0.50–0.53 sitting exactly at the vote bar.

## Loop exit / degrade rules

- A loop may exit early with a NO-SHIP verdict; that is a *successful* loop (knowledge
  gained, lever closed). Record it and start the next loop.
- If step 1's batch is ops-dirty (platform window), drain + refire rather than analyze.
- If Bedrock throttling blocks an LLM-dependent experiment, prefer deterministic-path
  levers (the standing v114+ posture) over waiting.
- Version log + WORKING_CONTEXT updated at every ship/no-ship; lessons to
  TENTATIVE_LESSONS as they happen.

## Success criteria for the alpha run itself

The run is evaluated on process, not only on Elo: (a) every experiment pre-registered
before firing, (b) no submit without a clean verdict + orchestrator approval, (c) the
belief-divergence channel (steps 3+5) demonstrably feeding at least one hypothesis,
(d) honest verdicts — refuted hypotheses closed, not massaged. Revise this doc to beta
with what the run teaches.
