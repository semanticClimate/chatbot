#!/usr/bin/env bash
# launchd wrapper for zoom_daily_summary_watch.py (macOS).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="${REPO_ROOT}/climate_streamlit"
VENV_ACTIVATE="${APP_DIR}/venv/bin/activate"

export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"

SLACK_ENV="${REPO_ROOT}/config/zoom_daily_summary/slack.env"
if [[ -f "${SLACK_ENV}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${SLACK_ENV}"
  set +a
fi

# Upload all files in each Zoom session folder (transcript, chat, audio, video, …).
# Set to 0 in slack.env to upload only summary + transcript. Override in slack.json.
export ZOOM_SLACK_UPLOAD_ALL_SESSION_FILES="${ZOOM_SLACK_UPLOAD_ALL_SESSION_FILES:-1}"

# Large video files may need a longer HTTP timeout (seconds).
export ZOOM_SLACK_TIMEOUT_S="${ZOOM_SLACK_TIMEOUT_S:-600}"

WATCH_ARGS=()
if [[ "${ZOOM_SLACK_UPLOAD_ALL_SESSION_FILES}" =~ ^(1|true|yes|on)$ ]]; then
  WATCH_ARGS+=(--slack-upload-all-session-files)
else
  WATCH_ARGS+=(--no-slack-upload-all-session-files)
fi
WATCH_ARGS+=(--slack-timeout-s "${ZOOM_SLACK_TIMEOUT_S}")

if [[ -f "${VENV_ACTIVATE}" ]]; then
  # shellcheck disable=SC1090
  source "${VENV_ACTIVATE}"
fi

cd "${APP_DIR}"
exec python zoom_daily_summary_watch.py "${WATCH_ARGS[@]}" "$@"
