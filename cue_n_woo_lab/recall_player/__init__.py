"""recall_player — a NO-LLM, fully-programmatic Cue-n-Woo player.

Strategy (planted PHRASE-recall, matching the field-leader gabby): ask 3 private probes that
force the judge to reply with a short evocative self-description phrase, then commit those
recalled phrases as our answers. Because the judge's scoring context contains its own interview
transcript, an answer matching what it just said reads as "its own words" — and being an
in-character phrase (not a neutral digit string) it competes with the field on character-fit.
No Bedrock, no fingerprint, no answer-writer — our turn is instant, which avoids the LLM-latency
timeouts that disqualified the mentalist players. See config.py for the full rationale, including
why phrase-recall replaced the earlier digit-recall (which qualified but lost to gabby's phrase).
"""
