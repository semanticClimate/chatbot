import pytest

from climate_streamlit.config_loader import get_settings
from climate_streamlit.rag.encyclopedia_document import (
    build_encyclopedia_entry_document,
    build_encyclopedia_placeholder_document,
    extract_entry_inner_html,
    normalize_entry_id,
    prepared_encyclopedia_path,
)


def test_normalize_entry_id_accepts_fragment():
    assert normalize_entry_id("entry-Q125928") == "Q125928"
    assert normalize_entry_id("Q125928") == "Q125928"


def test_normalize_entry_id_rejects_bad_ids():
    with pytest.raises(ValueError):
        normalize_entry_id("../etc/passwd")


def test_placeholder_document_has_hint():
    html = build_encyclopedia_placeholder_document()
    assert "encyclopedia entry" in html.lower()


@pytest.mark.skipif(
    not prepared_encyclopedia_path().is_file(),
    reason="prepared encyclopedia not in workspace",
)
def test_extract_known_entry():
    settings = get_settings()
    enc = prepared_encyclopedia_path(settings)
    inner = extract_entry_inner_html("Q125928", enc)
    assert "ami_entry" in inner or "encyclopedia-entry" in inner
    doc = build_encyclopedia_entry_document("Q125928", settings)
    assert "Q125928" in doc
    assert "encyclopedia-entry-shell" in doc
