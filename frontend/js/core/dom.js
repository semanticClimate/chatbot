/**
 * Shared DOM and URL helpers used by the split frontend modules.
 *
 * Detailed note:
 * - Keeping these helpers in one place avoids repeating the same URL trimming
 *   and DOM lookup code in multiple feature files.
 * - This file has no app-specific state; it only performs small reusable tasks.
 *
 * Simple note:
 * - Small helpers live here.
 */

/**
 * Return an element by id or throw a clear error.
 * This keeps failures explicit during development instead of silently failing.
 * @param {string} id
 * @returns {HTMLElement}
 */
export function $(id) {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing element #${id}`);
  return el;
}

/**
 * Remove trailing slashes from a URL or base string.
 * This is used everywhere the API base is concatenated with endpoint paths.
 * @param {string} baseUrl
 * @returns {string}
 */
export function trimBaseUrl(baseUrl) {
  return String(baseUrl || "").trim().replace(/\/+$/, "");
}

/**
 * Extract the origin from an API base URL.
 * Returns an empty string if the input is not a valid absolute URL.
 * @param {string} base
 * @returns {string}
 */
export function apiOriginFromBase(base) {
  try {
    return new URL(trimBaseUrl(base)).origin;
  } catch {
    return "";
  }
}

/**
 * Trigger a normal browser download from a Blob.
 * Used for CSV exports so the response is saved instead of displayed.
 * @param {Blob} blob
 * @param {string} filename
 */
export function triggerBrowserDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
