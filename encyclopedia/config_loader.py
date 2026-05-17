"""Load `config/annotate_cabook.toml` and resolve all paths from the repo root."""

from __future__ import annotations

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple


def _resolve(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


@dataclass(frozen=True)
class LinkSettings:
    href_template: str
    fragment_template: str
    link_class: str
    data_entry_id_attr: str
    data_canonical_term_attr: str
    wikipedia_base_url: str
    wikipedia_link_class: str
    wikidata_link_class: str
    internal_link_class: str


@dataclass(frozen=True)
class VariantSettings:
    expand_plurals: bool
    expand_verbs: bool
    min_surface_form_length: int
    strip_canonical_suffix: str


@dataclass(frozen=True)
class MatchingSettings:
    ignore_case: bool
    longest_match_first: bool
    min_term_length: int
    skip_tags: Tuple[str, ...]


@dataclass(frozen=True)
class ParagraphIdSettings:
    enabled: bool
    id_prefix: str


@dataclass(frozen=True)
class EncyclopediaPrepareSettings:
    entry_id_attribute: str
    copy_source_if_missing: bool
    overwrite_prepared: bool


@dataclass(frozen=True)
class ReportSettings:
    include_per_entry_counts: bool
    include_unmatched_surface_forms: bool


@dataclass(frozen=True)
class MediaSettings:
    media_src_prefix: str


@dataclass(frozen=True)
class AnnotatePaths:
    book_html: Path
    book_media_dir: Path
    encyclopedia_input_html: Path
    prepared_encyclopedia_html: Path
    annotated_book_html: Path
    annotation_report_json: Path
    book_with_para_ids_html: Path
    link_css: Path


@dataclass(frozen=True)
class AnnotateSettings:
    repo_root: Path
    package_dir: Path
    paths: AnnotatePaths
    links: LinkSettings
    encyclopedia_prepare: EncyclopediaPrepareSettings
    variants: VariantSettings
    matching: MatchingSettings
    paragraph_ids: ParagraphIdSettings
    report: ReportSettings
    media: MediaSettings


def load_annotate_settings(config_path: Path | None = None) -> AnnotateSettings:
    package_dir = Path(__file__).resolve().parent
    cfg_path = config_path or Path(package_dir, "config", "annotate_cabook.toml")
    raw = cfg_path.read_bytes()
    t = tomllib.loads(raw.decode("utf-8"))

    repo_root = _resolve(package_dir.parent, t["paths"]["repo_root"])
    inp = t["paths"]["input"]
    src = t["paths"]["source"]
    out = t["paths"]["output"]
    tmp = t["paths"]["temp"]
    assets = t["paths"]["assets"]
    links = t["links"]
    prep = t["encyclopedia_prepare"]
    var = t["variants"]
    match = t["matching"]
    para = t["paragraph_ids"]
    report = t["report"]
    media = t["media"]

    paths = AnnotatePaths(
        book_html=_resolve(repo_root, inp["book_html"]),
        book_media_dir=_resolve(repo_root, inp["book_media_dir"]),
        encyclopedia_input_html=_resolve(repo_root, inp["encyclopedia_html"]),
        prepared_encyclopedia_html=_resolve(repo_root, src["prepared_encyclopedia_html"]),
        annotated_book_html=_resolve(repo_root, out["annotated_book_html"]),
        annotation_report_json=_resolve(repo_root, out["annotation_report_json"]),
        book_with_para_ids_html=_resolve(repo_root, tmp["book_with_para_ids_html"]),
        link_css=_resolve(repo_root, assets["link_css"]),
    )

    return AnnotateSettings(
        repo_root=repo_root,
        package_dir=package_dir,
        paths=paths,
        links=LinkSettings(
            href_template=links["href_template"],
            fragment_template=links["fragment_template"],
            link_class=links["link_class"],
            data_entry_id_attr=links["data_entry_id_attr"],
            data_canonical_term_attr=links["data_canonical_term_attr"],
            wikipedia_base_url=links["wikipedia_base_url"],
            wikipedia_link_class=links["wikipedia_link_class"],
            wikidata_link_class=links["wikidata_link_class"],
            internal_link_class=links["internal_link_class"],
        ),
        encyclopedia_prepare=EncyclopediaPrepareSettings(
            entry_id_attribute=prep["entry_id_attribute"],
            copy_source_if_missing=bool(prep["copy_source_if_missing"]),
            overwrite_prepared=bool(prep["overwrite_prepared"]),
        ),
        variants=VariantSettings(
            expand_plurals=bool(var["expand_plurals"]),
            expand_verbs=bool(var["expand_verbs"]),
            min_surface_form_length=int(var["min_surface_form_length"]),
            strip_canonical_suffix=str(var["strip_canonical_suffix"]),
        ),
        matching=MatchingSettings(
            ignore_case=bool(match["ignore_case"]),
            longest_match_first=bool(match["longest_match_first"]),
            min_term_length=int(match["min_term_length"]),
            skip_tags=tuple(match["skip_tags"]),
        ),
        paragraph_ids=ParagraphIdSettings(
            enabled=bool(para["enabled"]),
            id_prefix=str(para["id_prefix"]),
        ),
        report=ReportSettings(
            include_per_entry_counts=bool(report["include_per_entry_counts"]),
            include_unmatched_surface_forms=bool(report["include_unmatched_surface_forms"]),
        ),
        media=MediaSettings(
            media_src_prefix=str(media["media_src_prefix"]),
        ),
    )


@lru_cache(maxsize=4)
def get_annotate_settings(config_path: str | None = None) -> AnnotateSettings:
    path = Path(config_path) if config_path else None
    return load_annotate_settings(path)
