/**
 * Shell modals — open/close only. Does not touch chat, health, or language logic.
 * Follows the same implementation pattern already used by the Help feature.
 */

function bindAppModal(triggerId, overlayId, dialogId) {
  const trigger = document.getElementById(triggerId);
  const overlay = document.getElementById(overlayId);
  const dialog = document.getElementById(dialogId);
  if (!trigger || !overlay || !dialog) return;

  const openModal = () => {
    overlay.classList.add("help-visible");
    dialog.classList.add("help-visible");
  };

  const closeModal = () => {
    overlay.classList.remove("help-visible");
    dialog.classList.remove("help-visible");
  };

  const isOpen = () => {
    return dialog.classList.contains("help-visible");
  };

  trigger.addEventListener("click", (e) => {
    e.stopPropagation();
    openModal();
  });

  dialog.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal());
  });

  overlay.addEventListener("click", () => {
    closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && isOpen()) {
      closeModal();
    }
  });
}

function initExternalModal() {
  const overlay = document.getElementById("externalOverlay");
  const dialog = document.getElementById("externalModal");
  const iframe = document.getElementById("externalFrame");
  const btnBack = document.getElementById("btnExternalBack");
  if (!overlay || !dialog) return;

  const closeModal = () => {
    overlay.classList.remove("help-visible");
    dialog.classList.remove("help-visible");
    if (iframe) iframe.src = "";
  };

  dialog.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal());
  });

  overlay.addEventListener("click", () => {
    closeModal();
  });

  if (btnBack) {
    btnBack.addEventListener("click", () => {
      closeModal();
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && dialog.classList.contains("help-visible")) {
      closeModal();
    }
  });
}

function initEncyclopediaModal() {
  const overlay = document.getElementById("encyclopediaOverlay");
  const dialog = document.getElementById("encyclopediaModal");
  const iframe = document.getElementById("encyclopediaFrame");
  if (!overlay || !dialog) return;

  const closeModal = () => {
    overlay.classList.remove("help-visible");
    dialog.classList.remove("help-visible");
    // Clear iframe to stop any loading / free resources
    if (iframe) iframe.removeAttribute("src");
  };

  dialog.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal());
  });

  overlay.addEventListener("click", () => {
    closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && dialog.classList.contains("help-visible")) {
      closeModal();
    }
  });
}

/** ── Global tooltip wiring ─────────────────────────────────────────────── */
function initButtonTooltips() {
  const tip = document.getElementById("appTooltip");
  if (!tip) return;

  let hideTimer = null;

  document.querySelectorAll("[data-tooltip]").forEach((el) => {
    const text = el.getAttribute("data-tooltip");
    if (!text) return;

    el.addEventListener("mouseenter", () => {
      clearTimeout(hideTimer);
      const rect = el.getBoundingClientRect();
      tip.textContent = text;
      tip.classList.add("app-tooltip-visible");

      // Position below the element by default, centred
      requestAnimationFrame(() => {
        const tw = tip.offsetWidth;
        const th = tip.offsetHeight;
        const GAP = 8;
        let left = rect.left + rect.width / 2 - tw / 2;
        let top  = rect.bottom + GAP;

        // Clamp to viewport
        left = Math.max(8, Math.min(left, window.innerWidth - tw - 8));
        // Flip above if overflows bottom
        if (top + th > window.innerHeight - 8) {
          top = rect.top - th - GAP;
        }

        tip.style.left = `${left}px`;
        tip.style.top  = `${top}px`;
      });
    });

    el.addEventListener("mouseleave", () => {
      hideTimer = setTimeout(() => {
        tip.classList.remove("app-tooltip-visible");
      }, 80);
    });

    el.addEventListener("focus", () => el.dispatchEvent(new MouseEvent("mouseenter")));
    el.addEventListener("blur",  () => el.dispatchEvent(new MouseEvent("mouseleave")));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  try {
    bindAppModal("btnSettingsToggle", "settingsOverlay", "settingsModal");
    bindAppModal("btnDevToolsToggle", "healthOverlay", "healthModal");
    initExternalModal();
    initEncyclopediaModal();
    initButtonTooltips();
  } catch (err) {
    console.error("[ui_modals] Initialization failed:", err);
  }
});

