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

document.addEventListener("DOMContentLoaded", () => {
  try {
    bindAppModal("btnSettingsToggle", "settingsOverlay", "settingsModal");
    bindAppModal("btnDevToolsToggle", "healthOverlay", "healthModal");
  } catch (err) {
    console.error("[ui_modals] Initialization failed:", err);
  }
});
