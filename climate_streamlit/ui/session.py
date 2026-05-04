"""Chat session state and identifiers."""

from __future__ import annotations

from uuid import uuid4

import streamlit as st

from config_loader import AppSettings


def welcome_message(settings: AppSettings) -> str:
    return settings.messages.welcome


def new_chat_name() -> str:
    return f"New Chat {len(st.session_state.chat_order) + 1}"


def create_chat(settings: AppSettings) -> None:
    chat_id = f"chat_{uuid4().hex[:10]}"
    st.session_state.chats[chat_id] = {
        "name": new_chat_name(),
        "messages": [{"role": "assistant", "content": welcome_message(settings)}],
    }
    st.session_state.chat_order.insert(0, chat_id)
    st.session_state.current_chat_id = chat_id


def chat_preview(chat_id: str) -> str:
    chat = st.session_state.chats.get(chat_id, {})
    for msg in chat.get("messages", []):
        if msg.get("role") == "user":
            text = (msg.get("content") or "").strip()
            if text:
                return (text[:34] + "...") if len(text) > 34 else text
    return chat.get("name", "New Chat")


def init_session(settings: AppSettings) -> None:
    defaults = {
        "chats":             {},
        "chat_order":        [],
        "current_chat_id":   None,
        "jump_anchor_id":    None,
        "jump_section":      None,
        "jump_heading_id":   "",
        "jump_type":         "section",
        "jump_pdf_query":    "",
        "jump_pdf_page":     1,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if not st.session_state.chat_order or not st.session_state.current_chat_id:
        create_chat(settings)
