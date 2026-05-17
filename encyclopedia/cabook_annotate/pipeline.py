"""Run the full CABook annotation pipeline from config."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from encyclopedia.cabook_annotate.encyclopedia_index import build_term_index
from encyclopedia.cabook_annotate.html_annotator import annotate_book_html
from encyclopedia.cabook_annotate.link_normalizer import (
    inject_stylesheet_for_output,
    normalize_links_in_file,
)
from encyclopedia.cabook_annotate.media_paths import rewrite_media_in_file
from encyclopedia.cabook_annotate.prepare_encyclopedia import prepare_encyclopedia_html
from encyclopedia.config_loader import AnnotateSettings, load_annotate_settings


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _resolve_book_input(settings: AnnotateSettings) -> Path:
    paths = settings.paths
    if settings.paragraph_ids.enabled:
        _ensure_parent(paths.book_with_para_ids_html)
        shutil.copy2(paths.book_html, paths.book_with_para_ids_html)
        return paths.book_with_para_ids_html
    return paths.book_html


def _write_report(
    settings: AnnotateSettings,
    *,
    links_inserted: int,
    entry_count: int,
    surface_form_count: int,
    per_entry_counts: Dict[str, int],
) -> Path:
    report_path = settings.paths.annotation_report_json
    _ensure_parent(report_path)

    payload: Dict[str, Any] = {
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
        "config": str(Path(settings.package_dir, "config", "annotate_cabook.toml")),
        "inputs": {
            "book_html": str(settings.paths.book_html),
            "encyclopedia_input_html": str(settings.paths.encyclopedia_input_html),
        },
        "outputs": {
            "prepared_encyclopedia_html": str(settings.paths.prepared_encyclopedia_html),
            "annotated_book_html": str(settings.paths.annotated_book_html),
        },
        "temp": {
            "book_with_para_ids_html": str(settings.paths.book_with_para_ids_html),
        },
        "summary": {
            "encyclopedia_entries": entry_count,
            "surface_forms": surface_form_count,
            "links_inserted": links_inserted,
        },
    }
    if settings.report.include_per_entry_counts:
        payload["per_entry_counts"] = per_entry_counts

    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return report_path


def run_annotation_pipeline(config_path: Path | None = None) -> Dict[str, Any]:
    settings = load_annotate_settings(config_path)

    for path in (
        settings.paths.annotated_book_html,
        settings.paths.annotation_report_json,
        settings.paths.book_with_para_ids_html,
    ):
        _ensure_parent(path)

    prepared = prepare_encyclopedia_html(settings)
    term_index = build_term_index(prepared, settings)
    book_input = _resolve_book_input(settings)

    links_inserted, counts = annotate_book_html(
        book_input,
        settings.paths.annotated_book_html,
        term_index,
        settings,
    )

    normalize_links_in_file(settings.paths.annotated_book_html, settings)
    rewrite_media_in_file(settings.paths.annotated_book_html, settings)
    inject_stylesheet_for_output(
        settings.paths.annotated_book_html,
        settings.paths.link_css,
    )

    report_path = _write_report(
        settings,
        links_inserted=links_inserted,
        entry_count=len(term_index.entries_by_id),
        surface_form_count=len(term_index.phrase_to_entry_id),
        per_entry_counts=dict(counts),
    )

    return {
        "links_inserted": links_inserted,
        "entries": len(term_index.entries_by_id),
        "surface_forms": len(term_index.phrase_to_entry_id),
        "annotated_book_html": str(settings.paths.annotated_book_html),
        "prepared_encyclopedia_html": str(prepared),
        "report": str(report_path),
    }
