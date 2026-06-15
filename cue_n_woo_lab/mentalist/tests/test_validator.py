"""Validator parity with the game (v2/coworld/harness.py) + repair coverage."""
import pytest

from mentalist.validator import repair_answer, validate_answer


@pytest.mark.parametrize("answer", [
    "Arr, the salty wind calls me to the docks",
    "Objection sustained",
    "one two three four five six seven eight nine ten eleven twelve",
])
def test_valid_answers_pass(answer):
    validate_answer(answer)


@pytest.mark.parametrize("answer,why", [
    ("", "empty"),
    ("ab", "under 3 non-space chars"),
    (" leading space", "leading space"),
    ("trailing space ", "trailing space"),
    ("double  space", "repeated spaces"),
    ("tab\tinside", "tab"),
    ("new\nline", "newline"),
    ("curly ’quote", "non-ascii"),
    ("!!! ???", "tokens without letters/digits"),
    ("one two three four five six seven eight nine ten eleven twelve thirteen", "13 tokens"),
])
def test_invalid_answers_raise(answer, why):
    with pytest.raises(ValueError):
        validate_answer(answer)


@pytest.mark.parametrize("raw", [
    "It’s a fine day — truly!",
    "  spaced   out\nanswer with\ttabs  ",
    "a very long answer that runs on and on and on and on and on and keeps going",
    "!!! ??? ...",  # nothing survives -> fallback
    "",
])
def test_repair_always_yields_valid(raw):
    validate_answer(repair_answer(raw))


def test_repair_folds_unicode_punctuation():
    # The apostrophe folds to ASCII; the lone em-dash token has no letter/digit
    # so it is dropped rather than kept as an illegal token.
    assert repair_answer("It’s grand — truly") == "It's grand truly"


def test_repair_truncates_to_limit():
    out = repair_answer(" ".join(f"w{i}" for i in range(30)))
    assert len(out.split(" ")) == 12
