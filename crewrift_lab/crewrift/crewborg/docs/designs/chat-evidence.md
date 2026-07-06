# Unified chat & meeting-behavior evidence

**Status:** design, not yet implemented (2026-07-05).

## Why

Two independent chat parsers exist today and disagree with each other:

- `strategy/meeting/chat_read.py` — a proper spaCy dependency parse (handles negation
  scope, victim-vs-suspect disambiguation). Used only for our own outgoing chat's
  implied vote and for the deterministic fallback's bandwagon target.
- `strategy/social_evidence.py` — a cruder regex/keyword tally (`ACCUSE_HINT`/
  `DEFEND_HINT` + a literal color-word match, no negation handling beyond one phrase).
  Its output (`accusations_made`/`times_accused`/`times_defended`) is what actually
  feeds the trained suspicion model.

Beyond that split, several behaviors that plausibly carry real signal aren't captured
at all: who speaks first in a meeting, whether a vote was cast immediately or only
after the field already piled on, and whether a chat claim about location/venting
holds up against what we actually witnessed. Chat is also read by the meeting LLM
every call, but nothing about that reading is retained or verified — it's discarded
after the LLM's own turn.

This is layer 1 only: a unified **extraction** mechanism. Trust-weighting by speaker
credibility over time and deception-pattern modeling are deferred to a follow-on
design once this layer's real output is visible.

## Architecture

Three module roles, one direction of data flow:

1. **`chat_evidence.py`** (new — replaces `chat_read.py`, absorbs `social_evidence.py`'s
   text-parsing half). Pure parsing: `ChatEvent` + `belief` (for known colors/rooms/
   vents) → structured `ChatClaim`s. No side effects; fully unit-testable in isolation.
   Keeps `chat_read.py`'s dependency-parse logic (it's already the good version) and
   deletes `social_evidence.py`'s regex tally. Also owns claim **verification**
   (below) since it's claim-specific.
2. **`social_evidence.py`** (kept, expanded) — stays the per-tick orchestrator that
   folds parsed signal into cumulative `PlayerRecord` state (exactly its role today
   for votes and meeting-callers). Now calls `chat_evidence.py` instead of its own
   regex, and gains two new responsibilities that fit this role rather than the
   parser's: **vote-timing** (diffing the vote-tally snapshot it already sees every
   tick) and **speaking order** (derived from `chat_log` ticks it already has).
3. **The meeting LLM** (`MeetingDecision` schema, Approach B) — gains one optional
   field carrying its own read on recent messages. Rides the call that's already
   happening every turn; no new latency, no new failure mode beyond "field missing,"
   in which case spaCy's independent pass over the same messages is what's used.

**spaCy is the floor both paths always have; the LLM field is enrichment on top when
available** — not a fallback relationship, a floor-plus-enrichment one. Both paths'
output converges into the *same* `ChatClaim` shape and the *same* `PlayerRecord.claims`
list (`source="spacy"` vs `source="llm"`), which is the actual point of unifying: one
system, not two.

