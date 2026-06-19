# mentalist-recall — version log

A NO-LLM, fully-programmatic Cue-n-Woo player. Strategy: planted-recall (ask the judge a
probe that forces a fixed-shape reply, then commit that reply verbatim as our secret answer —
it matches the judge's own interview transcript, which is in its scoring context). Keyed on
`(name, version)`; reconcile against the live list with
`policy_lifecycle.py versions --name mentalist-recall`.

| Version | Change | Result |
|--------|--------|--------|
| v1 | Digit-recall (jordan clone): probe forces a 10+ digit string, commit verbatim. | QUALIFIES intermittently but DQ'd in league (timeouts). Recall-timing bug: proposals committed FALLBACK digits, not recalled (me.judge lagged at propose time). |
| v2 | Fix recall timing: persistent `_phrases`/`_digits` cache harvested from me.judge on every state, so propose/answer use real recalled values. | Isolated gabby race: no timeouts, proposals commit recalled digits. BUT league DQ'd (mirror-match timeouts). And digits LOSE to gabby (digits are character-neutral; gabby plants an evocative phrase the Sonnet judge prefers). |
| v3 | Strategy switch: digit-recall → **phrase-recall** (probe forces a short evocative self-description phrase; commit verbatim). `extract_phrase` replaces `extract_digits`. | Built; superseded by v4 before full validation (v3 still carried the wedge bug). |
| v4 | **League-DQ root-cause fix:** the in-flight `pending` guard outlived its phase. After the 3rd probe we held `pending="ask"`; `_settle_pending` only cleared on `me.judge>=3`, but the proposals state arrives with me.judge LAGGING → guard never cleared → propose blocked → global phase stalls → inactive -100. Fix: track `_pending_phase`, drop the guard the instant the server's phase advances past the action's phase. Carries v3 phrase-recall. | **Wedge FIXED:** live MIRROR race (the DQ-repro config) completes cleanly, zero timeouts. Submitted to league (sub_c8b86fb6). Open: phrase-recall ties/loses to gabby head-to-head — qualifies but not yet champion-beating. |
