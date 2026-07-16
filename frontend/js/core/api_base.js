/**
 * API base resolution and persistence helpers.
 *
 * Detailed note:
 * - This module isolates all "where is the backend?" logic.
 * - The goal is to keep tunnel detection, saved settings, and local-dev fallback
 *   in one place so the UI layer stays simpler.
 *
 * Simple note:
 * - API base logic lives here.
 */

import { setStatus } from "../ui/render.js";
import { t } from "../ui/ui_strings.js";
import { trimBaseUrl } from "./dom.js";

export const STORAGE_KEY_API = "climate_web_client_api_base";

/**
 * Empty default: quick-tunnel run fills web_client/tunnel-api-base.txt.
 * Keeping this constant here makes the fallback behavior easy to audit.
 */
export const DEFAULT_API_BASE = "";

function normalizedDefaultApiBase() {
  return trimBaseUrl(DEFAULT_API_BASE);
}

/**
 * True when the page is served from a public tunnel hostname instead of local dev.
 * @returns {boolean}
 */
export function isRemoteWebOrigin() {
  const h = window.location.hostname;
  if (!h) return false;
  return h !== "localhost" && h !== "127.0.0.1";
}

/**
 * True when an API URL points at localhost / loopback.
 * @param {string} raw
 * @returns {boolean}
 */
export function isLoopbackApiBase(raw) {
  try {
    const u = new URL(String(raw || "").trim());
    return u.hostname === "127.0.0.1" || u.hostname === "localhost";
  } catch {
    return false;
  }
}

/**
 * Accept only absolute http(s) URLs.
 * Paths like /Users/... are not valid API base URLs and would break POST requests.
 * @param {string} raw
 * @returns {boolean}
 */
export function isAcceptableApiBase(raw) {
  const s = String(raw || "").trim();
  if (!s) return false;
  try {
    const u = new URL(s);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

/**
 * Local-dev fallback if no saved value and no tunnel hint are available.
 * Public tunnel pages prefer an empty default so we do not accidentally point
 * a remote browser at localhost.
 * @returns {string}
 */
export function fallbackApiBase() {
  if (isRemoteWebOrigin()) return "";
  return DEFAULT_API_BASE || "http://127.0.0.1:8800";
}

/**
 * Read the persisted API base URL.
 * @returns {string}
 */
export function loadApiBase() {
  try {
    return localStorage.getItem(STORAGE_KEY_API) || "";
  } catch {
    return "";
  }
}

/**
 * Persist the API base URL.
 * @param {string} url
 */
export function saveApiBase(url) {
  try {
    localStorage.setItem(STORAGE_KEY_API, url.trim());
  } catch {
    /* ignore quota / privacy mode failures */
  }
}

/**
 * Try to read the tunnel hint file written by the quick-tunnel script.
 * @returns {Promise<string>}
 */
export async function fetchTunnelHintApiBase() {
  const attempt = async () => {
    try {
      const u = new URL("tunnel-api-base.txt", window.location.href);
      if (isRemoteWebOrigin()) {
        u.searchParams.set("cb", String(Date.now()));
      }
      const res = await fetch(u, { cache: "no-store" });
      if (!res.ok) return "";
      const text = (await res.text()).trim();
      return isAcceptableApiBase(text) ? text : "";
    } catch {
      return "";
    }
  };

  let hint = await attempt();
  if (!hint && isRemoteWebOrigin()) {
    await new Promise((r) => setTimeout(r, 450));
    hint = await attempt();
  }
  return hint;
}

/**
 * Resolve the startup API base by combining:
 * - saved user preference
 * - tunnel hint file
 * - local-dev fallback
 *
 * @param {HTMLElement} statusLine
 * @returns {Promise<string>}
 */
export async function resolveInitialApiBase(statusLine) {
  const stored = loadApiBase();
  const hinted = await fetchTunnelHintApiBase();

  if (stored && !isAcceptableApiBase(stored)) {
    saveApiBase("");
    const v = hinted || fallbackApiBase();
    const parts = [t("errApiBaseInvalidSaved")];
    if (!v && isRemoteWebOrigin()) {
      parts.push(t("errTunnelNotFound"));
    }
    setStatus(statusLine, parts.join(" "), "error");
    return v;
  }

  const storedTrim = stored ? trimBaseUrl(stored) : "";
  const storedIsDefaultLocal = storedTrim === normalizedDefaultApiBase();

  if (stored) {
    if (hinted) {
      if (isRemoteWebOrigin()) {
        if (isLoopbackApiBase(stored) || storedIsDefaultLocal) {
          saveApiBase(hinted);
          return hinted;
        }
        return stored;
      }
      if (storedIsDefaultLocal) {
        saveApiBase(hinted);
        return hinted;
      }
      return stored;
    }
    return stored;
  }

  const out = hinted || fallbackApiBase();
  if (!out && isRemoteWebOrigin()) {
    setStatus(statusLine, t("errTunnelBaseNotFound"), "error");
  }
  return out;
}
