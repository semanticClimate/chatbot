# Using the Help Window (Browser‑Only Onboarding Tool)

This short guide explains how to interact with the **Help** overlay that appears for new users of the Climate Academy chat UI.

---

## 1. When the Help window appears automatically
- Open the chat UI in your browser (e.g., `http://127.0.0.1:8081` or the public **trycloudflare.com** URL).
- On your **first visit** you will see a semi‑transparent backdrop with a card titled **“Welcome to the Climate Academy chat UI”**.
- The card lists a few quick‑start steps (language selector, how to ask a question, etc.).
- Dismiss the window by clicking the **✕** button in the top‑right of the card, the **Got it!** button at the bottom, or by pressing **Esc** on your keyboard.

> The UI stores a flag in `localStorage` (`climate_help_seen`) so the overlay will **not** automatically show again on subsequent page loads.

---

## 2. Re‑opening the Help window later
- A **Help icon** (❔) has been added to the far‑right of the header bar.
- Click this icon at any time to bring the Help overlay back.
- The same steps listed above will be shown again.

---

## 3. Language support
- The Help window follows the same i18n system as the rest of the UI.
- Changing the UI language from the language selector (top‑right dropdown) instantly updates the Help text to the chosen language.
- English (`en`) and French (`fr`) are provided out‑of‑the‑box; additional languages can be added in `web_client/js/ui_strings.js` under the `help` namespace.

---

## 4. Accessibility notes
- The overlay is a proper **ARIA dialog** (`role="dialog"`, `aria-modal="true"`).
- Focus is moved into the dialog when it opens and trapped inside until the dialog is closed.
- Keyboard users can navigate with **Tab** and dismiss with **Esc**.

---

## 5. Resetting the “first‑time” flag (for testing)
If you want the Help window to show again as if you were a brand‑new visitor:
```js
localStorage.removeItem('climate_help_seen');
// then reload the page
``` 
You can run the above snippet in the browser console.

---

## 6. Where the code lives
- **HTML**: `web_client/index.html` (Help button and overlay markup). 
- **CSS**: `web_client/css/help.css` (styles for backdrop, card, buttons, responsive behavior). 
- **JS**: `web_client/js/help.js` (logic for showing/hiding, i18n population, persistence, focus trap). 
- **Strings**: `web_client/js/ui_strings.js` (new `help` namespace). 
- **Documentation**: this file (`docs/client/help-tool.md`).

---

## 7. Quick checklist before committing changes
- [ ] Verify the overlay appears on first load. 
- [ ] Test the Help icon re‑opens the modal. 
- [ ] Switch UI language and confirm the help text updates. 
- [ ] Run an accessibility audit (focus trap, ARIA, contrast). 
- [ ] Ensure the `localStorage` flag is set correctly.

That’s it! The Help window provides a smooth, self‑contained onboarding experience for anyone opening the chat UI for the first time.
