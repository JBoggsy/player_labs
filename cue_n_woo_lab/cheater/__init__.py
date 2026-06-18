"""cheater — a deliberately trivial Cue-n-Woo player policy.

Strategy (see README.md): no classifier, no LLM. On each of the three private
probe questions it asks the judge a prompt-injection instruction telling it to
always answer "goblin"; then for all six challenge-question answers (its three
secret proposal answers and its three blind answers to the opponent's
questions) it simply submits "goblin".

It exists as a baseline / control: a measure of how the steered judge responds
to a naive injection attempt, and a floor for how a no-effort policy scores.
"""
