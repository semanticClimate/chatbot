# Client-User Architecture

This is called a **Client-User Architecture** because the browser UI behaves as a client that asks the backend for responses.

* The previous Streamlit interface used a **Monolithic Architecture**, where a single section handled both the frontend and backend, which becomes difficult to maintain.
* The new architecture is upgraded to a **Decoupled Architecture**, where there are two separate sections:

  * Web UI (Frontend)
  * FastAPI Backend

---

# The User-Client Browser (Frontend)

## Page Origin — Where `index.html` Is Served

Examples:

```text
http://127.0.0.1:8081
https://xxxx.trycloudflare.com
```

The static frontend files run here:

* HTML
* CSS
* JavaScript

The webpage can be served from both:

* `http://127.0.0.1:8081` → Local server
* `https://xxxx.trycloudflare.com` → Global/public tunnel server

---

# ES Modules from Same Origin

```text
main.js wires UI → api/state/render/examples
```

ES Modules (ECMAScript Modules) are the modern JavaScript module system used to split code into multiple files and allow files to communicate cleanly.

Instead of writing everything in one file like:

```text
main.js
```

we split responsibilities into:

```text
api.js
render.js
state.js
examples.js
utils.js
```

Each file becomes a separate module.

In the architecture:

```text
main.js wires UI → api/state/render/examples
```

The chatbot frontend is broken into specialized modules.

This makes the frontend:

* scalable
* maintainable
* reusable
* professional

---

# Frontend File Structure

```text
frontend/
│
├── index.html
├── main.js
├── api.js
├── state.js
├── render.js
├── examples.js
├── citations.js
└── styles.css
```

---

# 1. `main.js` — APPLICATION CONTROLLER

This is the startup orchestrator.

Think of it as the:

```text
frontend manager
```

Responsibilities:

* initialize app
* attach button listeners
* connect modules together
* app startup handling

Example:

```javascript
import { sendQuestion } from "./api.js";
import { renderMessage } from "./render.js";
import { state } from "./state.js";
```

---

# 2. `api.js` — NETWORK LAYER

This module handles backend communication.

Very important separation.

## Why Separate Network Logic?

Without separation:

```javascript
button.onclick = async () => {
   fetch(...)
}
```

inside many files becomes messy.

Instead:

```text
api.js = all backend communication
```

This creates clean architecture.

## Likely Functions in `api.js`

```javascript
export async function checkHealth()

export async function askQuestion()

export async function getDocument()

export async function exportConversation()
```

This file centralizes:

* URLs
* headers
* fetch logic
* error handling

---

# 3. `state.js` — CLIENT MEMORY

Very important concept.

Frontend needs memory/state.

## What Is State?

State means:

```text
current application data
```

Examples:

* conversation history
* current API URL
* loading state
* selected citations

Example `state.js`:

```javascript
export const state = {
    messages: [],
    apiBase: "",
    loading: false
};
```

This becomes centralized frontend memory.

---

# 4. `render.js` — UI RENDERING ENGINE

This file handles:

* creating HTML
* updating DOM
* displaying messages

## Why Separate Rendering?

UI logic becomes messy quickly.

Instead:

```text
render.js = ONLY UI rendering
```

---

# 5. `examples.js`

Stores quick prompts.

Example:

```javascript
export const examples = [
    "What causes global warming?",
    "Explain greenhouse gases"
];
```

Frontend uses this to render chips/buttons.

---

# Optional Fetch: `tunnel-api-base.txt`

```text
same-origin, cache-busted on tunnel hosts
```

## THE CORE PROBLEM

Remember:

Frontend and backend are separated.

Frontend may be hosted somewhere like:

```text
https://frontend.trycloudflare.com
```

Backend may be running at:

```text
https://backend.trycloudflare.com
```

But:

* Cloudflare tunnel URLs change frequently
* ngrok URLs change
* localhost ports change

So frontend doesn’t know:

