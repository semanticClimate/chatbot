"""Single encyclopedia entry HTML for the browser client iframe."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from lxml import etree
from lxml import html as lxml_html

from backend.app.config.settings import AppSettings

_ENTRY_ID_RE = re.compile(r"^Q\d+$", re.IGNORECASE)

_PKG_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PKG_DIR.parent


def prepared_encyclopedia_path(settings: AppSettings | None = None) -> Path:
    root = settings.root_dir if settings else _REPO_ROOT
    return root / "data" / "encyclopedia" / "source" / "CA_encyclopedia_new.html"


def annotated_book_path(settings: AppSettings | None = None) -> Path:
    root = settings.root_dir if settings else _REPO_ROOT
    return root / "data" / "encyclopedia" / "output" / "full_student_book_annotated.html"


def link_css_path() -> Path:
    return _REPO_ROOT / "data" / "encyclopedia" / "assets" / "cabook_links.css"


def normalize_entry_id(entry_id: str) -> str:
    raw = (entry_id or "").strip()
    if not raw:
        raise ValueError("entry_id is required")
    if raw.lower().startswith("entry-"):
        raw = raw[6:]
    if not _ENTRY_ID_RE.match(raw):
        raise ValueError("entry_id must be a Wikidata id like Q125928")
    return raw


def _entry_panel_css() -> str:
    return """
body {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 15px;
  line-height: 1.75;
  color: #1a1a1a;
  background: #f8faf9;
  padding: 16px 18px 24px;
}
.encyclopedia-entry-shell {
  max-width: 52rem;
}
.encyclopedia-entry-shell .entry-checkboxes {
  display: none;
}
sub, sup {
  font-size: 0.75em;
  line-height: 0;
  vertical-align: baseline;
  position: relative;
}
sub { bottom: -0.25em; }
sup { top: -0.35em; }
.encyclopedia-empty {
  color: #4f6257;
  font-size: 0.95rem;
  margin: 0;
}
"""


@lru_cache(maxsize=1)
def _load_encyclopedia_tree(encyclopedia_path: str) -> etree._Element:
    parser = lxml_html.HTMLParser(encoding="utf-8")
    return lxml_html.parse(encyclopedia_path, parser).getroot()


def extract_entry_inner_html(entry_id: str, encyclopedia_path: Path) -> str:
    """Serialize one ami_entry div (without page chrome)."""
    wid = normalize_entry_id(entry_id)
    root = _load_encyclopedia_tree(str(encyclopedia_path.resolve()))
    nodes = root.xpath(
        f".//div[@role='ami_entry' and @data-entry-id='{wid}']"
    )
    if not nodes:
        anchor = f"entry-{wid}"
        nodes = root.xpath(f".//*[@id='{anchor}']")
    if not nodes:
        raise LookupError(f"Encyclopedia entry not found: {wid}")

    entry = nodes[0]
    return etree.tostring(entry, encoding="unicode", method="html")


def build_encyclopedia_entry_document(entry_id: str, settings: AppSettings) -> str:
    enc_path = prepared_encyclopedia_path(settings)
    if not enc_path.is_file():
        raise FileNotFoundError(f"Encyclopedia HTML not found: {enc_path}")

    inner = extract_entry_inner_html(entry_id, enc_path)
    link_css = ""
    css_file = link_css_path()
    if css_file.is_file():
        link_css = f"<style>\n{css_file.read_text(encoding='utf-8')}\n</style>"

    panel_css = f"<style>\n{_entry_panel_css()}\n</style>"
    title = normalize_entry_id(entry_id)
    script = """
<script>
(function() {
  document.addEventListener("click", function(e) {
    var anchor = e.target.closest("a");
    if (!anchor) return;
    var href = anchor.getAttribute("href");
    if (!href) return;
    var isWikipedia = anchor.classList.contains("ca-wikipedia-link") || anchor.classList.contains("wikipedia-link") || href.indexOf("wikipedia.org") >= 0;
    var isWikidata = anchor.classList.contains("ca-wikidata-link") || anchor.classList.contains("wikidata-link") || href.indexOf("wikidata.org") >= 0;
    if (isWikipedia || isWikidata) {
      e.preventDefault();
      var source = isWikipedia ? "Wikipedia" : "Wikidata";
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({
          type: "ca-external-link-open",
          url: anchor.href,
          source: source
        }, "*");
      }
    }
  });
})();
</script>
"""
    return (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='utf-8'/>"
        f"<title>Climate Academy encyclopedia — {title}</title>"
        f"{link_css}{panel_css}"
        "</head><body>"
        "<" + "div class='encyclopedia-entry-shell'>" + inner + "</" + "div>"
        f"{script}</body></html>"
    )


def build_encyclopedia_placeholder_document() -> str:
    panel_css = f"<style>\n{_entry_panel_css()}\n</style>"
    return (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='utf-8'/>"
        "<title>Climate Academy encyclopedia</title>"
        f"{panel_css}"
        "</head><body>"
        "<p class='encyclopedia-empty'>"
        "Click a highlighted term in the student book to open its encyclopedia entry here."
        "</p></body></html>"
    )
