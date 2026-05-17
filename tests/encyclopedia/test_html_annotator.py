from lxml import html as lxml_html

from encyclopedia.cabook_annotate.encyclopedia_index import build_term_index
from encyclopedia.cabook_annotate.html_annotator import annotate_book_html
from encyclopedia.cabook_annotate.prepare_encyclopedia import prepare_encyclopedia_html


def test_annotate_book_links_terms(fixture_settings):
    prepared = prepare_encyclopedia_html(fixture_settings)
    index = build_term_index(prepared, fixture_settings)
    out = fixture_settings.paths.annotated_book_html
    total, counts = annotate_book_html(
        fixture_settings.paths.book_html,
        out,
        index,
        fixture_settings,
    )
    assert total >= 3
    assert counts["Q7174"] >= 2
    assert counts["Q668"] >= 1

    root = lxml_html.parse(str(out)).getroot()
    links = root.xpath(".//a[contains(@class, 'ca-encyclopedia-link')]")
    assert len(links) == total

    nested = root.xpath("//a[@href='https://example.com']//a")
    assert nested == []
