# Web Client Architecture & Frontend Structure

This document explains the frontend architecture of the Semantic Climate chatbot, specifically focusing on the `web_client` directory.

The frontend is a lightweight, static web application built with vanilla HTML, CSS, and JavaScript. It does not use heavy frameworks like React or Vue, and relies on a backend API to fetch data.

## Folder Structure

Here is a visual map of everything inside the `web_client/` folder:

```text
web_client/
├── index.html         
├── css/               
│   ├── components.css 
│   ├── layout.css     
│   └── tokens.css     
└── js/                
    ├── api.js
    ├── examples.js
    ├── examples_data.js
    ├── lang_prefs.js
    ├── main.js
    ├── render.js
    ├── state.js
    └── ui_strings.js
```

### Understanding the CSS Files (How they connect to `index.html`)

To make styling easier to manage, the CSS is split into three specific files. Here is what each does and exactly where you can see it working inside `index.html`:

1.  **`tokens.css` (The Materials / Variables)**
    *   **What it does:** It stores the master "design rules" like brand colors (`--color-brand`), fonts, and spacing. 
    *   **Where it's used:** It is applied globally. Every other CSS file and HTML element references these variables so that if we want to change the "brand green", we only change it in one place.

2.  **`layout.css` (The Floorplan / Structure)**
    *   **What it does:** It dictates the size and placement of the big panels. It is responsible for making the app stack vertically on phones and sit side-by-side on wide desktop screens.
    *   **Where it's used in `index.html`:** 
        *   `<div class="app">`: Uses layout rules to center the entire app on your screen.
        *   `<main class="main-grid">`: Uses CSS Grid rules to split the screen into the left column (Chat) and right column (Student Book).
        *   `<section class="panel">`: Defines the white box, border, and drop-shadow for all the major panels (Settings, Chat, Sources, and Book).

3.  **`components.css` (The Furniture / Details)**
    *   **What it does:** It styles the individual interactive pieces *inside* the layout panels. It controls hover effects, button shapes, and text formatting.
    *   **Where it's used in `index.html`:**
        *   `<button class="btn btn-primary">`: Gives the "Send" button its green gradient and rounded edges.
        *   `<textarea class="composer-input">`: Styles the text box where you type your question.
        *   *(Dynamically created)*: It also styles the chat bubbles (`.bubble-user`) and citation chips (`.chip`) that appear in the chat thread.

## Identified Frontend Panels

The application interface is divided into several main "panels" (windows or regions on the screen). To maintain consistency when writing code, discussing bugs, or opening GitHub issues, we use the following standard names:

### 1. Settings Panel
*   **HTML Class:** `class="panel panel-settings"`
*   **Purpose:** The top control bar where you set the API connection URL, choose your chat language, check system health, and export chat logs.

### 2. Query Panel (Chat Window)
*   **HTML Class:** `class="panel panel-chat"`
*   **Purpose:** The main interaction area where you type questions and see the chatbot's responses. It contains the message thread and the text input box.

### 3. Sources Panel
*   **HTML Class:** `class="panel panel-sources"`
*   **Purpose:** The area that displays the exact text of a cited paragraph when you click a citation number in the Query Panel. On mobile, this sticks to the bottom of the screen.

### 4. Student Book Panel
*   **HTML Class:** `class="panel panel-book"`
*   **Purpose:** The large viewer (using an `iframe`) that displays the actual Climate Academy student book. It highlights specific paragraphs when you click citations in the chat.
