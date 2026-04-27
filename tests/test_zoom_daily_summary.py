from zoom_daily_summary import (
    anonymize_utterances,
    clean_caption_lines,
    parse_speaker_utterances,
)


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
