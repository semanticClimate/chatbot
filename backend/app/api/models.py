from typing import Any

from pydantic import BaseModel, Field, field_validator


RESPONSE_LANGUAGE_CODES = frozenset(
    {"en", "fr", "es", "pt", "hi"}
)


class AskRequest(BaseModel):

    question: str = Field(..., min_length=1)

    conversation: list[dict[str, Any]] = Field(
        default_factory=list
    )

    top_k: int | None = None

    chat_id: str | None = None

    message_id: str | None = None

    response_language: str = Field(default="en")

    @field_validator("response_language")
    @classmethod
    def _normalize_response_language(cls, v: str) -> str:

        code = (v or "en").strip().lower()

        if code not in RESPONSE_LANGUAGE_CODES:

            raise ValueError(
                "response_language must be one of: "
                + ", ".join(sorted(RESPONSE_LANGUAGE_CODES))
            )

        return code


class RetrieveRequest(BaseModel):

    query: str = Field(..., min_length=1)

    top_k: int | None = None


class ConversationImportBody(BaseModel):

    messages: list[dict[str, Any]]


class ConversationExportBody(BaseModel):

    conversation: list[dict[str, Any]]

    format: str = "json"
