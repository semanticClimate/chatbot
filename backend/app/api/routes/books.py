from typing import Any

from fastapi import APIRouter,FastAPI, HTTPException, Request
from starlette.responses import HTMLResponse

from backend.app.config.settings import AppSettings

from backend.app.utils.html_sectioning import (
    load_html_file,
    parse_book_html,
)

from backend.app.rag.book_document import (
    build_annotated_book_document,
)


router = APIRouter()


def _cached_book_outline(app: FastAPI) -> list[dict[str, Any]]:
    if getattr(app.state, "_book_outline_rows", None) is None:
        s: AppSettings = app.state.settings
        raw = load_html_file(s.html_path)
        records = parse_book_html(raw)
        app.state._book_outline_rows = [
            {
                "section_number": r.section_number,
                "title": r.title,
                "heading_id": r.heading_id,
                "level": r.level,
            }
            for r in records
        ]
    return app.state._book_outline_rows


def _cached_book_html(app: FastAPI) -> str:
    if getattr(app.state, "_book_document_html", None) is None:
        app.state._book_document_html = build_annotated_book_document(app.state.settings)
    return app.state._book_document_html



@router.get("/book/outline")
def book_outline(request: Request) -> dict[str, Any]:
    """Decimal outline (§ / title) for the student book — same structure Streamlit uses for navigation."""
    s: AppSettings = request.app.state.settings
    if not s.html_path.is_file():
        raise HTTPException(status_code=503, detail="Book HTML not available")
    return {"sections": _cached_book_outline(request.app)}


@router.get("/book/document", response_class=HTMLResponse)
def book_document(request: Request) -> HTMLResponse:
    """Annotated book HTML for embedding in the browser client iframe."""
    s: AppSettings = request.app.state.settings
    if not s.html_path.is_file():
        raise HTTPException(status_code=503, detail="Book HTML not available")
    return HTMLResponse(content=_cached_book_html(request.app))


@router.get("/book/jump")
def book_jump(
    anchor_id: str | None = None,
    section_number: str | None = None,
    heading_id: str | None = None,
) -> dict[str, Any]:
    jump_type = "para" if anchor_id else "section"
    return {
        "anchor_id": anchor_id,
        "section_number": section_number,
        "heading_id": heading_id or "",
        "jump_type": jump_type,
    }


