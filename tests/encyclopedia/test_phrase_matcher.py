from encyclopedia.cabook_annotate.phrase_matcher import find_non_overlapping_matches


def test_longest_match_first():
    phrases = ["climate", "climate change"]
    phrase_to_id = {"climate": "Q1", "climate change": "Q2"}
    text = "We face climate change today."
    matches = find_non_overlapping_matches(
        text,
        sorted(phrases, key=len, reverse=True),
        phrase_to_id,
        ignore_case=True,
        min_term_length=3,
    )
    assert len(matches) == 1
    assert matches[0].phrase == "climate change"
    assert matches[0].entry_id == "Q2"


def test_word_boundary():
    matches = find_non_overlapping_matches(
        "Indian democracy",
        ["india"],
        {"india": "Q668"},
        ignore_case=True,
        min_term_length=3,
    )
    assert matches == []
