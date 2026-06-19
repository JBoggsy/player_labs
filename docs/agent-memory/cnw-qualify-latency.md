---
name: cnw-qualify-latency
description: "Why Cue-n-Woo submissions get DQ'd (latency/timeout) and how to qualify"
metadata: 
  node_type: memory
  type: project
  originSessionId: 974bff52-7d92-49d3-b571-eddaad9f40a1
---

**Why our Cue-n-Woo agents weren't making it into the tournament** (diagnosed 2026-06-18):

Every submission was DISQUALIFIED: `status=disqualified, substatus=inactive, notes="Score <= 0"`.
Qualification gives a fresh policy a short (~13 min) window of qualifier rounds; if its **mean
round score ≤ 0** it's DQ'd. A timeout scores **-100** (the inactive party), so even a few
timeouts drag the mean ≤0 → DQ.

**Episodes time out (600s hard timer) for a chain of reasons:**
- (a) Rich/long probes make the **Sonnet judge generate long answers** — 3 sequential judge
  round-trips on a shared judge blow 600s. FIX: one-word-answer probes (`interview.PERSONA_PROBES`,
  `MENTALIST_PROBE_COUNT`). The field #1 (jordan) uses "respond only in numbers" as a latency hack.
- (b) **BUG (fixed):** our answers were SERVER-REJECTED ("N simple tokens; limit 12") → retries.
  "Simple tokens" = `ceil(len/4)` **characters** (≤48), NOT words. Our validator counted words.
  Fixed `validator.simple_token_count` + `repair_answer` to enforce the char budget.
- (c) Too many sequential probes → `MENTALIST_PROBE_COUNT` (pffast3=2, pfmin=1).
- (d) **FLEET SATURATION** (shared Sonnet judge): under load NOTHING completes regardless of our
  latency — uncontrollable, time-varying. Verified: same player completed gabby 6/6 @25-36s in a
  light window but timed out 12/12 in a saturated window (whole division dur=0 then).

**How to qualify:** submit a minimal-latency player (one-word probes, char-correct answers, few
probes) and **time the submission to a healthy fleet window** (check recent division episodes are
`complete` with low duration before submitting). Re-submit on DQ — each submission = a fresh
qualifier window = another shot at a healthy window. Latency is the controllable lever (done);
fleet timing is the rest.

**Diagnostic recipe:** membership record `notes` field gives the DQ reason; `policy_results[].avg_reward`
per episode shows who got the -100; `results.json status` (timeout vs complete) is truth — the xreq
API `completed_count` counts TIMEOUTS as "completed". Agent trace events (domain.probe/fingerprint/
authored/responded) show how far we got before the hang.

Strategy itself (persona-fit, beats the field except michaelsmith) is in [[cnw-superflood-champion]].
Players: mentalist-v4-pffast3 (2 probes), mentalist-v4-pfmin (1 probe). VERSION_LOG +
TENTATIVE_LESSONS in cue_n_woo_lab/mentalist_v4/.
