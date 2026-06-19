"""recall_player — a NO-LLM, fully-programmatic Cue-n-Woo player.

Strategy (v6, SELF-REFERENTIAL SIGNATURE — copied from the live #1 player outbounds): in the
interview, make the judge RECORD a labeled "signature" motto; then author our proposal questions
to explicitly reference that recorded signature ("Earlier you recorded your CORE SIGNATURE...
reproduce that exact phrase") and answer with it. The judge sees its own recorded keyword echoed
in both the question and our secret, so it picks our answer ~1.00 deterministically — beating
plain planted-recall (gabby/our v4), which only HOPES the judge prefers our phrase (a coin flip).
No Bedrock, no fingerprint, no answer-writer — our turn is instant, avoiding the LLM-latency
timeouts that disqualified the mentalist players. See config.py for the full rationale and the
evolution: digit-recall → phrase-recall (v4) → self-referential signature (v6).
"""
