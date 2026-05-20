from encyclopedia.cabook_annotate.phrase_matcher import find_non_overlapping_matches


def test_numeric_phrases_are_not_matched():
    matches = find_non_overlapping_matches(
        "Do 139. Do we still start",
        ["139", "Do"],
        {"139": "Q1", "do": "Q2"},
        ignore_case=True,
        min_term_length=2,
    )
    surfaces = [m.surface for m in matches]
    assert "139" not in surfaces
    assert "Do" in surfaces
