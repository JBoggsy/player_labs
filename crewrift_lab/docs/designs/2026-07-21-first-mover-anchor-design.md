# First-mover anchoring: immediate crew accusation at meeting start

**Status:** implemented on this branch; A/B'd as `crewborg-anchor:v1` (probe upload,
not submitted). Evidence base: the 2026-07-02 chat tactics deep-dive
(`crewrift/crewborg/docs/reports/2026-07-02-chat-tactics-deep-dive.html`).

## Hypothesis (mechanistic, pre-registered)

> When crewborg (as crew, alive) already has a vote-bar-clearing suspect at meeting
> start (`top_suspect` non-None), emitting its evidence-cited accusation **on the
> first meeting tick** — before any other player speaks, instead of after the
> ~2.6 s meeting_start LLM round-trip — increases the probability that its target
> is ejected that same meeting, because voters anchor on the **first named target**:
> the first accusation in a meeting collects the pile, largely independent of its
> correctness.

Observable: same-meeting ejection-of-accused-target rate for crewborg crew
accusations (the "conversion" metric of the chat study), plus crew win rate.

## Premise check (2026-07-21, /tmp/wh10 — 199 live league episodes, 446 meetings)

Scripts: `/tmp/anchor_premise/premise.py`, `premise2.py` (throwaway; methodology:
meetings = Voting phase windows; ejections = `died` events attributed to the most
recent meeting ≤3000 ticks prior — ejection deaths land ~72 ticks after VoteResult;
accusation = first substantive chat per speaker naming another player's color).

1. **crewborg never anchors today.** Among meetings where it spoke substantively
   (n=83): first 18%, last 52%. Median first-chat delay from meeting start:
   crewborg **55 ticks**; jordan-crewborg-aaln / crewborg-mv / relhalpha (the
   top-3 converters) all **median 1 tick**. The delay ≈ the meeting_start LLM
   latency (median 2.6 s ≈ 62 ticks) — with the LLM enabled, crewborg *always*
   waits for the round-trip (or its 3 s timeout) before any chat.
2. **First-named targets get ejected far more.** Contested meetings (≥2 targets
   named): P(ejected | named first) = **28.7%** (n=324) vs **12.5%** later-named
   (n=488), z=5.77. Controlling for correctness: imposter targets 36.9% vs 20.8%;
   crew (wrong) targets 21.7% vs 9.0% — anchoring, not just accuracy.
3. crewborg crew accusations in this sample: n=52, conversion 26.9%, accuracy
   59.6% — accuracy fine, conversion mid-poor, consistent with the 07-02 study.

## The change (minimal)

`modes/attend_meeting.py`, LLM-enabled path only (the deterministic LLM-off path
already accuses on the first decide tick — no change there):

- New `_first_mover_accusation_intent()`, checked right after the dead-mute guard
  and **before** any LLM machinery: crew + alive + no chat sent yet + no LLM call
  started + `top_suspect(belief)` clears the vote bar + Honor-Society vote veto
  passes + `build_accusation` has citable evidence → send the accusation
  immediately (first chat slot) and couple `_tentative_vote` to the target.
- Race safety, by construction rather than by locking: the branch runs before the
  meeting_start trigger can fire (both gate on virgin per-meeting state), so the
  accusation is out before the first LLM call starts. It sets
  `_deterministic_chatted` (so an LLM-failure fallback to `_decide_crewmate`
  cannot chat a second time) and routes through `_send_chat_intent` (so the text
  lands in `_sent_chat_texts` — an identical later LLM chat is suppressed by the
  existing duplicate gate, and different follow-ups obey the normal cooldown).
  The subsequent meeting_start LLM call proceeds normally and sees the accusation
  in its own chat context + tentative vote.
- Vote integrity unchanged: the target passes `_vote_target_corroborated` by
  definition (`top_suspect == target`), so the early-submit/deadline vote lands on
  exactly whom we accused — the existing accuse-whom-you-vote anti-tell.
- Imposter path untouched; dead seats untouched; LLM-off path byte-identical.

Trace: `meeting_first_mover_accusation` event + counter, and the
`meeting_decision` record fires with `path="first_mover_accuse"`.

## A/B (pre-registered before launch)

- Arms: candidate `crewborg-anchor:v1` (this branch, v107/v110 recipe) vs the
  current validated baseline (v110 if Thread 1 cleared it, else v107); matched
  pinned roster (Thread-1 roster), crewborg pinned slot 0, natural roles,
  ~100 eps/arm, paced ≤400 total concurrent across ALL running xreqs.
- PRIMARY: crewborg-crew accusation → same-meeting ejection-of-target conversion
  rate UP vs baseline (warehouse chat/vote/died events, premise-check method).
- Guards: crew win rate not worse; no new vote_timeouts; imposter win rate /
  kills unchanged (crew-only change); ops-fail ~0 both arms.
- Ship decision: this lever ships inside the next crewborg version — the probe
  name is never submitted to the league.
