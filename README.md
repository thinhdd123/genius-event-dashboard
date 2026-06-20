# Genius · Daily Event Console

A self-contained web dashboard to read daily GA4 numbers for the **Genius** app
(BigQuery project `iip055-genius`, dataset `analytics_523266340`). Built from the
event spec sheet + the live GA4 export. Replaces the Looker Studio daily report.

## What it shows

- **KPI cards** (selected window vs previous equal window): Avg DAU, New users,
  Sessions, Total events, Generations (`service_request`), Paywall views (`iap_view`),
  Purchases (`iap_successful`), Purchase CVR.
- **Daily trend** — full 102-day line chart with the selected window shaded. Toggle
  DAU / New users / Sessions / Events, and click any event row to overlay its daily line.
- **Product funnel** — Splash → Onboarding complete → Home → Generate request →
  Generate response → Paywall → Purchase, scaled to the largest step.
- **Event explorer** — all 232 tracked events grouped by feature (Splash, Onboarding,
  Paywall, Home, Enhance, I2I, I2V, Seedance, Try-on, World Cup Looks/Video, Service
  Quality, App/Auto). Search, group filter, sortable, per-event sparklines + Δ vs prev.

The window selector (7D / 14D / 28D / All) drives the KPIs, funnel, and table.

## Drop Rate by Cutoff — `drop-rate.html`

Per-feature daily funnel tables (Looker-style, blue heatmap), one tab per feature:
**Enhance, I2I, I2V, Try-on Jersey, World Cup Looks, World Cup Video**. Each row is a
day (newest first); columns are that feature's funnel steps with a count + a `%` of
User Active (DAU). A **Tổng cộng** row shows period-distinct users.

- Each cell = **distinct users** who reached that step that day.
- Shared steps are split by `feature_name` (`iap_view`, `service_request`,
  `home_style_click`); `home_view` is global (not feature-tagged in GA4).
- Deep-link a tab with `?f=enhance|i2i|i2v|tryon|wclooks|wcvideo`.

## Drop Rate with live filters — `serve.py` / `drop-rate-live.html`

Multi-dimension filters can't be precomputed into a static file (distinct-user
counts aren't additive across dimensions), so this page queries BigQuery **live**,
like Looker Studio. Run the local server:

```bash
./serve.sh            # starts on http://127.0.0.1:8799 and opens the browser
```

Filter bar (mirrors the requested layout):

| Filter | Status | Source |
|---|---|---|
| Date range | ✅ works | `_TABLE_SUFFIX` |
| **app_version** | ✅ works | `app_info.version` |
| **country** | ✅ works | `geo.country` |
| **_network_name_** | ✅ works | `utm_source` on `app_install_referrer` (per-user install attribution) |
| _campaign_name_ / adj_adgroup_name | ⛔ disabled | Adjust tokens unresolved in data (`{{campaign.name}}`) |
| creative_id | ⛔ disabled | empty in GA4 export |
| User Subscription Type / Cancellation Status | ⛔ disabled | not in GA4 — lives in RevenueCat/payment data |
| Day Retention | ⛔ disabled | a cohort metric, not a filter dimension |

Disabled filters are shown (dashed) so the layout matches the request; hover for why.
Each filter change re-runs one BigQuery query (~80 MB, a few cents).

> This page needs the running server — it can't be a hosted Artifact (the Artifact
> sandbox can't reach a localhost API). The two static pages below *can* be shared.

## Open the static pages

Open `index.html` (console) or `drop-rate.html` (funnel tables) in a browser —
all data is embedded, no server needed. The pages link to each other.

## Refresh with the latest BigQuery data

```bash
./refresh.sh
```

This re-runs two BigQuery queries (≈78 MB scanned, a few cents) and rebuilds
`index.html`. It needs Google application-default credentials:

```bash
gcloud auth application-default login    # one-time, if the token has expired
```

### Daily auto-refresh (optional)

Add a cron entry (macOS) to rebuild every morning at 09:00:

```
0 9 * * *  cd /Users/daothinh/artimind-kb/po/thinhdd/genius/event-dashboard && ./refresh.sh >> refresh.log 2>&1
```

## Files

| File | Purpose |
|---|---|
| `index.html` | Event console — open this. Data is embedded. |
| `drop-rate.html` | Per-feature funnel tables (static). Data is embedded. |
| `drop-rate-live.html` + `serve.py` + `serve.sh` | Live-filter funnel page + local query server. |
| `template.html` / `droprate.template.html` | Templates with a `__DATA_PLACEHOLDER__` slot. |
| `build.py` / `build_droprate.py` | Pivot JSON exports → inject into the templates. |
| `funnels.py` | Per-feature funnel step definitions + SQL column generator (shared by build + server). |
| `refresh.sh` | Pulls all data from BigQuery and rebuilds both static pages. |
| `per_event.json` / `daily_totals.json` / `funnel_data.json` | Raw BigQuery aggregates. |

## Notes

- GA4 here is **streaming-only export** (`events_intraday_*`, no finalized
  `events_*` tables), so the very latest day is partial and updates through the day.
- A few event names in the data differ slightly from the spec: `iap_successful`
  (spec: `iap_successfull`), `service_response` (spec also notes the typo
  `service_reponse`). The dashboard uses the names as they appear in BigQuery.
- `showcase_flow_1_complete` never fires in the data; the funnel uses
  `showcase_6_flow_1_complete` (last onboarding slide) as the completion step.
