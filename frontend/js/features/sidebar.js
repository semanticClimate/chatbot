/**
 * Sidebar toggle wiring.
 *
 * Detailed note:
 * - This is intentionally separate from the chat logic so the navigation shell
 *   can evolve independently of the message flow.
 *
 * Simple note:
 * - Sidebar wiring lives here.
 */

/**
 * Bind the sidebar toggle and overlay click behavior.
 * @returns {void}
 */
export function initSidebarToggle() {
  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("btnSidebarToggle");
  if (sidebar && toggle) {
    toggle.addEventListener("click", () => {
      sidebar.classList.toggle("expanded");
      sidebar.classList.toggle("collapsed");
    });
  }

  const overlay = document.getElementById("sidebarOverlay");
  if (sidebar && overlay) {
    overlay.addEventListener("click", () => {
      sidebar.classList.remove("collapsed");
      sidebar.classList.add("expanded");
    });
  }
}
