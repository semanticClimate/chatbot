# How the Climate Academy AI Assistant Works

*A plain-language guide for colleagues (non-technical readers)*

**Climate Academy Student Book** · Matthew Pye (2025)

---

## What it is

The **Climate Academy Assistant** is a chat tool that answers questions using the **Climate Academy Student Book**. Think of it as a patient study partner who has the textbook open and tries to answer **only from that book**—not from random websites or general “internet knowledge.”

You type a question in normal language (English, Hindi, French, or others). The assistant replies in **the same language you used**, with short, clear answers and **references to book sections** (for example **§ 1.2.3**).

---

## What it is not

| Myth | Reality |
|------|---------|
| “It knows everything about climate.” | It only uses text prepared from **this book**. |
| “It is always right.” | It can misread or combine passages; treat it as a **helper**, not an authority. |
| “It browses the web live.” | It searches a **pre-built index** of book passages on the server. |
| “It remembers me forever.” | It remembers only the **current chat** (recent messages), not you across months. |

---

## The big picture (three steps)

```
  YOU                         BOOK (prepared once)              ANSWER WRITER
  ---                         --------------------              -------------

  Ask a question    -->    Passages indexed by meaning    -->   Writes reply using
  in the chat              (searchable “smart index”)           ONLY those passages
                                                                  + section citations

  Read the answer   <--
  in the chat
```

1. **Prepare the book (once)** — The book is split into many small **passages** and indexed so the system can find “the parts most like your question.”
2. **Find passages (every question)** — Your question is matched to the **top few passages** from the book.
3. **Write the answer (every question)** — A language model **drafts a reply using only those passages**, with rules like “do not invent facts” and “cite section numbers.”

---

## Step 1 — Preparing the book (before anyone chats)

Like building a very smart index at the back of a textbook:

```
  Student Book (HTML)
        |
        v
  Split into sections & paragraphs  (section numbers: § 1.2.3 …)
        |
        v
  Cut into overlapping passages     (a few hundred words each)
        |
        v
  “Fingerprints” for meaning        (so similar ideas match, not just keywords)
        |
        v
  Search index stored on disk
```

**Analogy:** A librarian cuts the book into labelled index cards—each tagged with “§ which section”—and files them in a cabinet sorted by *meaning*, not only alphabetically.

---

## Step 2 — When someone asks a question

```
  Colleague          Chat screen        Passage finder       Book index
     |                   |                    |                  |
     |-- question ------>|                    |                  |
     |                   |-- find similar --->|                  |
     |                   |                    |--- search ----->|
     |                   |                    |<-- top 5 passages|
     |                   |<-- passages -------|                  |
     |                   |--- passages + rules + history -----> AI writer
     |<-- answer --------|                    |                  |
```

**Semantic search** means the system looks for passages about the *same idea* as your question, not only the exact same words.

Example: a question about “why Earth is warming” can still find a passage about the “greenhouse effect” even if you never used those words.

---

## Step 3 — How the answer is written

The **answer writer** is a large language model (in our setup: **Llama 3.3** via **Groq**). It does **not** freely invent climate facts. It is given strict instructions, including:

- Answer **only** from the passages retrieved in step 2.
- Reply in the **same language** as the user.
- If the book does not cover the topic, say: *“I could not find information about that in the Climate Academy book.”*
- **Cite section numbers** (e.g. **§ 1.2**) when using information from a passage.
- Stay concise and encouraging; use bullet points when listing several items.

**Analogy:** A teaching assistant who may only quote from the highlighted pages you handed them—not from memory of other textbooks.

---

## Example question and answer

**Colleague asks:**

> What is the greenhouse effect?

**Behind the scenes:** The index returns passages from a section such as *“The greenhouse effect”*, including: certain gases trap heat; sunlight warms the surface; the surface emits infrared radiation; greenhouse gases absorb and re-emit heat.

**The assistant might reply (illustrative):**

> The **greenhouse effect** is the process by which certain gases in the atmosphere trap heat, keeping Earth warmer than it would otherwise be. Without it, the planet would be much colder.
>
> In short:
> - Sunlight (shortwave) warms the surface.
> - The surface emits infrared radiation.
> - Greenhouse gases absorb and re-emit part of that infrared, so heat is retained.
>
> Key gases in the book include carbon dioxide (CO₂) and methane (CH₄), with water vapour as a fast feedback (**§ … — The greenhouse effect**).

*(Exact § numbers come from the live book; the app inserts real section labels from the passages it found.)*

---

## Example — when the book does not have the answer

**Question:**

> What will global temperatures be in the year 2100?

**Expected behaviour:**

> I could not find information about that in the Climate Academy book.

The assistant is **not** meant to guess future temperatures from general knowledge.

---

## Languages and follow-up questions

- Write in **French** → the assistant is instructed to answer in **French**, using the same English book passages as sources.
- Recent chat messages (about the last ten turns) are included so you can ask “Can you explain that more simply?”
- The sidebar can suggest starter questions (causes of climate change, renewable energy, etc.).

---

## Where colleagues use it

Depending on deployment:

- **On a laptop (demo / testing):** Someone runs the app; testers open a link in the browser.
- **On a small server (planned):** A stable web address—colleagues only need a browser.

The logic is the same: **browser → question → search book index → write answer → show in chat.**

```
  Browser  <----->  App on computer or server  <----->  Book index (local)
                           |
                           v
                    Answer-writing service (Groq)
                    (needs an API key; passages + question sent here)
```

**Privacy note:** Questions and retrieved passages are sent to the **answer-writing service** (Groq) to produce the reply. The book index stays on your machine or server. Check your organisation’s policy before using sensitive topics.

---

## Quality and limitations

| Strength | Limitation |
|----------|------------|
| Grounded in your official book | Weak if the topic is not in the book |
| Section citations (§) help verification | Humans should still confirm citations |
| Works in multiple languages | Quality may vary by language |
| Fast, friendly explanations | Not a substitute for teaching, exams, or policy |

**Good uses:** revision, exploring book content, drafting explanations students can check against the book.

**Poor uses:** exam answers without verification, legal or policy decisions, emergency advice.

---

## One-sentence summary

> The Climate Academy Assistant searches pre-indexed passages from the Student Book, then an AI writes a short answer only from those passages—in your language—with section references—and says clearly when the book does not cover your question.

---

*Document version: May 2026. PDF: `climate-academy-assistant-explained.pdf` (regenerate with `docs/scripts/build_climate_academy_assistant_pdf.py`).*
