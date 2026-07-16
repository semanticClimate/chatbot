/**
 * Client-side conversation state (mirrors API payload shape where possible).
 */

/** @type {object[]} */
let conversation = [];

export function getConversation() {
  return conversation;
}

export function setConversation(next) {
  conversation = Array.isArray(next) ? next.slice() : [];
}

/** Reset to empty API conversation. */
export function clearConversation() {
  conversation = [];
}

/**
 * After a successful /ask, server returns conversation_full — use that as source of truth.
 * @param {object[]|undefined} full
 */
export function applyConversationFull(full) {
  if (Array.isArray(full)) {
    conversation = full.slice();
  }
}