```text
Which backend URL should I connect to?
```

---

# HOW IT WORKS

The frontend tries to fetch:

```text
tunnel-api-base.txt
```

from the SAME ORIGIN.

Example:

If frontend loaded from:

```text
https://frontend.trycloudflare.com
```

then frontend requests:

```text
https://frontend.trycloudflare.com/tunnel-api-base.txt
```

---

# The File Contains a Very Simple Text File

Example:

```text
https://backend.trycloudflare.com
```

That’s it.

Just the backend base URL.

---

# `localStorage` Key: `climate_web_client_api_base`

```text
(saved API base URL)
```

`localStorage` is a built-in browser storage system that allows a website to save data directly inside the user’s browser.

It is part of:

```text
Web Storage API
```

Every modern browser supports it:

* Chrome
* Edge
* Firefox
* Safari

---

# HOW IT WORKS

## STEP 1 — User Enters Backend URL

Inside connection panel:

```text
API Base URL:
https://abc.trycloudflare.com
```

## STEP 2 — Frontend Saves It

Using:

```javascript
localStorage.setItem(
   "climate_web_client_api_base",
   "https://abc.trycloudflare.com"
)
```

## STEP 3 — Browser Stores It Permanently

Now even after:

* refresh
* reopening browser

The value still exists.

## STEP 4 — On App Startup

Frontend reads it back:

```javascript
const apiBase =
   localStorage.getItem(
      "climate_web_client_api_base"
   );
```

Now frontend auto-connects.

---

# VISUAL FLOW

```text
User enters backend URL
        ↓
main.js saves URL
        ↓
localStorage
(browser memory)
        ↓
Page refreshed
        ↓
main.js loads saved URL
        ↓
Frontend reconnects automatically
```

---

# Connection: API Base URL Input

```text
Check health · Clear chat
```

This component is the:

```text
Frontend Connection Manager
```

It controls:

* backend connectivity
* API configuration
* health verification
* conversation reset
* runtime environment switching

It is basically the “control panel” between frontend and backend.

---

# 1. API BASE URL INPUT

This is probably a textbox like:

```text
[ https://abc.trycloudflare.com ]
```

This is where the user specifies:

```text
Backend FastAPI server location
```

Frontend is static JavaScript.

It does NOT automatically know:

* backend IP
* backend domain
* backend port

So user or auto-discovery provides:

```text
API Base URL
```

---

# WHAT IS AN API BASE URL?

Suppose backend endpoints are:

```text
https://backend.com/health
https://backend.com/ask
https://backend.com/ready
```

The common root is:

```text
https://backend.com
```

That is:

```text
API Base URL
```

Frontend dynamically builds requests using it.

---

# Health Check

```javascript
fetch(apiBase + "/health")
```

becomes:

```text
https://backend.com/health
```

---

# Ask Question

```javascript
fetch(apiBase + "/ask")
```

becomes:

```text
https://backend.com/ask
```

---

# Book Viewer

```javascript
iframe.src =
  apiBase + "/book/document"
```

becomes:

```text
https://backend.com/book/document
```

Everything depends on this base URL.

---

# Clear Chat

This is a state-management operation.

The complete chat is deleted from the UI and frontend conversation state.

Example:

```javascript
state.messages = []
```

---

# Example Question Chips (`examples.js`)

Small clickable sample questions shown in the UI.

Like these:

```text
[ What is climate change? ]
[ Explain greenhouse gases ]
[ Effects of global warming ]
```

These are called:

```text
Chips
```

because they look like small rounded buttons.

---

# Why They Are Useful

They help users:

* quickly test chatbot
* understand what to ask
* avoid typing
* improve user experience

Especially useful for:

* demos
* first-time users
* presentations

---

# `examples.js`

```javascript
export const examples = [
   "What is climate change?",
   "Explain greenhouse gases",
   "How does deforestation affect climate?"
];
```

---

# Composer: `POST` Question on Submit

