"""Groq chat completion with RAG context."""

from __future__ import annotations

from typing import Optional

from backend.app.config.settings import AppSettings
from backend.app.llm.parsing import (
    escape_model_text_for_point_card,
    fallback_plain_text_when_json_unparsed,
    message_when_no_answer_blocks,
    normalize_answer_blocks,
    operator_detail_no_blocks,
    parse_llm_json_blob,
    salvage_answer_blocks_from_near_json,
)
from backend.app.llm.prompts import load_system_prompt_template
from backend.app.rag.sources import build_sources


_RESPONSE_LANGUAGE_LABELS = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "pt": "Portuguese",
    "hi": "Hindi",
}

_ENCYCLOPEDIA_HINT = {
    "en": (
        "I could not find a strong match in the Climate Academy Student Book for this question. "
        "Try browsing terms linked in the book (Climate Academy encyclopedia entries), "
        "or rephrase your question using chapter vocabulary."
    ),
    "fr": (
        "Je n'ai pas trouvé de passage pertinent dans le manuel Climate Academy. "
        "Consultez les entrées encyclopédiques liées dans le livre, ou reformulez votre question."
    ),
    "es": (
        "No encontré un pasaje relevante en el libro Climate Academy. "
        "Pruebe las entradas de la enciclopedia enlazadas en el libro, o reformule su pregunta."
    ),
    "pt": (
        "Não encontrei uma passagem relevante no manual Climate Academy. "
        "Veja as entradas da enciclopédia ligadas no livro, ou reformule a pergunta."
    ),
    "hi": (
        "Climate Academy छात्र पुस्तक में इस प्रश्न के लिए कोई मजबूत मिलान नहीं मिला। "
        "पुस्तक में जुड़े विश्वकोश प्रविष्टियों को देखें, या प्रश्न दोबारा लिखें।"
    ),
}

_CANNED_LINES = {
    "rate_limit": {
        "en": "You've hit a temporary usage limit. Wait a minute and try again.",
        "fr": "Vous avez atteint une limite d'utilisation temporaire. Attendez une minute et réessayez.",
        "es": "Has alcanzado un límite de uso temporal. Espera un minuto e inténtalo de nuevo.",
        "pt": "Atingiu um limite de uso temporário. Aguarde um minuto e tente novamente.",
        "hi": "आप अस्थायी उपयोग सीमा तक पहुँच गए हैं। एक मिनट प्रतीक्षा करें और पुनः प्रयास करें।",
    },
    "bad_key": {
        "en": (
            "This app can't reach the assistant because the API key is wrong or missing. "
            "Whoever set up the app needs to fix the key in secrets or environment."
        ),
        "fr": (
            "L'application ne peut pas joindre l'assistant : la clé API est absente ou invalide. "
            "La personne qui configure l'application doit corriger la clé dans les secrets ou "
            "l'environnement."
        ),
        "es": (
            "La aplicación no puede hablar con el asistente porque falta la clave API "
            "o no es válida. Quien configuró la app debe corregir la clave en secretos "
            "o entorno."
        ),
        "pt": (
            "A aplicação não consegue contactar o assistente porque a chave API falta ou "
            "é inválida. Quem instalou deve corrigir a chave nos segredos ou no ambiente."
        ),
        "hi": (
            "ऐप सहायक से जुड़ नहीं सकता — API कुंजी गलत या अनुपलब्ध है। सेटअप करने वाले को "
            "सिक्रेट्स या पर्यावरण में कुंजी ठीक करनी होगी।"
        ),
    },
    "generic": {
        "en": (
            "Something went wrong while getting an answer from the assistant. "
            "Please try again in a moment."
        ),
        "fr": (
            "Un problème est survenu en obtenant une réponse de l'assistant. "
            "Veuillez réessayer dans un instant."
        ),
        "es": (
            "Algo salió mal al obtener una respuesta del asistente. "
            "Inténtalo de nuevo dentro de un momento."
        ),
        "pt": (
            "Algo correu mal ao obter uma resposta do assistente. "
            "Tente novamente dentro de momentos."
        ),
        "hi": (
            "सहायक से उत्तर लेते समय कुछ गलत हुआ। कृपया कुछ क्षण बाद फिर से प्रयास करें।"
        ),
    },
}


def _normalize_response_language(code: str | None) -> str:
    c = (code or "en").strip().lower()
    return c if c in _RESPONSE_LANGUAGE_LABELS else "en"


def _language_mode_appendix(code: str) -> str:
    code = _normalize_response_language(code)
    label = _RESPONSE_LANGUAGE_LABELS.get(code, "English")
    if code == "en":
        return (
            "\n\nLANGUAGE MODE (mandatory):\n"
            "- Selected chat language: English (en).\n"
            "- Write this entire assistant reply in English only.\n"
        )
    return (
        f"\n\nLANGUAGE MODE (mandatory):\n"
        f'- Selected chat language: {label} ({code}).\n'
        f"- Write **every** answer paragraph only in {label}; do not mix English "
        "(or any other language) into the prose. Citation markers stay as ASCII digits.\n"
        "- Retrieved book excerpts remain in English underneath; summarize and quote "
        f"ideas faithfully in {label}.\n"
        "- If the user message is not in {label}, still answer entirely in {label}.\n"
    )


