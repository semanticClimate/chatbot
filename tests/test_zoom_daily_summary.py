from pathlib import Path

from zoom_daily_summary import (
    SUMMARY_WARNING,
    apply_name_aliases_to_text,
    apply_regex_name_corrections_to_text,
    attendees_markdown_table,
    anonymize_utterances,
    clean_caption_lines,
    collect_session_attendees,
    normalize_speaker_name,
    parse_speaker_utterances,
    prepend_warning_and_attendees,
)

EXISTING_TRANSCRIPT_PATH = Path("tests", "resources", "2026_04_25_anonymized.txt")


def test_clean_caption_lines_removes_timestamp_only_rows():
    raw = "00:00:03\n\n00:00:07 Alice: Hello\nRandom text"
    lines = clean_caption_lines(raw)
    assert lines == ["00:00:07 Alice: Hello", "Random text"], (
        f"Expected content lines only, got {lines}"
    )


def test_parse_speaker_utterances_extracts_speaker_and_text():
    lines = ["00:00:07 Alice Smith: hello team", "No prefix line"]
    utterances = parse_speaker_utterances(lines)
    assert utterances[0] == ("Alice Smith", "hello team"), (
        f"Expected parsed speaker tuple, got {utterances[0]}"
    )
    assert utterances[1] == (None, "No prefix line"), (
        f"Expected no-speaker tuple, got {utterances[1]}"
    )


def test_anonymize_utterances_replaces_speakers_and_contact_info():
    utterances = [
        ("Alice Smith", "Contact me at alice@example.com or +44 1234 567890"),
        ("Bob Jones", "Alice Smith shared docs at https://example.com"),
    ]
    anonymized, mapping = anonymize_utterances(utterances)

    assert "PERSON_01" in anonymized and "PERSON_02" in anonymized, (
        f"Expected speaker placeholders in anonymized transcript, got: {anonymized}"
    )
    assert "alice@example.com" not in anonymized, (
        f"Expected email redaction in anonymized transcript, got: {anonymized}"
    )
    assert "https://example.com" not in anonymized, (
        f"Expected URL redaction in anonymized transcript, got: {anonymized}"
    )
    assert mapping.people["Alice Smith"] == "PERSON_01", (
        f"Expected deterministic mapping for Alice Smith, got {mapping.people}"
    )


def test_anonymize_utterances_replaces_first_name_alias_mentions():
    utterances = [
        ("Alice Smith", "I reviewed this with Bob."),
        ("Bob Jones", "Thanks Alice, I agree."),
    ]
    anonymized, _ = anonymize_utterances(utterances)

    assert "Alice" not in anonymized and "Bob" not in anonymized, (
        f"Expected first-name mentions to be anonymized, got: {anonymized}"
    )
    assert anonymized.count("PERSON_01") >= 2, (
        f"Expected PERSON_01 for both speaker and alias mentions, got: {anonymized}"
    )
    assert anonymized.count("PERSON_02") >= 2, (
        f"Expected PERSON_02 for both speaker and alias mentions, got: {anonymized}"
    )


def test_normalize_speaker_name_with_alias_map_is_case_insensitive():
    alias_map = {"Alina": "Aleena"}
    assert normalize_speaker_name("alina", alias_map) == "Aleena"
    assert normalize_speaker_name(" Alina ", alias_map) == "Aleena"


def test_collect_session_attendees_applies_alias_map():
    utterances = [
        ("Alina", "Thanks."),
        ("Aleena", "Adding context."),
        ("Bob", "Question."),
        ("ALINA", "Follow-up."),
    ]
    attendees = collect_session_attendees(utterances, alias_map={"Alina": "Aleena"})
    assert attendees[0] == ("Aleena", 3), f"Expected Aleena merge, got: {attendees}"
    assert ("Bob", 1) in attendees, f"Expected Bob row, got: {attendees}"


def test_attendees_markdown_table_has_expected_headers():
    table = attendees_markdown_table([("Aleena", 3), ("Bob", 1)])
    assert "| Speaker | Turns |" in table
    assert "| Aleena | 3 |" in table


def test_apply_name_aliases_to_text_replaces_case_insensitive_whole_words():
    text = "Alina spoke. Later ALINA added detail. Malina should stay unchanged."
    replaced = apply_name_aliases_to_text(text, {"Alina": "Aleena"})
    assert "Aleena spoke." in replaced
    assert "Later Aleena added detail." in replaced
    assert "Malina should stay unchanged." in replaced


def test_apply_regex_name_corrections_to_text_replaces_matching_variants():
    text = "Alina spoke. A1ina added notes. Malina should stay unchanged."
    replaced = apply_regex_name_corrections_to_text(text, [(r"\bA[l1]ina\b", "Aleena")])
    assert "Aleena spoke." in replaced
    assert "Aleena added notes." in replaced
    assert "Malina should stay unchanged." in replaced


def test_prepend_warning_and_attendees_places_warning_first():
    attendees = attendees_markdown_table([("Aleena", 2)])
    summary = "## Daily Summary\n- Item"
    combined = prepend_warning_and_attendees(summary, attendees)
    assert combined.startswith(SUMMARY_WARNING)
    assert "## Attendees" in combined
    assert "## Daily Summary" in combined


def test_collect_session_attendees_applies_regex_corrections():
    utterances = [
        ("Alina", "Thanks."),
        ("A1ina", "Adding context."),
        ("Bob", "Question."),
    ]
    attendees = collect_session_attendees(
        utterances, regex_corrections=[(r"\bA[l1]ina\b", "Aleena")]
    )
    assert attendees[0] == ("Aleena", 2), f"Expected Aleena merge from regex, got: {attendees}"
    assert ("Bob", 1) in attendees, f"Expected Bob row, got: {attendees}"


def test_existing_transcript_extracts_non_empty_speaker_list():
    raw_text = EXISTING_TRANSCRIPT_PATH.read_text(encoding="utf-8")
    lines = clean_caption_lines(raw_text)
    utterances = parse_speaker_utterances(lines)
    attendees = collect_session_attendees(utterances)
    assert attendees, f"Expected attendee rows from {EXISTING_TRANSCRIPT_PATH}, found none"


def test_existing_transcript_attendees_include_known_speakers():
    raw_text = EXISTING_TRANSCRIPT_PATH.read_text(encoding="utf-8")
    lines = clean_caption_lines(raw_text)
    utterances = parse_speaker_utterances(lines)
    attendees = collect_session_attendees(utterances)
    attendee_names = {speaker for speaker, _ in attendees}
    expected_speakers = {
        "Peter Murray-Rust",
        "Renu Kumari",
        "Sai Nikhil",
        "Aleena Harold Peter",
        "Udita Agarwal",
        "Mahi Bhardwaj",
    }
    assert attendee_names == expected_speakers, (
        f"Expected speakers {sorted(expected_speakers)} from {EXISTING_TRANSCRIPT_PATH}, "
        f"got {sorted(attendee_names)}"
    )
