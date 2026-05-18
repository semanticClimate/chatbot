from pathlib import Path

from lxml import html as lxml_html

from encyclopedia.cabook_annotate.media_paths import rewrite_media_src_in_tree
from encyclopedia.config_loader import load_annotate_settings


def test_rewrite_media_src_points_to_input_media(tmp_path):
    cfg = tmp_path / "cfg.toml"
    out_html = tmp_path / "output" / "book.html"
    out_html.parent.mkdir(parents=True)
    out_html.write_text(
        '<html><body><img src="media/image1.png" alt="test"></body></html>',
        encoding="utf-8",
    )

    repo = Path(__file__).resolve().parents[2]
    cfg.write_text(
        f"""
[paths]
repo_root = "{repo.as_posix()}"

[paths.input]
book_html = "input/full_student_book.html"
book_media_dir = "input/media"
encyclopedia_html = "input/full_student_book.html"

[paths.source]
prepared_encyclopedia_html = "{(tmp_path / 'enc.html').as_posix()}"

[paths.output]
annotated_book_html = "{out_html.as_posix()}"
annotation_report_json = "{(tmp_path / 'report.json').as_posix()}"

[paths.temp]
book_with_para_ids_html = "{(tmp_path / 'temp.html').as_posix()}"

[paths.assets]
link_css = "{(repo / 'encyclopedia' / 'assets' / 'cabook_links.css').as_posix()}"

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
""",
        encoding="utf-8",
    )
    settings = load_annotate_settings(cfg)
    root = lxml_html.fromstring(out_html.read_text(encoding="utf-8"))
    updated = rewrite_media_src_in_tree(
        root,
        out_html,
        settings.paths.book_media_dir,
        settings.media.media_src_prefix,
    )
    assert updated == 1
    src = root.xpath("//img/@src")[0]
    assert not src.startswith("media/")
    resolved = (out_html.parent / src).resolve()
    assert resolved.name == "image1.png"
    assert resolved.is_file()
