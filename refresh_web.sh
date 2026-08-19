#!/usr/bin/env bash
# Pull genius-web's own numbers out of the shared GA4 export, then build
# web-events.html.
#
# Why a separate script: this property carries three streams — an iOS app
# (2.09M events), a marketing funnel site (405K) and genius-web (2.5K). Every
# other page here reads the property as a whole, which is the right call for the
# app but makes the web app invisible at 0.1% of the volume. Everything below is
# filtered to the web stream.
#
# Usage: ./refresh_web.sh
set -euo pipefail
cd "$(dirname "$0")"

PROJECT="iip055-genius"
DATASET="analytics_523266340"
STREAM="15350238535"   # genius-web. iOS = 13454223741, funnel site = 15339228736

# Daily tables AND today's intraday, so the newest day is not missing. The
# wildcard matches events_intraday_* too, hence the explicit suffix split.
FROM="\`${PROJECT}.${DATASET}.events_*\` WHERE stream_id='${STREAM}'"

export CLOUDSDK_AUTH_ACCESS_TOKEN="$(gcloud auth application-default print-access-token 2>/dev/null || gcloud auth print-access-token 2>/dev/null)"
if [ -z "${CLOUDSDK_AUTH_ACCESS_TOKEN}" ]; then
  echo "No token. Run:  gcloud auth application-default login" >&2
  exit 1
fi
q() { bq --project_id="$PROJECT" query --use_legacy_sql=false --format=json --max_rows=100000 "$1"; }

echo "[1/4] daily totals…"
q "
SELECT FORMAT_DATE('%Y-%m-%d', PARSE_DATE('%Y%m%d', event_date)) AS d,
       COUNT(*) AS events,
       COUNT(DISTINCT user_pseudo_id) AS users,
       COUNT(DISTINCT CONCAT(user_pseudo_id, CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key='ga_session_id') AS STRING))) AS sessions
FROM ${FROM} GROUP BY d ORDER BY d" > web_daily.json

echo "[2/4] per-event…"
q "
SELECT event_name,
       COUNT(*) AS events,
       COUNT(DISTINCT user_pseudo_id) AS users,
       FORMAT_DATE('%Y-%m-%d', MIN(PARSE_DATE('%Y%m%d', event_date))) AS first_seen,
       FORMAT_DATE('%Y-%m-%d', MAX(PARSE_DATE('%Y%m%d', event_date))) AS last_seen
FROM ${FROM} GROUP BY event_name ORDER BY events DESC" > web_events.json

echo "[3/4] generation health by model…"
q "
WITH g AS (
  SELECT event_name,
         (SELECT value.string_value FROM UNNEST(event_params) WHERE key='model_id') AS model_id,
         (SELECT value.string_value FROM UNNEST(event_params) WHERE key='agent_id') AS agent_id,
         (SELECT value.int_value    FROM UNNEST(event_params) WHERE key='duration_ms') AS ms
  FROM ${FROM} AND event_name IN ('generate_start','generate_success','generate_fail'))
SELECT IFNULL(model_id,'(unknown)') AS model_id, IFNULL(agent_id,'(unknown)') AS agent_id,
       COUNTIF(event_name='generate_start')   AS starts,
       COUNTIF(event_name='generate_success') AS ok,
       COUNTIF(event_name='generate_fail')    AS failed,
       ROUND(APPROX_QUANTILES(ms,100)[OFFSET(50)]/1000,1) AS p50_s,
       ROUND(APPROX_QUANTILES(ms,100)[OFFSET(95)]/1000,1) AS p95_s
FROM g GROUP BY 1,2 ORDER BY starts DESC" > web_models.json

echo "[4/4] session quality…"
q "
SELECT COUNT(DISTINCT user_pseudo_id) AS devices,
       COUNT(DISTINCT user_id) AS identified,
       ANY_VALUE(LENGTH(user_id)) AS user_id_len,
       ROUND(COUNTIF(event_name='page_view')/NULLIF(COUNTIF(event_name='session_start'),0),1) AS pv_per_session
FROM ${FROM}" > web_quality.json

python3 build_web.py
echo "Done → web-events.html"
