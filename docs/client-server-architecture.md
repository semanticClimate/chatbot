# Client and server architecture

Source diagrams live as Mermaid in `docs/architecture/*.mmd` (kept in sync with the blocks below). **PNG** and **SVG** exports for GitHub viewers and embedding are beside them: regenerate with `bash docs/architecture/render-diagrams.sh` (requires Node and downloads `@mermaid-js/mermaid-cli`, which renders via headless Chromium). Graphviz **`dot`** reads the DOT language, not Mermaid, so those exports are produced with the Mermaid CLI rather than Graphviz directly.

This diagram shows the end-to-end architecture across the browser client, web UI, API server, retrieval stack, and external LLM provider.

| Static export | PNG | SVG |
| --- | --- | --- |
| Overview | [`architecture-overview.png`](architecture/architecture-overview.png) | [`architecture-overview.svg`](architecture/architecture-overview.svg) |
| User client detail | [`architecture-user-client.png`](architecture/architecture-user-client.png) | [`architecture-user-client.svg`](architecture/architecture-user-client.svg) |

![Architecture overview (PNG)](architecture/architecture-overview.png)

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

  WebClient -->|"HTTP: /ask, /health, /ready"| FastAPI
  RAG -->|"HTTPS chat completions"| Groq
```

## User client (browser) detail

This expands the static `web_client/` layer: UI surfaces, modules, persisted API base URL, optional tunnel hint file, and HTTP endpoints used from the configured API base.

![User client (browser) detail (PNG)](architecture/architecture-user-client.png)

```mermaid
flowchart TB
  subgraph UserClient["User client — browser"]
    subgraph Runtime["Runtime"]
      Origin["Page origin — where index.html is served<br/>(e.g. http://127.0.0.1:8081 or https://….trycloudflare.com)"]
      Modules["ES modules from same origin<br/>main.js wires UI → api/state/render/examples"]
      Storage["localStorage key: climate_web_client_api_base<br/>(saved API base URL)"]
      Hint["Optional fetch: tunnel-api-base.txt<br/>same-origin, cache-busted on tunnel hosts"]
      Origin --> Modules
      Modules --> Storage
      Modules -.-> Hint
    end

    subgraph UI["Surfaces"]
      Conn["Connection: API base URL input<br/>Check health · Clear chat"]
      Examples["Example question chips<br/>(examples.js)"]
      Thread["Conversation thread<br/>(render.js + state.js)"]
      Composer["Composer: POST question on submit"]
      Book["Book panel: iframe → API base plus /book/document<br/>postMessage jumps for citations → iframe origin"]
    end

    Modules --> Conn
    Modules --> Examples
    Modules --> Thread
    Modules --> Composer
    Modules --> Book
  end

  subgraph API["Configured backend — FastAPI (any reachable base URL)"]
    H["GET /health"]
    R["GET /ready"]
    A["POST /ask<br/>JSON: question, conversation[, top_k]"]
    D["GET /book/document<br/>(iframe)"]
    C["POST /conversation/export<br/>CSV download"]
    L["GET /logs/export<br/>CSV download"]
  end

  Conn -->|"fetch"| H
  Conn -->|"fetch"| R
  Composer -->|"fetch"| A
  Book -->|"iframe + optional postMessage"| D
  Thread -->|"export buttons"| C
  Thread -->|"export buttons"| L

  Hint -.->|"if present text is https URL, may prefill"| Conn
  Storage -.->|"load/save"| Conn

  style UserClient fill:#f9f9f9
  style API fill:#eef6ff
```
