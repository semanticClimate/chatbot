#!/usr/bin/env bash
# Install or remove the Zoom daily summary LaunchAgent (UTC schedule).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.chatbot.zoom-daily-summary"
PLIST_SRC="${REPO_ROOT}/config/launchd/${LABEL}.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/${LABEL}.plist"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--uninstall]

Install LaunchAgent ${LABEL} to run the watch script daily at (UTC):
  09:30, 11:00, 12:00, 18:00

Logs: /tmp/zoom_summary_watch.log

Requires slack.env configured; passes --require-slack to the watch script.
EOF
}

uninstall_agent() {
  if [[ -f "${PLIST_DST}" ]]; then
    launchctl bootout "gui/$(id -u)" "${PLIST_DST}" 2>/dev/null \
      || launchctl unload "${PLIST_DST}" 2>/dev/null \
      || true
    rm -f "${PLIST_DST}"
    echo "Removed ${PLIST_DST}"
  else
    echo "Not installed: ${PLIST_DST}"
  fi
}

install_agent() {
  if [[ ! -f "${PLIST_SRC}" ]]; then
    echo "Missing plist template: ${PLIST_SRC}" >&2
    exit 1
  fi
  mkdir -p "${HOME}/Library/LaunchAgents"
  sed "s|__REPO_ROOT__|${REPO_ROOT}|g" "${PLIST_SRC}" > "${PLIST_DST}"
  chmod 644 "${PLIST_DST}"

  # bootout/unload first so re-install picks up plist changes
  launchctl bootout "gui/$(id -u)" "${PLIST_DST}" 2>/dev/null \
    || launchctl unload "${PLIST_DST}" 2>/dev/null \
    || true

  if launchctl bootstrap "gui/$(id -u)" "${PLIST_DST}" 2>/dev/null; then
    echo "Loaded with launchctl bootstrap."
  else
    launchctl load "${PLIST_DST}"
    echo "Loaded with launchctl load."
  fi

  echo "Installed ${PLIST_DST}"
  echo "Schedule (UTC): 09:30, 11:00, 12:00, 18:00"
  echo "Test now: ${REPO_ROOT}/scripts/run_zoom_daily_summary_watch.sh --dry-run"
}

case "${1:-}" in
  --uninstall)
    uninstall_agent
    ;;
  -h|--help)
    usage
    ;;
  "")
    install_agent
    ;;
  *)
    echo "Unknown option: $1" >&2
    usage >&2
    exit 1
    ;;
esac
