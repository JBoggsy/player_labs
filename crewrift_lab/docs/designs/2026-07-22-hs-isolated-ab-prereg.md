# Pre-registered A/B: Honor Society ISOLATED effect (crewborg-hsoff:v1 vs crewborg:v110) — written BEFORE launch

**Question.** HS has NEVER been A/B'd in isolation — it always shipped bundled (tonight's
v110-vs-v107 A/B bundles it with the palette fix). What is HS's solo contribution?

**Candidate (the OFF arm):** `crewborg-hsoff:v1` — the *identical* image to crewborg:v110
(`players-crewborg:dev`, verified byte-identical: sha256 of `strategy/honor_society.py`,
`perception/constants.py`, `modes/attend_meeting.py` inside the image == the same files at
main `9b9606c`, the v109/v110 code commit) uploaded with v110's exact recipe (LLM meetings
+ `CREWBORG_HS_SECRET`) **plus `CREWBORG_HONOR_SOCIETY=0`**. So vs the v110 baseline the
ONLY delta is the HS flag.

**Disable-path verification (code, before launch):** `_flag_on()` returns False for `"0"`;
`enabled()` = flag AND identity. That gates ALL four HS surfaces:
- send — `attend_meeting._society_chat_intent` early-returns on `enabled()` (attend_meeting.py:674);
- receive — `process_chats` only called under `if honor_society.enabled()` (attend_meeting.py:145);
- vote/accuse veto — `vote_veto` returns False when not `enabled()` (honor_society.py:419),
  covering `_submit_vote_intent` and both accusation vetoes;
- posterior pin — suspicion.py:552 keys on `belief.society_trusted`, which only
  `process_chats` populates, so it is inert when receive is off.

**Arms (matched pinned roster = Thread-1's, crewborg slot 0, natural roles,
div_acbde92a-df21-4489-859c-4510bd4445f2):**
- HS-OFF candidate: 2×100 fresh eps (paced: two separate 100-ep requests), roster
  daf-actinf-crewborg-v3:v1, softmaxwell-crewborg:v34, sasmith-crewborg-hs1:v15, notsus:v130,
  scott-crewborg-hs1:v13, crewrift-prime-crewborg-aaln-hunter-relhalpha:v6, crewborg-aaln:v25.
- HS-ON baseline: Thread 1's v110 arms `xreq_136dd84f` + `xreq_edd0f75e` (2×100 eps,
  completed 2026-07-21T23:02Z, same roster/slot/division/recipe; warehouse
  `/tmp/wh_anchor_base_v110`, 200/200 ok — verified present before launch).

Note the roster contains TWO live HS members (sasmith-crewborg-hs1:v15,
scott-crewborg-hs1:v13), so both directions of the mechanism are exercised: our announce
(they may trust us) and their announce (we may veto votes against them — only in the ON arm).

**PRIMARY outcome:** crewborg crew win rate, HS-on vs HS-off. Mechanism: the trust veto
spares crew from mis-votes against verified members, and the announce lets sasmith/scott
seats trust us (fewer votes against us → fewer mis-ejections of us).

**Honest power statement (before data):** at n=200/200 with natural roles (~150 crew eps
per arm, crew win ~27%), 80% power at α=.05 needs a ~+15pp swing — only a LARGE effect is
detectable at the episode-win level. A "HS-neutral" verdict on the primary therefore means
"no large effect", not "no effect". The decision-grade evidence at this n is the
MECHANISM level (secondaries below), which have per-meeting/per-event granularity.

**Pre-registered SECONDARY (mechanism) outcomes — measurable at this n:**
1. `meeting_vote_society_veto` count: ON arm > 0 expected, OFF arm must be exactly 0
   (if OFF > 0 the disable failed and the run is invalid).
2. HS1 announce + `honor_known_member` events: ON ~expected from Thread 1 (announce in
   138/199 eps, known-member in 188/199); OFF must be 0 (send+receive disabled).
3. Votes received by crewborg (slot 0) FROM the two HS-member policies' seats, per
   episode-in-which-we're-crew: ON < OFF expected if the announce buys trust (from
   warehouse `vote_cast` events, voter policy ∈ {sasmith-crewborg-hs1, scott-crewborg-hs1}).
4. crewborg crew ejected rate (crew seats voted out): ON < OFF expected (same mechanism).
5. Guard: imposter win rate / kills per seat unchanged (HS never touches imposter play;
   a significant imposter diff means contamination → investigate before interpreting).
6. Guard: ops-fail ~0 both arms; vote_timeouts comparable (~0-2%/arm at slot 0).

**Verdict rule (decided now):**
- HS-helps: primary crew win significantly up in ON arm, OR (primary noise AND ≥2 of
  mechanism 3/4 significantly in the predicted direction with guards clean).
- HS-hurts: primary significantly down in ON arm, or guards implicate HS.
- HS-neutral: everything else. Report the mechanism numbers regardless.

**No ship decision rides on this** — v110 (HS on) is already champion; this measures the
flag's solo contribution and informs whether future HS work (coordinated vote-piling,
challenge/response) is worth the effort. The probe name `crewborg-hsoff` is NEVER submitted.
