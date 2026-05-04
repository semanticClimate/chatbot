"""Load `config/app.defaults.toml` and expose resolved paths."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class SidebarLabels:
    chats_heading: str
    new_chat: str
    clear_chat: str
    delete_chat: str


@dataclass(frozen=True)
class PanelLabels:
    chat_title: str
    chat_subtitle: str
    book_title: str
    book_subtitle: str
    section_label_conversation: str
    reset_book: str


@dataclass(frozen=True)
class ChatHistoryUi:
    min_height: int
    max_height: int
    base: int
    per_message: int


@dataclass(frozen=True)
class MessageCopy:
    welcome: str
    disclaimer_template: str
    chat_input_placeholder: str


@dataclass(frozen=True)
class AppSettings:
    root_dir: Path
    base_dir: Path
    html_path: Path
    pdf_path: Path
    chroma_dir: str
    collection_name: str
    top_k: int
    max_distance: float
    indexing_batch_size: int
    embed_model: str
    groq_model: str
    llm_max_tokens: int
    llm_temperature: float
    llm_history_turns: int
    pdf_max_query_words: int
    pdf_keyword_max_words: int
    page_title: str
    page_icon: str
    layout: str
    initial_sidebar_state: str
    book_viewer_height: int
    spinner_text: str
    chat_history: ChatHistoryUi
    sidebar: SidebarLabels
    panels: PanelLabels
    messages: MessageCopy


def _resolve_path(root: Path, relative: str) -> Path:
    return (root / relative).resolve()


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    base_dir = Path(__file__).resolve().parent
    root_dir = base_dir.parent
    cfg_path = base_dir / "config" / "app.defaults.toml"
    raw = cfg_path.read_bytes()
    t = tomllib.loads(raw.decode("utf-8"))

    paths = t["paths"]
    chroma = t["chroma"]
    retrieval = t["retrieval"]
    indexing = t["indexing"]
    embed = t["embed"]
    llm = t["llm"]
    pdf = t["pdf"]
    ui = t["ui"]
    u_side = ui["sidebar"]
    u_pan = ui["panels"]
    u_msg = ui["messages"]
    u_hist = ui["chat_history"]

    return AppSettings(
        root_dir=root_dir,
        base_dir=base_dir,
        html_path=_resolve_path(root_dir, paths["html"]),
        pdf_path=_resolve_path(root_dir, paths["pdf"]),
        chroma_dir=str(_resolve_path(root_dir, paths["chroma_dir"])),
        collection_name=chroma["collection_name"],
        top_k=int(retrieval["top_k"]),
        max_distance=float(retrieval["max_distance"]),
        indexing_batch_size=int(indexing["batch_size"]),
        embed_model=embed["model_label"],
        groq_model=llm["model"],
        llm_max_tokens=int(llm["max_tokens"]),
        llm_temperature=float(llm["temperature"]),
        llm_history_turns=int(llm["history_turns"]),
        pdf_max_query_words=int(pdf["max_query_words"]),
        pdf_keyword_max_words=int(pdf["keyword_max_words"]),
        page_title=ui["page_title"],
        page_icon=ui["page_icon"],
        layout=ui["layout"],
        initial_sidebar_state=ui["initial_sidebar_state"],
        book_viewer_height=int(ui["book_viewer_height"]),
        spinner_text=ui["spinner_text"],
        chat_history=ChatHistoryUi(
            min_height=int(u_hist["min_height"]),
            max_height=int(u_hist["max_height"]),
            base=int(u_hist["base"]),
            per_message=int(u_hist["per_message"]),
        ),
        sidebar=SidebarLabels(
            chats_heading=u_side["chats_heading"],
            new_chat=u_side["new_chat"],
            clear_chat=u_side["clear_chat"],
            delete_chat=u_side["delete_chat"],
        ),
        panels=PanelLabels(
            chat_title=u_pan["chat_title"],
            chat_subtitle=u_pan["chat_subtitle"],
            book_title=u_pan["book_title"],
            book_subtitle=u_pan["book_subtitle"],
            section_label_conversation=u_pan["section_label_conversation"],
            reset_book=u_pan["reset_book"],
        ),
        messages=MessageCopy(
            welcome=u_msg["welcome"],
            disclaimer_template=u_msg["disclaimer_template"],
            chat_input_placeholder=u_msg["chat_input_placeholder"],
        ),
    )
