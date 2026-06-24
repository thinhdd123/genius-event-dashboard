#!/usr/bin/env bash
# Daily one-command update: pull latest BigQuery numbers, rebuild the pages,
# commit, and push so GitHub Pages updates.
#
#   ./update-web.sh
#
# Needs: gcloud application-default creds (for BigQuery) + gh/git auth (for push).
# If BigQuery auth has expired, run once:  gcloud auth application-default login
set -euo pipefail
cd "$(dirname "$0")"

echo "▶ Pulling latest numbers from BigQuery + rebuilding…"
./refresh.sh

if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "✓ No changes — pages already up to date."
  exit 0
fi

git add -A
git commit -q -m "Daily refresh $(date +%Y-%m-%d)"
echo "▶ Pushing to GitHub…"
git push -q

echo "✓ Done. Pages will refresh in ~1 min:"
echo "  https://thinhdd123.github.io/genius-event-dashboard/            (console)"
echo "  https://thinhdd123.github.io/genius-event-dashboard/drop-rate.html  (funnel tables)"