The chat input box sends the user's question to the backend when the user presses submit.

That’s all at a high level.

---

# WHAT IS "COMPOSER"?

Composer means:

```text
The message typing area
```

Like ChatGPT’s input box.

Example:

```text
--------------------------------
| Ask something...             |
--------------------------------
            [ Send ]
```

That whole section is called:

```text
Composer
```

because user composes/writes a message there.

---

# When User Presses

* Enter
* OR Send button

the frontend sends the question to backend using:

```http
POST /ask
```

---

# HTTP Methods

HTTP has methods like:

* GET
* POST
* PUT
* DELETE

---

# GET

Used to:

```text
fetch data
```

Example:

```http
GET /health
```

---

# POST

Used to:

```text
send data
```

Since user question is data,
frontend uses:

```http
POST /ask
```

---

# WHAT DATA IS SENT?

Frontend likely sends JSON.

Example:

```json
{
  "question": "What is climate change?",
  "conversation": [
    {
      "role": "user",
      "content": "Hi"
    },
    {
      "role": "assistant",
      "content": "Hello!"
    }
  ],
  "top_k": 5
}
```

---

# `question`

Current user question.

---

# `conversation`

Previous chat history.

Helps AI remember context.

---

# `top_k`

How many document chunks to retrieve from vector DB.

Example:

```text
Retrieve top 5 most relevant chunks
```

---

# Book Panel: `iframe → API base + /book/document`

```text
postMessage jumps for citations → iframe origin
```

An iframe is used when a webpage is inserted inside another webpage.

---

# The Chatbot Has a Built-In Document/Book Viewer

Connected to the AI answers.

So when AI gives citations like:

```text
[Page 12]
[Section 3]
```

you can click them and the book automatically jumps to that location.

Very similar to:

* NotebookLM
* Perplexity citations
* research assistants

---

# Book Viewer iframe

```text
https://abc.trycloudflare.com/book/document
```

This is where the PDF book is displayed inside the chatbot UI.

It’s an iframe.

Which means:

```text
A webpage showing another webpage
```

Example:

```html
<iframe
  src="https://backend.com/book/document"
  width="100%"
  height="600px"
></iframe>
```

---

# Browser Security

Browsers protect cross-window communication.

Without origin checks:

* malicious websites could spy
* unsafe message injection possible

Example:

## Parent Page

```text
https://frontend.com
```

## Iframe

```text
https://backend.com/book/document
```

Messages must specify correct target origin.

---

# LIKELY IMPLEMENTATION

## Parent Page

```javascript
iframe.contentWindow.postMessage(
   {
      type: "jump",
      citation: 12
   },
   "https://backend.com"
);
```

## Iframe Side

```javascript
window.addEventListener(
   "message",
   (event) => {

      if(event.data.type === "jump") {

          goToCitation(
             event.data.citation
          );
      }
   }
);
```

---

# Conversation Thread (`render.js + state.js`)

The system that stores and displays the chat conversation.

This is basically the:

```text
Chat History System
```

like:

```text
User: Hi
AI: Hello
User: Explain climate change
AI: ...
```

---

# WHY IT SAYS

```text
(render.js + state.js)
```

Because TWO modules work together:

## 1. `state.js`

Stores conversation data in memory.

## 2. `render.js`

Displays conversation on screen.

---

# PART 1 — `state.js`

This is the chatbot’s temporary memory.

## WHAT DOES IT STORE?

Usually:

```javascript
state.messages = [
   {
      role: "user",
      content: "What is climate change?"
   },
   {
      role: "assistant",
      content: "Climate change is..."
   }
];
```

This is the conversation history.

---

# WHY STORE IT?

Because AI needs context.

Example:

## First Question

```text
What is climate change?
```

## Second Question

```text
What causes it?
```

AI must know:

```text
"it" = climate change
```

So frontend stores previous messages.

---

# THIS IS CALLED STATE

State means:

