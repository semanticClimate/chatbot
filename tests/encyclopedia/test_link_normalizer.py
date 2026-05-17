from pathlib import Path

from lxml import html as lxml_html

from encyclopedia.cabook_annotate.link_normalizer import (
    absolutize_wikipedia_href,
    normalize_links_in_tree,
)


def test_absolutize_wikipedia_href():
    assert (
        absolutize_wikipedia_href("/wiki/Climate_change", "https://en.wikipedia.org")
        == "https://en.wikipedia.org/wiki/Climate_change"
    )


def test_normalize_fixes_wiki_and_classes(fixture_settings):
    html = """
    <html><body>
      <a href="/wiki/Earth" title="Earth">Earth</a>
      <a href="https://en.wikipedia.org/wiki/India">India</a>
      <a href="#note-1">back</a>
      <a href="../source/CA_encyclopedia_new.html#entry-Q1" class="ca-encyclopedia-link">term</a>
    </body></html>
    """
    root = lxml_html.fromstring(html)
    hrefs_fixed, classes_applied = normalize_links_in_tree(root, fixture_settings)
    assert hrefs_fixed == 1
    assert classes_applied >= 3

    earth = root.xpath("//a[@title='Earth']")[0]
    assert earth.get("href") == "https://en.wikipedia.org/wiki/Earth"
    assert "ca-wikipedia-link" in earth.get("class", "")

    india = root.xpath("//a[text()='India']")[0]
    assert "ca-wikipedia-link" in india.get("class", "")

    back = root.xpath("//a[@href='#note-1']")[0]
    assert "ca-internal-link" in back.get("class", "")

    ca = root.xpath("//a[@class='ca-encyclopedia-link']")[0]
    assert "ca-wikipedia-link" not in (ca.get("class") or "")
