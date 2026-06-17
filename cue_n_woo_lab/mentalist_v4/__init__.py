"""mentalist_v4 — Cue-n-Woo player (passphrase offense/defense + fingerprinting).

Full rewrite on the Player SDK. Strategy: docs/designs/mentalist-v4-strategy-and-design.md.
No style classifier (the axis-recovery probe showed it is at chance). The edge is
authoring passphrase questions, defending against opponents' passphrases via a harvested
table, and (scan-gated) self-report fingerprinting.
"""
