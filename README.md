# chatbot

Cursor's explanation

## How climate_streamlit/app.py works
It’s a Streamlit app that does a simple RAG (Retrieval-Augmented Generation) loop:

UI (Streamlit)

Sets the page title/layout and defines some inline CSS for the chat bubbles.
Keeps chat history in st.session_state.messages.
Sidebar lets you pick a language (English/Hindi/French) and click example questions.
“Clear chat” empties st.session_state.messages and reruns.
Cached resources (runs once, then reused)

load_embedder() loads a local embedding model: all-MiniLM-L6-v2 using sentence-transformers.
load_groq() creates a Groq(...) client using GROQ_API_KEY from either:
environment variable GROQ_API_KEY, or
Streamlit secrets: st.secrets["GROQ_API_KEY"]
If the key is missing, it shows an error and stops the app.
Build / load the vector database (first run vs later runs)

build_knowledge_base() uses chromadb.PersistentClient(path=CHROMA_DIR) with CHROMA_DIR = "./chroma_db".
It checks collection.count(). If the DB already has chunks, it skips re-embedding.
Otherwise it:
extracts text from ClimateAcademy_Book.pdf using pdfplumber,
chunks the text (with overlap) into pieces of about CHUNK_SIZE=400 words and CHUNK_OVERLAP=60,
embeds each chunk with the local embedding model,
stores (documents, embeddings) into ChromaDB.
Chat loop (retrieve → answer)

## When you ask a question:
retrieve() embeds your question, queries ChromaDB for top TOP_K=5 chunks, and filters by distance (d < 1.5).
ask_groq() builds a prompt:
system message = rules + --- retrieved passages --- {context}
then appends the last 10 conversation turns
sends it to Groq (GROQ_MODEL = "llama-3.3-70b-versatile") and returns the assistant text.
The assistant response is appended to st.session_state.messages and rendered.


## How to run it
From the repo root:

Go into the app folder:

cd climate_streamlit
Make sure you have a Groq API key in:

climate_streamlit/.streamlit/secrets.toml
It must be GROQ_API_KEY = "gsk_...your_key_here" (the file currently has a placeholder).
Ensure the PDF is present in the same folder as app.py:

climate_streamlit/ClimateAcademy_Book.pdf
Create/activate a virtualenv and install requirements:

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Start the app:

streamlit run app.py
Then open http://localhost:8501
On the first run, it will take a couple minutes to build ./chroma_db. Subsequent runs should be fast.

Fixing your chroma-hnswlib build error on macOS
Your failure is happening while installing chromadb’s dependency chroma-hnswlib, and the log shows:

“You have not agreed to the Xcode license agreements…”
and then “Unsupported compiler -- at least C++11 support is needed!”
Do this:

Accept the Xcode license + ensure compiler tools exist:

sudo xcodebuild -license
(also usually necessary) xcode-select --install
Retry dependency install in the activated venv:

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
If it still can’t build wheels, the next most common cause is no wheel available for your Python version/architecture. In that case, switch to a Python version that has better wheel coverage (often Python 3.11 on macOS/arm64), recreate the venv, and reinstall.

If you tell me your python --version (inside the venv) and whether you’re on Apple Silicon (arm64), I can suggest the most likely “pin/change” to make chromadb install cleanly.