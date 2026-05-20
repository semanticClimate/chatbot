### Client-User architecture

# This is called a Client-User beacause the browser UI behaves as a client which asks for the responses to the backend.

* The previous streamlit interface is Monolithic architecture in which only single section handles both front end and backend which is a little disfuncitonal 
* The new architecture is upgraded to  Decoupled architecture,where there are two  sections one for Web UI and Fast API the backened 

### The User-Client Browser ( Frontend ) 

## Page origin — where index.html is served
(e.g. http://127.0.0.1:8081 or https://….trycloudflare.com)

* The Static files run here
 - HTML
 - CSS
 - JavaScript

* The webpage is served in the both
    - http://127.0.0.1:8081 the local server
    - https://xxxx.trycloudflare.com the global server 

## ES modules from same origin
main.js wires UI → api/state/render/examples

* ES Modules (ECMAScript Modules) are the modern JavaScript module system used to split code into multiple files and allow files to communicate cleanly.

* Instead of writing everything in one file:

main.js

we split responsibilities:

api.js
render.js
state.js
examples.js
utils.js

Each file becomes a module.

* In the architecture:

main.js wires UI → api/state/render/examples

The chatbot frontend is broken into specialized modules.

This makes the frontend:

scalable
maintainable
reusable
professional

* frontend/
│
├── index.html
├── main.js
├── api.js
├── state.js
├── render.js
├── examples.js
├── citations.js
└── styles.css

* 1. main.js — APPLICATION CONTROLLER

This is the startup orchestrator.

Think of it as:

frontend manager

Responsibilities:

initialize app
attach button listeners
connect modules together
app startup
Example
import { sendQuestion } from "./api.js";
import { renderMessage } from "./render.js";
import { state } from "./state.js";

* 2. api.js — NETWORK LAYER

This module handles backend communication.

VERY important separation.

WHY SEPARATE NETWORK LOGIC?

Without separation:

button.onclick = async () => {
   fetch(...)
}

inside many files becomes messy.

Instead:

api.js = all backend communication

Clean architecture.

Likely Functions in api.js
export async function checkHealth()

export async function askQuestion()

export async function getDocument()

export async function exportConversation()

This file centralizes:

URLs
headers
fetch logic
error handling

* 3. state.js — CLIENT MEMORY

VERY important concept.

Frontend needs memory/state.

WHAT IS STATE?

State means:

current application data

Examples:

conversation history
current API URL
loading state
selected citations
Example state.js
export const state = {
    messages: [],
    apiBase: "",
    loading: false
};

This becomes centralized frontend memory.

* 4. render.js — UI RENDERING ENGINE

This file handles:

creating HTML
updating DOM
displaying messages
WHY SEPARATE RENDERING?

UI logic becomes messy quickly.

Instead:

render.js = ONLY UI rendering

* 5. examples.js

Stores quick prompts.

Example:

export const examples = [
    "What causes global warming?",
    "Explain greenhouse gases"
];

Frontend uses this to render chips/buttons.

## Optional fetch: tunnel-api-base.txt
same-origin, cache-busted on tunnel hosts

* THE CORE PROBLEM

Remember:

Frontend and backend are separated.

Frontend may be hosted somewhere like:

https://frontend.trycloudflare.com

Backend may be running at:

https://backend.trycloudflare.com

But:

Cloudflare tunnel URLs change frequently
ngrok URLs change
localhost ports change

So frontend doesn’t know:

"Which backend URL should I connect to?"

* HOW IT WORKS

The frontend tries to fetch:

tunnel-api-base.txt

from the SAME ORIGIN.

Example:

If frontend loaded from:

https://frontend.trycloudflare.com

then frontend requests:

https://frontend.trycloudflare.com/tunnel-api-base.txt

* The file contains Very simple text file.

Example:

https://backend.trycloudflare.com

That’s it.

Just the backend base URL.


## localStorage key: climate_web_client_api_base
(saved API base URL)

* localStorage is a built-in browser storage system that allows a website to save data directly inside the user’s browser.

It is part of:

Web Storage API

Every modern browser supports it:

Chrome
Edge
Firefox
Safari

* HOW IT WORKS
STEP 1 — User enters backend URL

Inside connection panel:

API Base URL:
https://abc.trycloudflare.com
STEP 2 — Frontend saves it

Using:

localStorage.setItem(
   "climate_web_client_api_base",
   "https://abc.trycloudflare.com"
)
STEP 3 — Browser stores it permanently

Now even after:

refresh
reopening browser

the value still exists.

STEP 4 — On app startup

Frontend reads it back:

const apiBase =
   localStorage.getItem(
      "climate_web_client_api_base"
   );

Now frontend auto-connects.

VISUAL FLOW
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

## Connection: API base URL input
Check health · Clear chat

* This component is the:

Frontend Connection Manager

It controls:

backend connectivity
API configuration
health verification
conversation reset
runtime environment switching

It is basically the “control panel” between frontend and backend.

* 1. API BASE URL INPUT

This is probably a textbox like:

[ https://abc.trycloudflare.com ]

This is where the user specifies:

Backend FastAPI server location

* Frontend is static JavaScript.

It does NOT automatically know:

backend IP
backend domain
backend port

So user or auto-discovery provides:

API Base URL
WHAT IS AN API BASE URL?

Suppose backend endpoints are:

https://backend.com/health
https://backend.com/ask
https://backend.com/ready

The common root is:

https://backend.com

That is:

API Base URL

Frontend dynamically builds requests using it.

# Health Check
* 
fetch(apiBase + "/health")

becomes:

https://backend.com/health
Ask Question
fetch(apiBase + "/ask")

becomes:

https://backend.com/ask
Book Viewer
iframe.src =
  apiBase + "/book/document"

becomes:

https://backend.com/book/document

Everything depends on this base URL.

# Clear Chat
* This is a state-management operation
* the complete chat is deleted from the UI and backend storage

## Example question chips
(examples.js)

* Small clickable sample questions shown in the UI

Like these:

[ What is climate change? ]
[ Explain greenhouse gases ]
[ Effects of global warming ]

These are called:

Chips

because they look like small rounded buttons.

* They help users:
- quickly test chatbot
- understand what to ask
- avoid typing
- improve user experience

* Especially useful for:
- demos
- first-time users
- presentations

* examples.js
export const examples = [
   "What is climate change?",
   "Explain greenhouse gases",
   "How does deforestation affect climate?"
];

## Composer: POST question on submit 

* The chat input box sends the user's question to the backend when the user presses Submit.

That’s all at a high level.

Now let’s understand it properly and simply.

WHAT IS "COMPOSER"?

Composer means:

The message typing area

Like ChatGPT’s input box.

Example:

--------------------------------
| Ask something...             |
--------------------------------
            [ Send ]

That whole section is called:

Composer

because user composes/writes a message there.

* When user presses:

Enter
OR
Send button

the frontend sends the question to backend using:

POST /ask

- HTTP has methods like:

    - GET
    - POST
    - PUT
    - DELETE
* GET

Used to:

fetch data

Example:

GET /health
POST

Used to:

send data

Since user question is data,
frontend uses:

POST /ask
WHAT DATA IS SENT?

Frontend likely sends JSON.

Example:

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

* question

Current user question.

conversation

Previous chat history.

Helps AI remember context.

top_k

How many document chunks to retrieve from vector DB.

Example:

Retrieve top 5 most relevant chunks

## Book panel: iframe → API base plus /book/document
postMessage jumps for citations → iframe origin

# An iframe is a used when a webpage is inserted inside another webpage

* The chatbot has a built-in document/book viewer connected to the AI answers.

So when AI gives citations like:

[Page 12]
[Section 3]

you can click them and the book automatically jumps to that location.

Very similar to:

- NotebookLM
- Perplexity citations
- research assistants

# Book Viewer iframe
https://abc.trycloudflare.com/book/document

* This is where the PDF book is displayed inside the chatbot UI.

It’s an iframe.

Which means:

A web page showing another web page
Example:
<iframe
  src="https://backend.com/book/document"
  width="100%"
  height="600px"
></iframe>

* browsers protect cross-window communication.

Without origin checks:

malicious websites could spy
unsafe message injection possible
Example

Parent page:

https://frontend.com

Iframe:

https://backend.com/book/document

Messages must specify correct target origin.

LIKELY IMPLEMENTATION
Parent Page
iframe.contentWindow.postMessage(
   {
      type: "jump",
      citation: 12
   },
   "https://backend.com"
);
Iframe Side
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

## Conversation thread
(render.js + state.js)

* The system that stores and displays the chat conversation.

This is basically the:

Chat History System

like:

User: Hi
AI: Hello
User: Explain climate change
AI: ...
WHY IT SAYS:
(render.js + state.js)

Because TWO modules work together:

1. state.js

Stores conversation data in memory.

2. render.js

Displays conversation on screen.

# PART 1 — state.js

This is the chatbot’s temporary memory.

WHAT DOES IT STORE?

Usually:

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

This is the conversation history.

WHY STORE IT?

Because AI needs context.

Example:

First question
"What is climate change?"
Second question
"What causes it?"

AI must know:

"it" = climate change

So frontend stores previous messages.

THIS IS CALLED STATE

State means:

current app data

For chatbot:

messages
loading state
current conversation

#  PART 2 — render.js

This module displays messages on screen.

WHAT DOES IT DO?

Takes message data from state.js and creates UI.

Example:

renderMessage(
   "user",
   "What is climate change?"
);

Then message bubble appears.

---

---

### Fast API Section - The Backend

## GET /health
* is one of the MOST important parts of modern backend systems.

It is called:

Health Check Endpoint

Its job is simply:

"Tell me if the backend server is alive."

* EXAMPLE

Suppose backend URL is:

https://backend.com

Frontend sends:

GET https://backend.com/health
BACKEND RECEIVES REQUEST

FastAPI has endpoint like:

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }
BACKEND RESPONDS
{
   "status": "ok"
}
FRONTEND RECEIVES RESPONSE

Frontend now knows:

"Backend server is alive."

So UI may show:

🟢 Connected

## GET /ready

* AI backends are HEAVY.

When backend starts:

server may start quickly
BUT
models still loading
vector DB initializing
embeddings downloading

So backend may be:

ALIVE
but
NOT READY
COMPLETE STARTUP PROCESS

When FastAPI starts:

STEP 1 — Server starts
FastAPI process alive

So:

/health → OK
STEP 2 — AI components load

Backend now loads:

embedding model
vector DB
documents
LLM clients

This may take:

seconds
minutes
STEP 3 — Everything initialized

Now:

/ready → true
WHY THIS IS IMPORTANT

Without /ready:

Frontend may send question too early.

Then:

vector DB missing
embeddings unavailable
crashes happen

/ready prevents that.

# /ready checks for 
# 1. EMBEDDING MODEL LOADED

Example:

embedder != None
WHAT IS AN EMBEDDING MODEL?

This is the AI model that converts text into numbers/vectors.

SIMPLE EXAMPLE

Suppose user asks:

"What causes global warming?"

The embedding model converts it into something like:

[0.23, -0.91, 0.44, ...]

called:

Vector Embedding
* Vectors help AI understand:

similarity
meaning
semantic relationships

#2. CHROMADB CONNECTED

Example:

collection exists
WHAT IS CHROMADB?

ChromaDB is the:

Vector Database

It stores document embeddings.

SIMPLE IDEA

Suppose climate book has:

1000 paragraphs

Each paragraph converted into vector embeddings.

Stored in ChromaDB.

# 3. KNOWLEDGE BASE INDEXED

Example:

documents loaded
WHAT IS KNOWLEDGE BASE?

This means:

climate PDFs
books
processed chunks

basically:

All source documents
* Suppose PDF has:

500 pages

Backend performs:

STEP 1 — Extract text
PDF → text
STEP 2 — Split into chunks

Example:

Chunk 1
Chunk 2
Chunk 3
...
STEP 3 — Create embeddings

Each chunk converted into vector.

STEP 4 — Store in ChromaDB

Now searchable.

This whole process is called:

Indexing

# 4. GROQ CLIENT INITIALIZED

Example:

groq_client != None
WHAT IS GROQ CLIENT?

This is the connection to the actual LLM.

Like:

Llama
Mixtral
Gemma

running through Groq API.

WHAT DOES IT DO?

After retrieval:

Backend builds prompt:

Context:
...

Question:
...

Then sends it to Groq.

FLOW
Retrieved chunks
      ↓
Prompt construction
      ↓
Groq LLM
      ↓
Generated answer

# STEP 1 — User asks question
"What causes global warming?"
# STEP 2 — Embedding model converts question
Text → Vector
# STEP 3 — ChromaDB searches vectors
Find relevant climate chunks
# STEP 4 — Knowledge base provides chunks
Relevant paragraphs retrieved
# STEP 5 — Groq LLM generates answer
Final AI response


### POST /ask
JSON: question, conversation[, top_k]

* The main AI brain endpoint

This is where:

user question arrives
RAG happens
AI generates answer

Everything important happens here.

* POST

Used for:

sending data

Since user question is data,
frontend uses:

POST /ask

* Example:

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

This JSON is the chatbot request.

# 1. question

Example:

"question":
"What causes climate change?"

This is:

Current user question

The MAIN thing backend must answer.

WHY THIS IS IMPORTANT

Backend uses this question for:

embeddings
vector search
prompt generation

Everything starts from this.

# 2. conversation

Example:

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

This is:

Previous chat history

# 3. top_k

Example:

"top_k": 5

This controls:

How many document chunks to retrieve
VERY IMPORTANT RAG CONCEPT

Suppose climate documents contain:

10,000 chunks

Backend cannot send ALL to LLM.

Too expensive and huge.

So backend retrieves only:

Most relevant chunks

# COMPLETE BACKEND FLOW

Now let’s combine everything.

# STEP 1 — Frontend sends POST request
POST /ask

with JSON.

# STEP 2 — FastAPI receives request

Example:

@app.post("/ask")
async def ask(data: AskRequest):
# STEP 3 — Extract question
question = data.question
# STEP 4 — Create embedding vector
query_embedding =
   embedder.encode(question)
# STEP 5 — Search ChromaDB
results = collection.query(
   query_embeddings=[query_embedding],
   n_results=top_k
)
# STEP 6 — Retrieve relevant chunks

Example:

Climate change causes...
Sea level rise occurs...
# STEP 7 — Build prompt

Backend combines:

conversation history
retrieved chunks
current question

into one prompt.

# EXAMPLE PROMPT
Context:
[retrieved climate chunks]

Conversation:
[user + assistant history]

Question:
What causes climate change?

# STEP 8 — Send to Groq LLM
response =
   groq_client.chat(prompt)

# STEP 9 — LLM generates answer

Example:

Climate change is mainly caused by...
# STEP 10 — Backend returns JSON
{
   "answer": "...",
   "citations": [...]
}
# STEP 11 — Frontend renders answer

render.js displays response.

COMPLETE SYSTEM FLOW
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

This is the HEART of the whole chatbot.

## GET /book/document
(iframe)

# The chatbot loads a document viewer inside an iframe, and optionally communicates with it using postMessage for citation jumps.

This is how:

AI answers
citations
document viewer

all become connected together.

# The chatbot UI has TWO major sections:

# LEFT SIDE

Chat conversation.

User ↔ AI
# RIGHT SIDE

Document/book viewer.

Climate PDF / HTML Book

The right side is implemented using:

iframe
# WITHOUT IFRAME

Everything mixed together:

chat UI
document rendering
PDF scripts
scrolling

Problems:

CSS conflicts
rendering issues
difficult navigation

# WITH IFRAME

Document becomes isolated.

Like:

mini independent webpage

Very clean architecture.

* HOW THIS WORKS

Suppose backend URL is:

https://backend.com

Frontend creates iframe:

<iframe
   src="https://backend.com/book/document">
</iframe>

# Browser automatically sends:

GET /book/document

to backend.

BACKEND RESPONDS WITH DOCUMENT

Could return:

PDF
HTML book
annotated document
THEN IFRAME DISPLAYS IT

Now document appears inside panel.

# COMPLETE FLOW
Frontend creates iframe
         ↓
iframe requests /book/document
         ↓
FastAPI backend sends document
         ↓
iframe displays book/PDF
# WHAT DOES /book/document ACTUALLY DO?

This endpoint serves the knowledge document.

Example FastAPI:

@app.get("/book/document")
async def get_document():

    return FileResponse(
       "climate_book.html"
    )

## POST /conversation/export
CSV download

# The chatbot can export the entire conversation/chat history into a downloadable CSV file.

Very useful for:

research
analysis
auditing
saving conversations
evaluating AI answers

# Suppose conversation looks like:

User: What is climate change?
AI: Climate change is...

User: What causes it?
AI: Greenhouse gases...

User clicks:

Export Conversation

Then chatbot downloads a file like:

conversation.csv

containing the full chat.

# EXAMPLE CSV
role,message
user,What is climate change?
assistant,Climate change is...
user,What causes it?
assistant,Greenhouse gases...

# COMPLETE FLOW
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

# BACKEND IMPLEMENTATION IDEA

FastAPI endpoint might look like:

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

# Frontend probably does:

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

## GET /logs/export
CSV download

# CSV FORMAT
timestamp,role,message
10:00,user,What is climate change?
10:01,assistant,Climate change is...

# HOW THIS CONNECTS TO state.js

Remember:

state.messages

stores conversation.

Frontend exports that state.

# FLOW
state.messages
       ↓
/logs/export
       ↓
Backend converts to CSV
       ↓
CSV download