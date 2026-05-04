"""Sidebar chat list and actions."""

from __future__ import annotations

import streamlit as st

from config_loader import AppSettings
from ui.session import chat_preview, create_chat, welcome_message


def clear_jump_targets() -> None:
    st.session_state.jump_anchor_id = None
    st.session_state.jump_section = None
    st.session_state.jump_heading_id = ""
    st.session_state.jump_type = "section"
    st.session_state.jump_pdf_query = ""
    st.session_state.jump_pdf_page = 1


def render_sidebar(settings: AppSettings) -> None:
    sb = settings.sidebar
    with st.sidebar:
        st.markdown(f"### {sb.chats_heading}")
        if st.button(sb.new_chat, use_container_width=True):
            create_chat(settings)
            st.rerun()

        for chat_id in st.session_state.chat_order:
            is_active = chat_id == st.session_state.current_chat_id
            prefix = "● " if is_active else ""
            label = prefix + chat_preview(chat_id)
            if st.button(label, key=f"chat_pick_{chat_id}", use_container_width=True):
                st.session_state.current_chat_id = chat_id
                st.rerun()

        st.divider()
        if st.button(sb.clear_chat, use_container_width=True):
            current = st.session_state.chats[st.session_state.current_chat_id]
            current["messages"] = [{"role": "assistant", "content": welcome_message(settings)}]
            clear_jump_targets()
            st.rerun()

        if st.button(sb.delete_chat, use_container_width=True):
            current_id = st.session_state.current_chat_id
            if len(st.session_state.chat_order) > 1:
                st.session_state.chat_order = [cid for cid in st.session_state.chat_order if cid != current_id]
                st.session_state.chats.pop(current_id, None)
                st.session_state.current_chat_id = st.session_state.chat_order[0]
            else:
                st.session_state.chats[current_id]["messages"] = [
                    {"role": "assistant", "content": welcome_message(settings)}
                ]
            clear_jump_targets()
            st.rerun()