**Scope boundary:** this design covers extraction, verification, and storage. It does
NOT wire the new signals into `suspicion_weights.json` (a separate refit step, same as
any new feature) and does NOT feed the LLM's own tags back into its next-turn context
(a reasonable future extension once we've seen what the tags actually produce).

## Data model

```python
ClaimType = Literal["accusation", "defense", "location", "vent", "task"]
VerificationStatus = Literal["confirmed", "contradicted", "unconfirmed"]

class ChatClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    tick: int
    speaker_color: str | None
    target_color: str                       # who the claim is ABOUT (== speaker for a self-alibi)
    claim_type: ClaimType
    place_name: str | None = None           # matched room/vent name; only for location/vent/task claims
    verification: VerificationStatus | None = None   # set by verify_claim(); None for non-verifiable types
    source: Literal["spacy", "llm"] = "spacy"
```

One message can yield multiple claims (e.g. "Blue was in Reactor when the body
dropped, sus" → an accusation claim *and* a location claim, both `target_color="blue"`).

`PlayerRecord` additions:

- `claims: list[ChatClaim]` — every claim where `target_color` is this player,
  appended as parsed. Mirrors the existing `events: list[PlayerEvent]` pattern: raw
  structured log, aggregated by whoever needs a number later (same as
  `_fitted_features()` does today over `record.events`) rather than pre-committing to
  a fixed set of scalar counters before real data exists.
- `spoke_first_count: int` — cumulative, one increment per meeting.
- `vote_history: list[VoteCast]` — the detailed option (chosen over a cheaper scalar
  accumulator, for the same reason as `claims`: per-meeting granularity lets later
  analysis ask "did they always bandwagon or only sometimes," which a summed ratio
  can't answer):

  ```python
  class VoteCast(BaseModel):
      model_config = ConfigDict(frozen=True, extra="forbid")
      meeting_tick: int              # phase_start_tick — identifies the meeting
      ticks_after_meeting_start: int
      target_color: str              # skip votes aren't timing-interesting; not recorded here
      rank: int                      # 1 = first to vote among non-skip votes this meeting
  ```

  The existing `votes_cast`/`votes_skipped`/`voted_against_me`/`vote_agreed_with_me`
  counters are untouched — they answer "did they vote for me"; `vote_history` answers
  "how fast."

`MeetingDecision` extension (Approach B):

```python
class ChatEvidenceTag(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    speaker_color: str
    target_color: str
    stance: Literal["accuse", "defend", "neutral"]
    claim_type: ClaimType
    credibility: float | None = None        # the LLM's own judgment; None = no opinion offered
    note: str | None = None                 # e.g. "contradicts their own earlier claim"

# MeetingDecision gains:
chat_evidence: list[ChatEvidenceTag] = []   # default empty — old-shape responses still validate
```

## Data flow

**Chat, per new message:** `ChatEvent` observed → `chat_evidence.py` parses it into
zero or more `ChatClaim`s (`source="spacy"`) → for `location`/`vent`/`task` claims
(the three verifiable-against-our-own-observations types — `accusation`/`defense` are
suspicion stances, not checkable facts), `verify_claim()` fills in `.verification` →
each claim appended to `belief.roster[claim.target_color].claims`.

**Votes, per tick (the new part):** `social_evidence.py` already sees the vote-tally
snapshot every tick; today it overwrites a flat set and commits once at meeting end,
discarding order. New: each tick, diff the current `(voter, target)` set against the
previous tick's — any new pair gets its tick stamped right then, into a per-meeting
staging list (`belief.social_vote_order: list[(tick, voter, target)]`, append-only, in
order of first appearance). At meeting end, sort by tick, assign `rank` 1..N over the
non-skip votes, fold each into the voter's `PlayerRecord.vote_history`.

**Speaking order, at meeting end:** filter `chat_log` for `tick >= phase_start_tick`,
take the earliest non-self speaker, increment their `spoke_first_count` once. No new
capture — a read over data that already exists.

**The LLM path:** `context.py`'s payload is unchanged. The LLM's response optionally
includes `chat_evidence`. Each tag is validated (both colors must be in the current
roster, `claim_type` must be a real enum value — same posture `validate_meeting_decision`
already applies to `vote_target`), converted 1:1 into a `ChatClaim` with
`source="llm"`, and appended to `claims` exactly like a spaCy-sourced one.
Verification is skipped for LLM-sourced claims — the LLM's own `credibility`/`note`
*is* its judgment; running the fuzzy witnessed-event check on top would be judging the
same thing twice, two different ways. If the field is absent (fallback path, or the
LLM tags nothing that turn), nothing happens — spaCy's independent pass over the same
messages already ran and already populated `claims`, so coverage never depends on the
LLM firing.

## Error handling & validation

**spaCy unavailable → produce nothing, not something crude.** Today, if the NLP model
isn't loaded, `chat_read.py` already returns empty (deliberately — false positives
from crude keyword matching are worse than no signal), while `social_evidence.py`'s
regex tally *still fires* as a crude fallback. Consolidating removes that fallback:
if spaCy is down, chat evidence for that game is simply absent, not degraded. This is
a real behavior change from today, made deliberately, consistent with the codebase's
existing stated philosophy on this exact trade-off (`chat_read.py`'s own docstring).

**Verification defaults to "don't know," never to "false."** Visibility is inherently
partial. `contradicted` requires a *positive* conflicting observation (witnessed them
somewhere else, incompatibly, in a tight window); the absence of a matching event
stays `unconfirmed`. Treating "no matching event found" as a contradiction would
manufacture false contradictions out of ordinary blind spots.

**LLM tag validation degrades per-tag, not per-decision.** A `ChatEvidenceTag` naming
an unknown color or invalid `claim_type` is dropped silently (logged), not surfaced as
a validation error blocking the chat/vote action it rode in on.

**Dedup.** Reuse the existing `social_counted_chats`-style seen-set
(`(tick, speaker, text)`) so a message is parsed into claims exactly once.

## Testing

Consistent with the current speed-first process (no test-first discipline as a
routine step): `chat_evidence.py`'s parser and `verify_claim()` are cheap,
deterministic, pure functions — the same category of code `test_suspicion.py` and
`test_meeting_context.py` already cover, and unit tests are the fastest way to answer
specific questions about them during implementation. Not proposed as a formal gate;
the real validation is the next experience-request eval.

## Out of scope (deferred)

- Wiring the new counters/claims into `suspicion_weights.json` (needs a refit pass).
- Feeding the LLM's own `chat_evidence` tags back into its own next-turn context.
- Speaker credibility/trust scoring over time and deceiver-vs-truth-teller pattern
  modeling — the follow-on "layer 2" design this layer's real output should inform.
