# Client and server architecture

This diagram shows the end-to-end architecture across the browser client, web UI, API server, retrieval stack, and external LLM provider.

```mermaid
flowchart LR
  subgraph UserSide["Client Side"]
    Browser[Browser]
    WebClient[Static Web Client<br/>web_client]
    Browser --> WebClient
  end

  subgraph AppHost["Server Side"]
    FastAPI[FastAPI App<br/>fastapi_app.main]
    RAG[RAG Pipeline]
    Embed[ONNX Embeddings<br/>all-MiniLM-L6-v2]
    Chroma[(ChromaDB<br/>chroma_db/)]
    Input[(input/full_student_book.html<br/>optional PDF)]

    FastAPI --> RAG
    RAG --> Embed
    RAG --> Chroma
    RAG --> Input
  end

  Groq[Groq API<br/>llama-3.3-70b-versatile]

  WebClient -->|HTTP requests (/ask, /health, /ready)| FastAPI
  RAG -->|HTTPS chat completions| Groq
```
