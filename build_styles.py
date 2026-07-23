#!/usr/bin/env python3
"""Build styles.html — per-style usage table for Genius (iip055).

Metrics per style (all carry the GA4 `style` param): Click (home_style_click),
Generate (service_request), Response (service_response), Result (*_result_view),
Paywall (iap_view), Users (distinct on generate). Purchase is excluded —
iap_successful carries no style.

Layout: one row per style (ranked by generate), a Total/day <select> switches the
scope (counts + distinct users precomputed per scope via ROLLUP so distinct users
stay correct). Reads GA4 from events_intraday_* (ADC). Writes styles.html; NOT pushed.
"""
import os
import sys
import json
import datetime

os.environ.setdefault("PYTHONWARNINGS", "ignore")
from google.cloud import bigquery

# shared 5-page nav
sys.path.insert(0, os.path.expanduser("~/po-thinhdd/_shared/.claude/skills/cancel-revenue"))
from nav import nav_html  # noqa: E402

PROJECT = "iip055-genius"
TABLE = f"{PROJECT}.analytics_523266340.events_intraday_*"
HERE = os.path.dirname(os.path.abspath(__file__))

SQL = f"""
WITH base AS (
  SELECT
    PARSE_DATE('%Y%m%d', event_date) AS d,
    user_pseudo_id AS uid,
    event_name AS ev,
    TRIM(REPLACE((SELECT value.string_value FROM UNNEST(event_params) WHERE key='style'),
                 'Style Name:', '')) AS style,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key='feature_name') AS feat
  FROM `{TABLE}`
  WHERE (SELECT value.string_value FROM UNNEST(event_params) WHERE key='style') IS NOT NULL
)
SELECT
  style,
  ANY_VALUE(feat) AS feat,
  FORMAT_DATE('%Y-%m-%d', d) AS day,       -- NULL row = per-style total (ROLLUP)
  COUNTIF(ev='home_style_click') AS clicks,
  COUNTIF(ev='service_request')  AS generates,
  COUNTIF(ev='service_response') AS responses,
  COUNTIF(ev LIKE '%result_view') AS results,
  COUNTIF(ev='iap_view')         AS paywalls,
  COUNT(DISTINCT IF(ev='service_request', uid, NULL)) AS gen_users
FROM base
WHERE style IS NOT NULL AND style NOT IN ('', '(none)', '(empty)')
GROUP BY ROLLUP(style, day)
"""


def build():
    bq = bigquery.Client(project=PROJECT)
    styles = {}   # style -> {feat, tot:{}, day:{d:{}}}
    days = set()
    for r in bq.query(SQL).result():
        if r.style is None:      # ROLLUP grand-total row (all styles) — skip
            continue
        rec = {"c": r.clicks, "g": r.generates, "rs": r.responses,
               "rv": r.results, "p": r.paywalls, "u": r.gen_users}
        s = styles.setdefault(r.style, {"feat": r.feat, "tot": None, "day": {}})
        if r.day is None:
            s["tot"] = rec
        else:
            s["day"][r.day] = rec
            days.add(r.day)

    days = sorted(days, reverse=True)
    # embed: sorted by total generates desc
    slist = sorted(styles.items(), key=lambda kv: (kv[1]["tot"] or {}).get("g", 0), reverse=True)
    data = {"days": days, "styles": [
        {"s": k, "feat": v["feat"] or "", "tot": v["tot"] or {"c": 0, "g": 0, "rs": 0, "rv": 0, "p": 0, "u": 0},
         "day": v["day"]}
        for k, v in slist
    ]}

    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""<!doctype html>
