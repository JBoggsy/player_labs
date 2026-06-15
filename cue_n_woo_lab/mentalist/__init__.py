"""mentalist — our Cue-n-Woo player policy.

Architecture (docs/designs/player-design.md): a cheap local style classifier
identifies the judge's hidden style from 3 fixed private questions; an AWS
Bedrock Claude writer then produces short, on-topic answers in that style.
"""
