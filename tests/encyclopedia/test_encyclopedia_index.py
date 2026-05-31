from encyclopedia.cabook_annotate.encyclopedia_index import build_term_index
from encyclopedia.cabook_annotate.prepare_encyclopedia import prepare_encyclopedia_html


def test_build_term_index_includes_synonyms_and_plurals(fixture_settings):
    prepared = prepare_encyclopedia_html(fixture_settings)
    index = build_term_index(prepared, fixture_settings)
    assert "Q7174" in index.entries_by_id
    assert "democracy" in index.phrase_to_entry_id
    assert "democracies" in index.phrase_to_entry_id
    assert index.entries_by_id["Q7174"].href.endswith("#entry-Q7174")


def test_prepared_encyclopedia_has_anchor_ids(fixture_settings):
    prepared = prepare_encyclopedia_html(fixture_settings)
    html = prepared.read_text(encoding="utf-8")
    assert 'id="entry-Q7174"' in html
    assert 'id="entry-Q668"' in html