```text
current app data
```

For chatbot:

* messages
* loading state
* current conversation

---

# PART 2 — `render.js`

This module displays messages on screen.

## WHAT DOES IT DO?

Takes message data from `state.js` and creates UI.

Example:

```javascript
renderMessage(
   "user",
   "What is climate change?"
);
```

Then the message bubble appears.

---

---

# FastAPI Section — The Backend

---

# `GET /health`

One of the MOST important parts of modern backend systems.

It is called:

```text
Health Check Endpoint
```

Its job is simply:

```text
Tell me if the backend server is alive.
```

---

# EXAMPLE

Suppose backend URL is:

```text
https://backend.com
```

Frontend sends:

```http
GET https://backend.com/health
```

---

# BACKEND RECEIVES REQUEST

FastAPI has endpoint like:

```python
@app.get("/health")
async def health():
    return {
        "status": "ok"
    }
```

---

# BACKEND RESPONDS

```json
{
   "status": "ok"
}
```

---

# FRONTEND RECEIVES RESPONSE

Frontend now knows:

```text
Backend server is alive.
```

So UI may show:

```text
🟢 Connected
```

---

# `GET /ready`

AI backends are HEAVY.

When backend starts:

* server may start quickly
* BUT models still loading
* vector DB initializing
* embeddings downloading

So backend may be:

```text
ALIVE
but
NOT READY
```

---

# COMPLETE STARTUP PROCESS

## STEP 1 — Server Starts

```text
FastAPI process alive
```

So:

```text
/health → OK
```

---

## STEP 2 — AI Components Load

Backend now loads:

* embedding model
* vector DB
* documents
* LLM clients

This may take:

* seconds
* minutes

---

## STEP 3 — Everything Initialized

Now:

```text
/ready → true
```

---

# WHY THIS IS IMPORTANT

Without `/ready`:

Frontend may send question too early.

Then:

* vector DB missing
* embeddings unavailable
* crashes happen

`/ready` prevents that.

---

# `/ready` Checks For

---

# 1. EMBEDDING MODEL LOADED

Example:

```python
embedder != None
```

## WHAT IS AN EMBEDDING MODEL?

This is the AI model that converts text into numbers/vectors.

---

# SIMPLE EXAMPLE

Suppose user asks:

```text
What causes global warming?
```

The embedding model converts it into something like:

```text
[0.23, -0.91, 0.44, ...]
```

called:

```text
Vector Embedding
```

Vectors help AI understand:

* similarity
* meaning
* semantic relationships

---

# 2. CHROMADB CONNECTED

Example:

```python
collection exists
```

## WHAT IS CHROMADB?

ChromaDB is the:

```text
Vector Database
```

It stores document embeddings.

---

# SIMPLE IDEA

Suppose climate book has:

```text
1000 paragraphs
```

Each paragraph converted into vector embeddings.

Stored in ChromaDB.

---

# 3. KNOWLEDGE BASE INDEXED

Example:

```python
documents loaded
```

## WHAT IS KNOWLEDGE BASE?

This means:

* climate PDFs
* books
* processed chunks

basically:

```text
All source documents
```

---

# Suppose PDF Has

```text
500 pages
```

Backend performs:

## STEP 1 — Extract Text

```text
PDF → text
```

## STEP 2 — Split into Chunks

Example:

```text
Chunk 1
Chunk 2
Chunk 3
...
```

## STEP 3 — Create Embeddings

Each chunk converted into vector.

## STEP 4 — Store in ChromaDB

Now searchable.

This whole process is called:

```text
Indexing
```

---

# 4. GROQ CLIENT INITIALIZED

Example:

```python
groq_client != None
```

## WHAT IS GROQ CLIENT?

This is the connection to the actual LLM.

Like:

* Llama
* Mixtral
* Gemma

running through Groq API.

---

# WHAT DOES IT DO?

After retrieval:

Backend builds prompt:

