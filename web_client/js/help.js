// help.js – Browser‑only Help window implementation
import { getUiLanguage, UI_STRINGS } from "./ui_strings.js";

// Elements
const overlay   = document.getElementById("helpOverlay");
const btnOpen   = document.getElementById("helpBtn");
const btnClose  = document.getElementById("helpClose");
const btnGotIt  = document.getElementById("helpGotIt");
const titleEl   = document.getElementById("helpTitle");
const stepsEl   = document.getElementById("helpSteps");

const STORAGE_KEY = "climate_help_seen";

function populateStrings() {
  const lang = getUiLanguage();
  const strings = UI_STRINGS.help[lang] || UI_STRINGS.help.en;
  titleEl.textContent = strings.title;
  btnGotIt.textContent = strings.gotIt;
  stepsEl.innerHTML = "";
  strings.steps.forEach(step => {
    const li = document.createElement("li");
    li.textContent = step;
    stepsEl.appendChild(li);
  });
}

// Elements
const overlay   = document.getElementById("helpOverlay");
const btnOpen   = document.getElementById("helpBtn");
const btnClose  = document.getElementById("helpClose");
const btnGotIt  = document.getElementById("helpGotIt");
const titleEl   = document.getElementById("helpTitle");
const stepsEl   = document.getElementById("helpSteps");

const STORAGE_KEY = "climate_help_seen";

function populateStrings() {
  const strings = uiStrings.help[currentLang] || uiStrings.help.en;
  titleEl.textContent = strings.title;
  btnGotIt.textContent = strings.gotIt;
  stepsEl.innerHTML = "";
  strings.steps.forEach(step => {
    const li = document.createElement("li");
    li.textContent = step;
    stepsEl.appendChild(li);
  });
}

function hasSeenHelp() {
  return localStorage.getItem(STORAGE_KEY) === "true";
}
function markSeen() {
  localStorage.setItem(STORAGE_KEY, "true");
}

function openHelp() {
  populateStrings();
  overlay.classList.remove("hidden");
  overlay.setAttribute("aria-hidden", "false");
  // Move focus to the close button for accessibility
  btnClose.focus();
}
function closeHelp() {
  overlay.classList.add("hidden");
  overlay.setAttribute("aria-hidden", "true");
  markSeen();
  // Return focus to the Help icon
  btnOpen.focus();
}

// Focus trap inside the modal
let focusableElements = [];
function buildFocusTrap() {
  const focusables = overlay.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  focusableElements = Array.from(focusables);
}
function trapFocus(e) {
  if (e.key !== "Tab") return;
  const first = focusableElements[0];
  const last  = focusableElements[focusableElements.length - 1];
  if (e.shiftKey) {
    if (document.activeElement === first) {
      e.preventDefault();
      last.focus();
    }
  } else {
    if (document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}

// Event listeners
btnOpen.addEventListener("click", openHelp);
btnClose.addEventListener("click", closeHelp);
btnGotIt.addEventListener("click", closeHelp);
overlay.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeHelp();
  else trapFocus(e);
});

document.addEventListener("DOMContentLoaded", () => {
  buildFocusTrap();
  openHelp();
});
