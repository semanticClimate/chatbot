/**
 * Tooltip behavior for the book term previews.
 *
 * Detailed note:
 * - This is intentionally tiny, but separating it makes the modal/book code
 *   easier to read and easier to extend later if the tooltip needs animations
 *   or accessibility tweaks.
 *
 * Simple note:
 * - Tooltip logic lives here.
 */

/**
 * Show or hide the floating term preview tooltip.
 * Coordinates are received from the book iframe in viewport space.
 * @param {string} text
 * @param {number} x
 * @param {number} y
 * @param {boolean} visible
 */
export function showTermPreviewTooltip(text, x, y, visible) {
  const tip = document.getElementById("appTooltip");
  if (!tip) return;

  if (!visible || !text) {
    tip.classList.remove("app-tooltip-visible");
    return;
  }

  const bookFrame = document.getElementById("bookFrame");
  const frameRect = bookFrame ? bookFrame.getBoundingClientRect() : { left: 0, top: 0 };

  const vx = frameRect.left + x;
  const vy = frameRect.top + y;

  tip.textContent = text;

  // Small offset so the tooltip does not sit directly on the hover point.
  const GAP = 12;
  tip.style.left = `${vx + GAP}px`;
  tip.style.top = `${vy - GAP}px`;
  tip.classList.add("app-tooltip-visible");

  requestAnimationFrame(() => {
    const tw = tip.offsetWidth;
    if (vx + GAP + tw > window.innerWidth - 16) {
      tip.style.left = `${vx - tw - GAP}px`;
    }

    const th = tip.offsetHeight;
    if (vy - GAP - th < 8) {
      tip.style.top = `${vy + GAP + 16}px`;
    } else {
      tip.style.top = `${vy - th - GAP}px`;
    }
  });
}
