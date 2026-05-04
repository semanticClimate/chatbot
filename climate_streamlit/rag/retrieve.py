"""Chroma similarity retrieval."""

from __future__ import annotations

from config_loader import AppSettings


def retrieve(query: str, collection, embedder, settings: AppSettings) -> list[dict]:
    """
    Returns a list of dicts, each containing:
      document, section_number, section_title, heading_id, chunk_id, anchor_id
    Ordered by relevance.
    """
    query_vector = embedder([query])[0]
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=settings.top_k,
        include=["documents", "distances", "metadatas"],
    )
    docs = results["documents"][0]
    dists = results["distances"][0]
    metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)

    triples = list(zip(docs, dists, metas))
    filtered = [(d, dist, m) for d, dist, m in triples if dist < settings.max_distance]
    use = filtered if filtered else triples

    chunks = []
    for doc, _dist, meta in use:
        chunks.append({
            "document":       doc,
            "section_number": meta.get("section_number", ""),
            "section_title":  meta.get("section_title", ""),
            "heading_id":     meta.get("heading_id", ""),
            "chunk_id":       meta.get("chunk_id", ""),
            "anchor_id":      meta.get("anchor_id", ""),
        })
    return chunks
