#!/usr/bin/env bash
# Refresh the Genius daily event console from BigQuery, then rebuild index.html.
# Usage: ./refresh.sh
set -euo pipefail
cd "$(dirname "$0")"

PROJECT="iip055-genius"
DATASET="analytics_523266340"
TABLE="${PROJECT}.${DATASET}.events_intraday_*"

# bq authenticates from gcloud user creds; this repo uses application-default creds.
export CLOUDSDK_AUTH_ACCESS_TOKEN="$(gcloud auth application-default print-access-token 2>/dev/null)"
if [ -z "${CLOUDSDK_AUTH_ACCESS_TOKEN}" ]; then
  echo "No ADC token. Run:  gcloud auth application-default login" >&2
  exit 1
fi

echo "[1/4] per-event daily aggregates…"
bq --project_id="$PROJECT" query --use_legacy_sql=false --format=json --max_rows=200000 "
SELECT PARSE_DATE('%Y%m%d', event_date) AS d, event_name,
  COUNT(*) AS events, COUNT(DISTINCT user_pseudo_id) AS users
FROM \`${TABLE}\`
GROUP BY d, event_name ORDER BY d, event_name" > per_event.json

echo "[2/4] daily totals…"
bq --project_id="$PROJECT" query --use_legacy_sql=false --format=json --max_rows=200000 "
SELECT PARSE_DATE('%Y%m%d', event_date) AS d,
  COUNT(DISTINCT user_pseudo_id) AS dau,
  COUNT(DISTINCT IF(event_name='first_open', user_pseudo_id, NULL)) AS new_users,
  COUNT(DISTINCT CONCAT(user_pseudo_id, CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key='ga_session_id') AS STRING))) AS sessions,
  COUNT(*) AS total_events
FROM \`${TABLE}\`
GROUP BY d ORDER BY d" > daily_totals.json

echo "[3/4] per-feature funnel (Drop Rate by Cutoff)…"
python3 -c "
import funnels
cols=funnels.sql_columns()
col_sql=',\n  '.join(f'{e} AS {n}' for n,e in cols.items())
print(f'''WITH base AS (
  SELECT PARSE_DATE('%Y%m%d', event_date) AS d, user_pseudo_id AS uid, event_name AS ev,
         (SELECT value.string_value FROM UNNEST(event_params) WHERE key='feature_name') AS fname
  FROM \`${TABLE}\`
)
SELECT FORMAT_DATE('%Y-%m-%d', d) AS d, COUNT(DISTINCT uid) AS user_active,
  {col_sql}
FROM base GROUP BY ROLLUP(d) ORDER BY d''')
" > funnel_query.sql
bq --project_id="$PROJECT" query --use_legacy_sql=false --format=json --max_rows=5000 "$(cat funnel_query.sql)" > funnel_data.json

echo "[4/4] building dashboards…"
python3 build.py
python3 build_droprate.py
echo "Done. Open index.html (console) or drop-rate.html (funnel tables)"
