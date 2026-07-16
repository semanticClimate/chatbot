from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response
from starlette.responses import HTMLResponse

from backend.app.config.settings import AppSettings
from backend.app.database.db import get_logs_csv_string


router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """Help people who open the API tunnel URL in a browser by mistake."""
    return HTMLResponse(
        content="""<!doctype html>
<meta charset="utf-8">
<title>Climate Academy API</title>
<h1>Climate Academy API</h1>
<p>This host is the <strong>API server</strong>, not the chat page in your browser.</p>
<p>Open the <strong>web client</strong> URL you were given (another
<code>*.trycloudflare.com</code> hostname) to use the chat UI.</p>
<p>Checks: <a href="/health">/health</a> · <a href="/ready">/ready</a></p>
""",
    )

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}



@router.get("/ready")
def ready(request: Request) -> dict[str, Any]:
    s: AppSettings = request.app.state.settings
    col = request.app.state.collection
    html_ok = s.html_path.is_file()
    try:
        n = col.count()
    except Exception:
        n = 0
    return {
        "ready": bool(html_ok and n > 0),
        "chunk_count": n,
        "html_exists": html_ok,
    }


@router.get("/logs/export")
def logs_export_csv() -> Response:
    """SQLite-backed interaction logs as CSV (same data as Streamlit analytics download)."""
    csv_str = get_logs_csv_string()
    if not csv_str.strip():
        csv_str = "id,timestamp,chat_id,user_query,bot_response,feedback\n"
    return Response(
        content=csv_str.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="chatbot_logs.csv"'},
    )
