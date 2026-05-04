"""Main chat column: history, input, citation chips."""

from __future__ import annotations

import streamlit as st

from config_loader import AppSettings
from llm.ask import ask_groq
from pdf.index import map_chunks_to_pdf
from rag.retrieve import retrieve
from ui.book_viewer import render_book_viewer


def render_chat_column(
    settings: AppSettings,
    collection,
    embedder,
    groq_client,
    pdf_path_str: str,
    pdf_exists: bool,
) -> None:
    panels = settings.panels
    msgs = settings.messages
    hist = settings.chat_history

    current_chat = st.session_state.chats[st.session_state.current_chat_id]
    messages = current_chat["messages"]

    st.markdown(
        f"""
    <div class="panel-header">
        <p class="panel-title">{panels.chat_title}</p>
        <p class="panel-subtitle">{panels.chat_subtitle}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<p class="section-label">{panels.section_label_conversation}</p>',
        unsafe_allow_html=True,
    )

    message_count = len(messages)
    chat_history_height = max(
        hist.min_height,
        min(hist.max_height, hist.base + (message_count * hist.per_message)),
    )
    history_box = st.container(height=chat_history_height, border=False)
    with history_box:
        for msg_idx, msg in enumerate(messages):
            if msg["role"] == "assistant":
                blocks = msg.get("blocks") or []
                sources = msg.get("sources") or []
                source_by_id = {s.get("source_id"): s for s in sources}

                if blocks:
                    for bi, block in enumerate(blocks):
                        text = block.get("text", "")
                        citations = block.get("citations", [])

                        st.markdown(
                            f'<div class="point-card"><div class="point-body">{text}</div></div>',
                            unsafe_allow_html=True,
                        )

                        if citations:
                            chip_cols = st.columns(len(citations))
                            for ci, source_id in enumerate(citations):
                                source = source_by_id.get(source_id, {})
                                sec_num = source.get("section_number", "")
                                sec_title = source.get("section_title", "")
                                source_line = f"§ {sec_num}" if sec_num else "Source"
                                if sec_title:
                                    source_line += f" — {sec_title}"

                                key = f"cite_{st.session_state.current_chat_id}_{msg_idx}_{bi}_{source_id}"
                                if chip_cols[ci].button(
                                    str(source_id),
                                    key=key,
                                    help=f"Jump to source {source_id}\n{source_line}",
                                    use_container_width=True,
                                ):
                                    st.session_state.jump_anchor_id = source.get("anchor_id", "")
                                    st.session_state.jump_section = source.get("section_number", "")
                                    st.session_state.jump_heading_id = source.get("heading_id", "")
                                    st.session_state.jump_type = "para" if source.get("anchor_id") else "section"
                                    st.session_state.jump_pdf_query = source.get("pdf_query", "")
                                    st.session_state.jump_pdf_page = source.get("pdf_page", 1)
                                    st.rerun()
                    od = msg.get("operator_detail")
                    if od:
                        with st.expander("Operator diagnostics (technical)", expanded=False):
                            st.text(od)
                else:
                    content = msg.get("content", "")
                    st.markdown(
                        f'<div class="msg-row-bot">'
                        f'<div class="avatar">CA</div>'
                        f'<div class="bubble-bot">{content.replace(chr(10), "<br>")}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                content = msg.get("content", "")
                st.markdown(
                    f'<div class="msg-row-user">'
                    f'<div class="bubble-user">{content.replace(chr(10), "<br>")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    user_input = st.chat_input(msgs.chat_input_placeholder)
    if user_input:
        messages.append({"role": "user", "content": user_input})

        if current_chat["name"].startswith("New Chat"):
            current_chat["name"] = (user_input[:28] + "...") if len(user_input) > 28 else user_input

        with st.spinner(settings.spinner_text):
            chunks = retrieve(user_input, collection, embedder, settings)
            pdf_chunk_map = (
                map_chunks_to_pdf(chunks, pdf_path_str, settings.pdf_keyword_max_words)
                if pdf_exists
                else {}
            )
            answer = ask_groq(
                groq_client,
                chunks,
                messages[:-1],
                user_input,
                settings,
                pdf_chunk_map=pdf_chunk_map,
            )

        blocks = answer.get("blocks", [])
        sources = answer.get("sources", [])
        first_source = None
        if blocks and blocks[0].get("citations"):
            first_source_id = blocks[0]["citations"][0]
            first_source = next((s for s in sources if s.get("source_id") == first_source_id), None)

        if first_source:
            st.session_state.jump_anchor_id = first_source.get("anchor_id", "")
            st.session_state.jump_section = first_source.get("section_number", "")
            st.session_state.jump_heading_id = first_source.get("heading_id", "")
            st.session_state.jump_type = "para" if first_source.get("anchor_id") else "section"
            st.session_state.jump_pdf_query = first_source.get("pdf_query", "")
            st.session_state.jump_pdf_page = first_source.get("pdf_page", 1)

        messages.append({
            "role": "assistant",
            "content": None,
            "blocks": blocks,
            "sources": sources,
            "operator_detail": answer.get("operator_detail"),
        })
        st.rerun()

    st.divider()
    if st.button(panels.reset_book, use_container_width=True):
        st.session_state.jump_anchor_id = None
        st.session_state.jump_section = None
        st.session_state.jump_heading_id = ""
        st.session_state.jump_type = "section"
        st.session_state.jump_pdf_query = ""
        st.session_state.jump_pdf_page = 1
        st.rerun()

    disclaimer = msgs.disclaimer_template.format(
        embed_model=settings.embed_model,
        llm_model=settings.groq_model,
    )
    st.markdown(
        f'<p class="disclaimer">{disclaimer}</p>',
        unsafe_allow_html=True,
    )


def render_book_panel(settings: AppSettings, book_html: str) -> None:
    panels = settings.panels
    st.markdown(
        f"""
    <div class="panel-header">
        <p class="panel-title">{panels.book_title}</p>
        <p class="panel-subtitle">{panels.book_subtitle}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    render_book_viewer(
        book_html,
        settings,
        target_anchor_id=st.session_state.jump_anchor_id,
        target_section=st.session_state.jump_section,
        heading_id=st.session_state.jump_heading_id,
        jump_type=st.session_state.jump_type,
    )
