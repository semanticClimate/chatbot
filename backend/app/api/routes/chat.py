import logging

from typing import Any


from fastapi import APIRouter

from fastapi import HTTPException

from fastapi import Request


from backend.app.api.models import (

    AskRequest,

    RetrieveRequest,

)


from backend.app.config.settings import AppSettings


from backend.app.database.db import (

    log_interaction,

)


from backend.app.services.chat_service import (

    run_ask,

    run_retrieve,

)


from backend.app.services.conversation import (

    append_turn,

    normalize_conversation,

)


router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/retrieve")
def retrieve_ep(request: Request, body: RetrieveRequest) -> dict[str, Any]:
    if body.top_k is not None and (body.top_k < 1 or body.top_k > 100):
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 100")
    s: AppSettings = request.app.state.settings
    chunks = run_retrieve(
        body.query,
        request.app.state.collection,
        request.app.state.embedder,
        s,
        top_k=body.top_k,
    )
    return {"chunks": chunks}


