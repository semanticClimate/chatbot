from pathlib import Path

from encyclopedia.cabook_annotate.pipeline import run_annotation_pipeline


def test_run_annotation_pipeline(annotate_config_path: Path):
    result = run_annotation_pipeline(annotate_config_path)
    assert result["links_inserted"] >= 3
    assert Path(result["annotated_book_html"]).exists()
    assert Path(result["report"]).exists()
