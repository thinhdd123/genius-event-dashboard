#!/usr/bin/env bash
# Launch the live-filter Drop Rate server (queries BigQuery on demand).
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-8799}"

if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
  echo "No ADC token. Run:  gcloud auth application-default login" >&2
  exit 1
fi

URL="http://127.0.0.1:${PORT}/"
( sleep 1; command -v open >/dev/null && open "$URL" ) &   # auto-open browser (macOS)
echo "Opening $URL"
exec python3 serve.py "$PORT"
