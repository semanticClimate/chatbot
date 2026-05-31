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


def test_body_cross_refs_are_not_surface_forms(tmp_path, fixture_settings):
    enc_html = """<html><body>
  <div role="ami_encyclopedia">
    <div role="ami_entry" data-entry-id="Q224858" term="Keeling Curve">
      <a class="wikipedia-link ca-wikipedia-link">Keeling Curve</a>
      <p class="wpage_first_para">Measurements at the
        <a class="wikipedia-link ca-wikipedia-link">Mauna Loa Observatory</a>
        in Hawaii.</p>
    </div>
    <div role="ami_entry" data-entry-id="Q622590" term="Mauna Loa Observatory">
      <a class="wikipedia-link ca-wikipedia-link">Mauna Loa Observatory</a>
    </div>
  </div>
</body></html>"""
    path = tmp_path / "crossref_encyclopedia.html"
    path.write_text(enc_html, encoding="utf-8")
    index = build_term_index(path, fixture_settings)

    assert index.phrase_to_entry_id["mauna loa observatory"] == "Q622590"
    keeling_forms = {f.lower() for f in index.entries_by_id["Q224858"].surface_forms}
    assert "mauna loa observatory" not in keeling_forms
    assert "hawaii" not in keeling_forms
