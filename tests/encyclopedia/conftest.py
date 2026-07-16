from pathlib import Path

import pytest

from encyclopedia.config_loader import AnnotateSettings, load_annotate_settings


FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def annotate_config_path(tmp_path):
    base = load_annotate_settings()
    config_text = f"""
[paths]
repo_root = "{tmp_path.as_posix()}"

[paths.input]
book_html = "{(FIXTURES / 'sample_book.html').as_posix()}"
book_media_dir = "{(FIXTURES.parents[2] / 'input' / 'media').as_posix()}"
encyclopedia_html = "{(FIXTURES / 'sample_encyclopedia.html').as_posix()}"

[paths.source]
prepared_encyclopedia_html = "{(tmp_path / 'source' / 'CA_encyclopedia_new.html').as_posix()}"

[paths.output]
annotated_book_html = "{(tmp_path / 'output' / 'book_annotated.html').as_posix()}"
annotation_report_json = "{(tmp_path / 'output' / 'report.json').as_posix()}"

[paths.temp]
book_with_para_ids_html = "{(tmp_path / 'temp' / 'book_para.html').as_posix()}"

[paths.assets]
link_css = "{(base.package_dir / 'assets' / 'cabook_links.css').as_posix()}"

[media]
media_src_prefix = "media"

[links]
href_template = "../source/CA_encyclopedia_new.html#{{fragment}}"
fragment_template = "entry-{{wikidata_id}}"
link_class = "ca-encyclopedia-link"
data_entry_id_attr = "data-entry-id"
data_canonical_term_attr = "data-canonical-term"
wikipedia_base_url = "https://en.wikipedia.org"
wikipedia_link_class = "ca-wikipedia-link"
wikidata_link_class = "ca-wikidata-link"
internal_link_class = "ca-internal-link"

[encyclopedia_prepare]
entry_id_attribute = "id"
copy_source_if_missing = true
overwrite_prepared = true

[variants]
expand_plurals = true
expand_verbs = false
min_surface_form_length = 3
strip_canonical_suffix = " (canonical)"

[matching]
ignore_case = true
longest_match_first = true
min_term_length = 3
skip_tags = ["a", "script", "style", "title", "noscript"]

[paragraph_ids]
enabled = false
id_prefix = "cabook-p-"

[report]
include_per_entry_counts = true
include_unmatched_surface_forms = false
"""
    cfg = tmp_path / "annotate_cabook.toml"
    cfg.write_text(config_text, encoding="utf-8")
    return cfg


@pytest.fixture
def fixture_settings(annotate_config_path) -> AnnotateSettings:
    return load_annotate_settings(annotate_config_path)