```text
Context:
...

Question:
...
```

Then sends it to Groq.

---

# FLOW

```text
Retrieved chunks
      ↓
Prompt construction
      ↓
Groq LLM
      ↓
Generated answer
```

---

# STEP 1 — User Asks Question

```text
What causes global warming?
```

## STEP 2 — Embedding Model Converts Question

```text
Text → Vector
```

## STEP 3 — ChromaDB Searches Vectors

```text
Find relevant climate chunks
```

## STEP 4 — Knowledge Base Provides Chunks

```text
Relevant paragraphs retrieved
```

## STEP 5 — Groq LLM Generates Answer

```text
Final AI response
```

---

# `POST /ask`

```text
JSON: question, conversation[, top_k]
```

The main AI brain endpoint.

This is where:

* user question arrives
* RAG happens
* AI generates answer

Everything important happens here.

---

# POST

Used for:

```text
sending data
```

Since user question is data,
frontend uses:

```http
POST /ask
```

---

# Example Request

```json
{
  "question": "What causes climate change?",
  "conversation": [
    {
      "role": "user",
      "content": "Hi"
    },
    {
      "role": "assistant",
      "content": "Hello!"
    }
  ],
  "top_k": 5
}
```

This JSON is the chatbot request.

---

# 1. `question`

Example:

```json
"question":
"What causes climate change?"
```

This is:

```text
Current user question
```

The MAIN thing backend must answer.

---

# WHY THIS IS IMPORTANT

Backend uses this question for:

* embeddings
* vector search
* prompt generation

Everything starts from this.

---

# 2. `conversation`

Example:

```json
"conversation": [
   {
      "role": "user",
      "content": "What is climate change?"
   },
   {
      "role": "assistant",
      "content": "Climate change is..."
   }
]
```

This is:

```text
Previous chat history
```

---

# 3. `top_k`

Example:

```json
"top_k": 5
```

This controls:

```text
How many document chunks to retrieve
```

---

# VERY IMPORTANT RAG CONCEPT

Suppose climate documents contain:

```text
10,000 chunks
```

Backend cannot send ALL to LLM.

Too expensive and huge.

So backend retrieves only:

```text
Most relevant chunks
```

---

# COMPLETE BACKEND FLOW

Now let’s combine everything.

## STEP 1 — Frontend Sends POST Request

```http
POST /ask
```

with JSON.

---

## STEP 2 — FastAPI Receives Request

Example:

```python
@app.post("/ask")
async def ask(data: AskRequest):
```

---

## STEP 3 — Extract Question

```python
question = data.question
```

---

## STEP 4 — Create Embedding Vector

```python
query_embedding =
   embedder.encode(question)
```

---

## STEP 5 — Search ChromaDB

```python
results = collection.query(
   query_embeddings=[query_embedding],
   n_results=top_k
)
```

---

## STEP 6 — Retrieve Relevant Chunks

Example:

```text
Climate change causes...
Sea level rise occurs...
```

---

## STEP 7 — Build Prompt

Backend combines:

* conversation history
* retrieved chunks
* current question

into one prompt.

---

# EXAMPLE PROMPT

```text
Context:
[retrieved climate chunks]

Conversation:
[user + assistant history]

Question:
What causes climate change?
```

---

## STEP 8 — Send to Groq LLM

```python
response =
   groq_client.chat(prompt)
```

---

## STEP 9 — LLM Generates Answer

Example:

```text
Climate change is mainly caused by...
```

---

## STEP 10 — Backend Returns JSON

```json
{
   "answer": "...",
   "citations": [...]
}
```

---

## STEP 11 — Frontend Renders Answer

`render.js` displays response.

---

# COMPLETE SYSTEM FLOW

```text
User asks question
        ↓
POST /ask
        ↓
Backend receives JSON
        ↓
Embedding model creates vector
        ↓
ChromaDB retrieves top_k chunks
        ↓
Prompt assembled
        ↓
Groq LLM generates answer
        ↓
Backend returns response
        ↓
Frontend displays AI answer
```

