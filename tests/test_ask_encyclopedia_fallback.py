from backend.app.config_loader import get_settings
from backend.app.llm.ask import ask_groq


def test_weak_retrieval_returns_encyclopedia_hint():
    settings = get_settings()
    out = ask_groq(
        groq_client=None,
        chunks=[{"document": "x", "distance": settings.max_distance + 0.5, "chunk_id": "p-1-0"}],
        history=[],
        user_message="test",
        settings=settings,
    )
    assert "encyclopedia" in out["blocks"][0]["text"].lower()
    assert out["sources"] == []
    assert "encyclopedia_fallback" in (out.get("operator_detail") or "")
