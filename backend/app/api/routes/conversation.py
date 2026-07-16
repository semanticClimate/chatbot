from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from typing import Any
from backend.app.api.models import (
    ConversationImportBody,
    ConversationExportBody,
)

from backend.app.services.conversation import (
    conversation_from_csv,
    conversation_to_csv,
    normalize_conversation,
)


router = APIRouter()


@router.post("/conversation/import")
def conversation_import_ep(body: ConversationImportBody) -> dict[str, Any]:
    return {"conversation": normalize_conversation(body.messages)}



@router.post("/conversation/import_csv")
async def conversation_import_csv(request: Request) -> dict[str, Any]:
    raw = (await request.body()).decode("utf-8", errors="replace")
    conv = normalize_conversation(conversation_from_csv(raw))
    return {"conversation": conv}


@router.post("/conversation/export")
def conversation_export_ep(body: ConversationExportBody) -> Response:
    fmt = (body.format or "json").lower().strip()
    norm = normalize_conversation(body.conversation)
    if fmt == "csv":
        csv_text = conversation_to_csv(norm)
        return Response(
            content=csv_text.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="conversation.csv"'},
        )
    if fmt == "json":
        return JSONResponse({"conversation": norm})
    raise HTTPException(status_code=400, detail="format must be json or csv")