This is the HEART of the whole chatbot.

---

# `GET /book/document`

```text
(iframe)
```

The chatbot loads a document viewer inside an iframe, and optionally communicates with it using `postMessage` for citation jumps.

This is how:

* AI answers
* citations
* document viewer

all become connected together.

---

# The Chatbot UI Has TWO Major Sections

## LEFT SIDE

Chat conversation.

```text
User ↔ AI
```

---

## RIGHT SIDE

Document/book viewer.

```text
Climate PDF / HTML Book
```

The right side is implemented using:

```text
iframe
```

---

# WITHOUT IFRAME

Everything mixed together:

* chat UI
* document rendering
* PDF scripts
* scrolling

Problems:

* CSS conflicts
* rendering issues
* difficult navigation

---

# WITH IFRAME

Document becomes isolated.

Like:

```text
mini independent webpage
```

Very clean architecture.

---

# HOW THIS WORKS

Suppose backend URL is:

```text
https://backend.com
```

Frontend creates iframe:

```html
<iframe
   src="https://backend.com/book/document">
</iframe>
```

---

# Browser Automatically Sends

```http
GET /book/document
```

to backend.

---

# BACKEND RESPONDS WITH DOCUMENT

Could return:

* PDF
* HTML book
* annotated document

Then iframe displays it.

---

# COMPLETE FLOW

```text
Frontend creates iframe
         ↓
iframe requests /book/document
         ↓
FastAPI backend sends document
         ↓
iframe displays book/PDF
```

---

# WHAT DOES `/book/document` ACTUALLY DO?

This endpoint serves the knowledge document.

Example FastAPI:

```python
@app.get("/book/document")
async def get_document():

    return FileResponse(
       "climate_book.html"
    )
```

---

# `POST /conversation/export`

```text
CSV download
```

The chatbot can export the entire conversation/chat history into a downloadable CSV file.

Very useful for:

* research
* analysis
* auditing
* saving conversations
* evaluating AI answers

---

# Suppose Conversation Looks Like

```text
User: What is climate change?
AI: Climate change is...

User: What causes it?
AI: Greenhouse gases...
```

User clicks:

```text
Export Conversation
```

Then chatbot downloads a file like:

```text
conversation.csv
```

containing the full chat.

---

# EXAMPLE CSV

```csv
role,message
user,What is climate change?
assistant,Climate change is...
user,What causes it?
assistant,Greenhouse gases...
```

---

# COMPLETE FLOW

```text
User clicks Export
        ↓
Frontend sends POST /conversation/export
        ↓
Conversation JSON sent
        ↓
Backend converts chat → CSV
        ↓
Backend returns file
        ↓
Browser downloads CSV
```

---

# BACKEND IMPLEMENTATION IDEA

FastAPI endpoint might look like:

```python
@app.post("/conversation/export")
async def export_chat(data):

    conversation =
       data["conversation"]

    csv_content = create_csv(
       conversation
    )

    return Response(
       csv_content,
       media_type="text/csv"
    )
```

---

# Frontend Probably Does

```javascript
const response =
   await fetch(
      "/conversation/export",
      {
         method: "POST",
         body: JSON.stringify({
            conversation
         })
      }
   );

const blob =
   await response.blob();

download(blob);
```

---

# `GET /logs/export`

```text
CSV download
```

---

# CSV FORMAT

```csv
timestamp,role,message
10:00,user,What is climate change?
10:01,assistant,Climate change is...
```

---

# HOW THIS CONNECTS TO `state.js`

Remember:

```javascript
state.messages
```

stores conversation.

Frontend exports that state.

---

# FLOW

```text
state.messages
       ↓
/logs/export
       ↓
Backend converts to CSV
       ↓
CSV download
```

---

# `/logs/export`

Exports:

```text
System/backend logs
```
