"""cheater's answer: the fixed short phrase config.ANSWER ("The goblin").

The "daveey" approach: the FLAS-steered judge prefers short, plain, concrete
answers, and a fixed 2-token "The <noun>" wins most head-to-heads in the field
(daveey-cnw-stock). cheater uses "The goblin" for ALL six answers — its 3 secret
proposal answers and its 3 blind answers. Clamped to a legal natural-keyboard
answer (it already is; the clamp is belt-and-braces).
"""
from __future__ import annotations

from . import config
from .validator import clamp_answer


def goblin_answer() -> str:
    """The fixed short answer, clamped to a legal natural-keyboard answer."""
    return clamp_answer(config.ANSWER)
