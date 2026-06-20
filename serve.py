#!/usr/bin/env python3
"""Local query server for the filtered Drop Rate by Cutoff page.

Runs BigQuery live per filter selection (like Looker Studio) — multi-dimension
filter combos can't be precomputed into a static file. Binds to 127.0.0.1 only.

Run:  ./serve.sh   (or:  python3 serve.py [port])
Then open http://127.0.0.1:8799/
"""
import http.server, socketserver, subprocess, json, re, os, sys, urllib.parse

HERE    = os.path.dirname(os.path.abspath(__file__))
PROJECT = "iip055-genius"
TABLE   = "iip055-genius.analytics_523266340.events_intraday_*"
PORT    = int(sys.argv[1]) if len(sys.argv) > 1 else 8799
sys.path.insert(0, HERE)
import funnels

_token = None
def token():
    global _token
    if not _token:
        _token = subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token"],
            text=True).strip()
    return _token

def run_bq(sql):
    """Run a query via the bq CLI using the ADC token; return parsed JSON rows."""
    env = dict(os.environ, CLOUDSDK_AUTH_ACCESS_TOKEN=token())
    p = subprocess.run(
        ["bq", f"--project_id={PROJECT}", "query", "--use_legacy_sql=false",
         "--format=json", "--max_rows=5000", "--quiet", sql],
        capture_output=True, text=True, env=env)
    if p.returncode != 0:
        # token may have expired — clear and retry once
        global _token
        if "credential" in p.stderr.lower() or "token" in p.stderr.lower():
            _token = None
            env = dict(os.environ, CLOUDSDK_AUTH_ACCESS_TOKEN=token())
            p = subprocess.run(
                ["bq", f"--project_id={PROJECT}", "query", "--use_legacy_sql=false",
                 "--format=json", "--max_rows=5000", "--quiet", sql],
                capture_output=True, text=True, env=env)
        if p.returncode != 0:
            raise RuntimeError(p.stderr[-800:])
    return json.loads(p.stdout or "[]")

# ---- sanitization ----
def q(v):                                   # safe SQL string literal
    return "'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'"
def datestamp(s, default):
    return s if re.fullmatch(r"\d{8}", s or "") else default
def vals(s):                                # CSV multi-value param -> clean list
    return [v for v in (s or "").split(",") if v.strip()]

def funnel_sql(frm, to, versions, countries, sources):
    cols = funnels.sql_columns()
    col_sql = ",\n  ".join(f"{e} AS {n}" for n, e in cols.items())
    where = [f"_TABLE_SUFFIX BETWEEN '{frm}' AND '{to}'"]
    if versions:  where.append("app_info.version IN (" + ",".join(q(v) for v in versions) + ")")
    if countries: where.append("geo.country IN (" + ",".join(q(c) for c in countries) + ")")
    src_filter = ""
    if sources:
        src_in = ",".join(q(s) for s in sources)
        src_filter = (f"WHERE uid IN (SELECT user_pseudo_id FROM `{TABLE}` "
                      f"WHERE event_name='app_install_referrer' AND "
                      f"(SELECT value.string_value FROM UNNEST(event_params) WHERE key='utm_source') "
                      f"IN ({src_in}))")
    return f"""WITH base AS (
  SELECT PARSE_DATE('%Y%m%d', event_date) AS d, user_pseudo_id AS uid, event_name AS ev,
         (SELECT value.string_value FROM UNNEST(event_params) WHERE key='feature_name') AS fname
  FROM `{TABLE}`
  WHERE {' AND '.join(where)}
),
filtered AS (SELECT * FROM base {src_filter})
SELECT FORMAT_DATE('%Y-%m-%d', d) AS d, COUNT(DISTINCT uid) AS user_active,
  {col_sql}
FROM filtered GROUP BY ROLLUP(d) ORDER BY d"""

def filters_sql():
    return f"""
SELECT 'version' AS typ, app_info.version AS val, COUNT(DISTINCT user_pseudo_id) AS u
FROM `{TABLE}` WHERE app_info.version IS NOT NULL GROUP BY val
UNION ALL
SELECT 'country', geo.country, COUNT(DISTINCT user_pseudo_id)
FROM `{TABLE}` WHERE geo.country IS NOT NULL GROUP BY geo.country
UNION ALL
SELECT 'source', (SELECT value.string_value FROM UNNEST(event_params) WHERE key='utm_source'),
       COUNT(DISTINCT user_pseudo_id)
FROM `{TABLE}` WHERE event_name='app_install_referrer' GROUP BY 2
ORDER BY typ, u DESC"""

def daterange_sql():
    return (f"SELECT MIN(event_date) AS lo, MAX(event_date) AS hi "
            f"FROM `{TABLE}`")

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(u.query)
        g = lambda k, d="": (qs.get(k, [d])[0])
        try:
            if u.path in ("/", "/index.html", "/drop-rate-live.html"):
                with open(os.path.join(HERE, "drop-rate-live.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if u.path == "/api/spec":
                feat = {fid: {"label": f["label"],
                              "steps": [[f"{fid}__{k}", lab] for k, lab, ev, ff in f["steps"]]}
                        for fid, f in funnels.FEATURES.items()}
                return self._send(200, json.dumps(feat))
            if u.path == "/api/filters":
                rows = run_bq(filters_sql())
                out = {"version": [], "country": [], "source": []}
                for r in rows:
                    if r["val"]: out[r["typ"]].append({"v": r["val"], "u": int(r["u"])})
                dr = run_bq(daterange_sql())[0]
                out["range"] = {"lo": dr["lo"], "hi": dr["hi"]}
                return self._send(200, json.dumps(out))
            if u.path == "/api/funnel":
                lo, hi = "20260310", "20260620"
                frm = datestamp(g("from"), lo); to = datestamp(g("to"), hi)
                sql = funnel_sql(frm, to, vals(g("version")), vals(g("country")), vals(g("source")))
                rows = run_bq(sql)
                daily, total = [], {}
                for r in rows:
                    row = {k: (int(v) if v not in (None, "") else 0) for k, v in r.items() if k != "d"}
                    if r.get("d"): row["d"] = r["d"]; daily.append(row)
                    else: total = row
                daily.sort(key=lambda x: x["d"], reverse=True)
                return self._send(200, json.dumps({"daily": daily, "total": total}))
            self._send(404, json.dumps({"error": "not found"}))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))

if __name__ == "__main__":
    # build the static funnel-step spec the page needs, written next to it
    feat = {fid: {"label": f["label"],
                  "steps": [[f"{fid}__{k}", lab] for k, lab, ev, ff in f["steps"]]}
            for fid, f in funnels.FEATURES.items()}
    with open(os.path.join(HERE, "funnel_spec.json"), "w") as fp:
        json.dump(feat, fp)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), H) as httpd:
        print(f"Drop Rate (live filters) → http://127.0.0.1:{PORT}/")
        print("Ctrl+C to stop.")
        try: httpd.serve_forever()
        except KeyboardInterrupt: print("\nstopped.")