<html lang="vi"><head>
<meta charset="utf-8"><title>Genius · Styles</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root{{--bg:#EEF1F6;--card:#FFF;--ink:#1B2530;--muted:#5C6A7A;--faint:#94A1B2;
    --line:#E2E7EF;--line2:#EDF0F5;--accent:#1A73E8;--blue:#3C82F6;
    --mono:ui-monospace,"SF Mono",Menlo,monospace;--sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}}
  *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:13px}}
  .wrap{{max-width:1280px;margin:0 auto;padding:22px 18px 60px}}
  header{{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:16px}}
  h1{{font-size:19px;font-weight:700;margin:0;display:flex;align-items:center;gap:9px}}
  h1 .pip{{width:10px;height:10px;border-radius:50%;background:var(--accent)}} h1 span{{color:var(--muted);font-weight:500}}
  .meta{{font-family:var(--mono);font-size:11px;color:var(--faint);text-align:right;line-height:1.7}}
  .card{{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:0 1px 2px rgba(16,24,40,.04);margin-bottom:16px}}
  .card-head{{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px;padding:15px 18px 12px}}
  .card-head h2{{font-size:15px;font-weight:700;margin:0}}
  select{{font-family:var(--mono);font-size:12px;padding:6px 10px;border:1px solid var(--line);border-radius:9px;background:#fff;color:var(--ink)}}
  .scroll{{overflow-x:auto}}
  table{{border-collapse:separate;border-spacing:0;width:100%;font-variant-numeric:tabular-nums}}
  th,td{{padding:7px 12px;text-align:right;white-space:nowrap;font-family:var(--mono);font-size:12px}}
  thead th{{position:sticky;top:0;background:#F7F9FC;color:var(--muted);font-weight:700;font-size:10.5px;border-bottom:2px solid var(--line);font-family:var(--sans)}}
  tbody td{{border-bottom:1px solid var(--line2)}}
  th.s0,td.s0{{position:sticky;left:0;background:#fff;text-align:left;font-family:var(--sans);font-weight:600;max-width:280px;overflow:hidden;text-overflow:ellipsis}}
  td.rank{{color:var(--faint);text-align:right;width:34px}}
  td.feat{{font-family:var(--sans);color:var(--muted);text-align:left}}
  td.g{{color:var(--accent);font-weight:700}}
  tbody tr:hover td{{background:#F3F7FF}} tbody tr:hover td.s0{{background:#F3F7FF}}
  tfoot td{{font-weight:700;border-top:2px solid var(--line);background:#FBFCFE}}
  .heat{{position:absolute;left:0;top:4px;bottom:4px;background:rgba(60,130,246,.16);border-radius:4px;z-index:0}}
  td.hc{{position:relative}} td.hc span{{position:relative;z-index:1}}
  .note{{font-family:var(--mono);font-size:11px;color:var(--faint);padding:0 18px 16px;line-height:1.7}}
</style></head>
<body><div class="wrap">
  {nav_html('styles')}
  <header>
    <h1><span class="pip"></span>Genius <span>· Styles — mức độ sử dụng</span></h1>
    <div class="meta"><div>Generated {generated}</div><div id="scopeinfo"></div></div>
  </header>
  <div class="card">
    <div class="card-head">
      <h2>Style dùng nhiều nhất</h2>
      <label>Kỳ: <select id="scope"></select></label>
    </div>
    <div class="scroll"><table>
      <thead><tr>
        <th class="s0" style="text-align:left">#  Style</th>
        <th class="s0" style="left:0;position:static;text-align:left">Feature</th>
        <th class="grp">Click</th><th class="grp">Generate</th><th class="grp">Response</th>
        <th class="grp">Result</th><th class="grp">Paywall</th><th class="grp">Users</th>
      </tr></thead>
      <tbody id="tb"></tbody><tfoot id="tf"></tfoot>
    </table></div>
    <div class="note">Sắp theo Generate (service_request). Metrics đều gắn GA4 param <code>style</code> · Users = distinct theo Generate · chọn "Tổng" hoặc 1 ngày ở góc phải · nguồn events_intraday_* (GA4)</div>
  </div>
<script>
  var D = {json.dumps(data, separators=(',',':'))};
  var sel = document.getElementById('scope');
  sel.innerHTML = '<option value="__total__">Tổng (all)</option>' + D.days.map(function(d){{return '<option value="'+d+'">'+d+'</option>';}}).join('');
  var COLS = ['c','g','rs','rv','p','u'];
  function nf(x){{return (x||0).toLocaleString('en-US');}}
  function render(scope){{
    var rows = D.styles.map(function(st){{
      var m = scope==='__total__' ? st.tot : (st.day[scope] || {{}});
      return {{s:st.s, feat:st.feat, m:m}};
    }}).filter(function(r){{ return (r.m.g||0)+(r.m.c||0)+(r.m.rs||0)+(r.m.rv||0)+(r.m.p||0) > 0; }});
    rows.sort(function(a,b){{ return (b.m.g||0)-(a.m.g||0); }});
    var maxg = Math.max(1, rows.length?rows[0].m.g||0:0);
    var T={{c:0,g:0,rs:0,rv:0,p:0,u:0}};
    var html = rows.map(function(r,i){{
      COLS.forEach(function(k){{T[k]+=r.m[k]||0;}});
      var w=(100*(r.m.g||0)/maxg).toFixed(1);
      return '<tr><td class="s0"><span style="color:var(--faint)">'+(i+1)+'.</span> '+r.s+'</td>'+
        '<td class="feat">'+r.feat+'</td>'+
        '<td>'+nf(r.m.c)+'</td>'+
        '<td class="g hc"><span class="heat" style="width:'+w+'%"></span><span>'+nf(r.m.g)+'</span></td>'+
        '<td>'+nf(r.m.rs)+'</td><td>'+nf(r.m.rv)+'</td><td>'+nf(r.m.p)+'</td><td>'+nf(r.m.u)+'</td></tr>';
    }}).join('');
    document.getElementById('tb').innerHTML = html || '<tr><td class="s0">Không có dữ liệu</td><td colspan="7"></td></tr>';
    document.getElementById('tf').innerHTML = '<tr><td class="s0">Σ '+rows.length+' styles</td><td></td>'+
      '<td>'+nf(T.c)+'</td><td>'+nf(T.g)+'</td><td>'+nf(T.rs)+'</td><td>'+nf(T.rv)+'</td><td>'+nf(T.p)+'</td><td>'+(scope==='__total__'?'—':nf(T.u))+'</td></tr>';
    document.getElementById('scopeinfo').textContent = (scope==='__total__'?'Tổng':scope)+' · '+rows.length+' styles';
  }}
  sel.addEventListener('change', function(){{ render(sel.value); }});
  render('__total__');
</script>
</div></body></html>"""
    out = os.path.join(HERE, "styles.html")
    open(out, "w").write(html)
    print(f"wrote {out} | {len(data['styles'])} styles, {len(days)} days")


if __name__ == "__main__":
    build()