def _canned_line(kind: str, lang: str) -> str:
    code = _normalize_response_language(lang)
    return _CANNED_LINES.get(kind, {}).get(code) or _CANNED_LINES[kind]["en"]


def _encyclopedia_fallback_line(lang: str) -> str:
    code = _normalize_response_language(lang)
    return _ENCYCLOPEDIA_HINT.get(code) or _ENCYCLOPEDIA_HINT["en"]


def _retrieval_is_weak(chunks: list[dict], settings: AppSettings) -> bool:
    if not chunks:
        return True
    return all(c.get("distance", 0) >= settings.max_distance for c in chunks)


def ask_groq(
    groq_client,
    chunks: list[dict],
    history: list,
    user_message: str,
    settings: AppSettings,
    pdf_chunk_map: Optional[dict] = None,
    response_language: str = "en",
) -> dict:
    """
    Calls Groq and returns:
      {
        "blocks": [{"text": str, "citations": [int, ...]}, ...],
        "sources": [{source metadata}, ...],
        "operator_detail": optional str (technical diagnostics for operators),
      }
    """
    rl = _normalize_response_language(response_language)
    if _retrieval_is_weak(chunks, settings):
        return {
            "blocks": [{"text": _encyclopedia_fallback_line(rl), "citations": []}],
            "sources": [],
            "operator_detail": "retrieve=weak_or_empty;encyclopedia_fallback=1",
        }

    sources = build_sources(chunks, settings, pdf_chunk_map=pdf_chunk_map)
    context_parts = []
    for s in sources:
        passage = (
            f"[SOURCE_ID: {s['source_id']}] "
            f"[CHUNK_ID: {s['chunk_id']}] "
            f"[ANCHOR_ID: {s['anchor_id']}] "
            f"[§ {s['section_number']} — {s['section_title']}]\n"
            f"{s['document']}"
        )
        context_parts.append(passage)
    context = "\n\n---\n\n".join(context_parts)

    template = load_system_prompt_template() #load_system_prompt_template(settings.base_dir)
    system = template.format(context=context) + _language_mode_appendix(rl)
    messages = [{"role": "system", "content": system}]
    for t in history[-settings.llm_history_turns :]:
        if t["role"] in ("user", "assistant"):
            content = t.get("content") or ""
            if t["role"] == "assistant" and t.get("blocks"):
                content = " ".join(b.get("text", "") for b in t.get("blocks", []))
            messages.append({"role": t["role"], "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        resp = groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )
        choice = resp.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        raw = (choice.message.content or "").strip()
        parsed = parse_llm_json_blob(raw)
        valid_source_ids = {s["source_id"] for s in sources}
        blocks = normalize_answer_blocks(parsed, valid_source_ids)

        operator_detail = None
        if not blocks:
            plain = fallback_plain_text_when_json_unparsed(raw)
            if plain:
                blocks = [{
                    "text": escape_model_text_for_point_card(plain),
                    "citations": [],
                }]
                operator_detail = operator_detail_no_blocks(
                    raw,
                    parsed,
                    finish_reason,
                    source_count=len(sources),
                    extra_lines=(
                        "display_mode=recovered_plain_prose_no_json",
                    ),
                )
            else:
                salvaged = salvage_answer_blocks_from_near_json(raw)
                if salvaged:
                    blocks = normalize_answer_blocks(
                        {"answer_blocks": salvaged},
                        valid_source_ids,
                    )
                if blocks:
                    operator_detail = operator_detail_no_blocks(
                        raw,
                        parsed,
                        finish_reason,
                        source_count=len(sources),
                        extra_lines=("display_mode=salvaged_near_json_text_scan",),
                    )
                else:
                    fallback_citations = [s["source_id"] for s in sources[:3]]
                    blocks = [{
                        "text": message_when_no_answer_blocks(raw, parsed, finish_reason),
                        "citations": fallback_citations,
                    }]
                    operator_detail = operator_detail_no_blocks(
                        raw, parsed, finish_reason, source_count=len(sources),
                    )

        return {"blocks": blocks, "sources": sources, "operator_detail": operator_detail}
    except Exception as e:
        err = str(e)
        op_detail = f"exception_type={type(e).__name__}\nexception_message={err}"
        if "rate_limit" in err.lower():
            return {
                "blocks": [{"text": _canned_line("rate_limit", rl), "citations": []}],
                "sources": sources,
                "operator_detail": op_detail,
            }
        if "invalid_api_key" in err.lower():
            return {
                "blocks": [{"text": _canned_line("bad_key", rl), "citations": []}],
                "sources": sources,
                "operator_detail": op_detail,
            }
        return {
            "blocks": [{"text": _canned_line("generic", rl), "citations": []}],
            "sources": sources,
            "operator_detail": op_detail,
        }
