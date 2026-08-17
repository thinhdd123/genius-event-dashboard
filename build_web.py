#!/usr/bin/env python3
"""Build web-events.html — genius-web's slice of the shared GA4 property.

The other pages here read the property whole, which is right for the iOS app but
buries the web app at 0.1% of the volume. Everything here is the web stream only.

The page also carries something BigQuery alone cannot show: which events the app
DECLARES it can send. An event that has never fired is either a feature nobody
reached or an instrumentation gap, and those two look identical in a query — so
the declared list is checked in here and diffed against what arrived.
"""
import json, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
load = lambda n: json.load(open(os.path.join(HERE, n)))

daily   = load("web_daily.json")
events  = load("web_events.json")
models  = load("web_models.json")
quality = (load("web_quality.json") or [{}])[0]

# Declared in src/services/analytics/AnalyticsService.ts. Kept here rather than
# derived, so this page still says something true when run away from the repo.
DECLARED = [
    "page_view", "login", "sign_up", "auth_fail", "logout",
    "generate_start", "generate_success", "generate_fail", "generate_partial",
    "result_download", "template_select", "model_select", "pricing_view",
    "paywall_open", "select_plan", "begin_checkout", "purchase", "checkout_fail",
    "credit_spend", "ui_click", "app_error", "web_vitals",
]
# GA4 sends these itself; their absence from the declared list is not a gap.
AUTOMATIC = {"session_start", "first_visit", "user_engagement", "scroll", "click"}

# Declared in code but not yet in the build that production serves. A zero here
# means "not deployed", which is a different thing from "nobody did it" — and the
# query cannot tell them apart, so the distinction is recorded rather than
# inferred. Drop a name from this set once the release carrying it ships.
NOT_YET_DEPLOYED = {"model_select", "pricing_view", "credit_spend"}

seen = {e["event_name"]: e for e in events}
fired  = [n for n in DECLARED if n in seen]
silent = [n for n in DECLARED if n not in seen]

def i(v, d=0):
    try: return int(v)
    except (TypeError, ValueError): return d

total_events = sum(i(r["events"]) for r in daily)
total_users  = max([i(r["users"]) for r in daily], default=0)
days = [r["d"] for r in daily]

# Two journeys, not one. Choosing a plan is not the step after getting a result —
# someone can reach the prices from the nav without ever generating anything, and
# treating them as one chain produced ratios over 100%, which is a made-up
# relationship dressed as a conversion rate. Each list below IS sequential, so
# "% of the previous step" means something inside it.
FUNNELS = [
    ("Dùng sản phẩm", [
        ("page_view",        "Mở trang"),
        ("login",            "Đăng nhập"),
        ("generate_start",   "Bấm tạo"),
        ("generate_success", "Có kết quả"),
    ]),
    ("Trả tiền", [
        ("pricing_view",     "Xem bảng giá"),
        ("select_plan",      "Chọn gói"),
        ("begin_checkout",   "Mở thanh toán"),
        ("purchase",         "Trả tiền"),
    ]),
]
funnels = [
    {"title": t, "steps": [{"ev": ev, "label": lb,
                            "users": i(seen.get(ev, {}).get("users")),
                            "pending": ev in NOT_YET_DEPLOYED and ev not in seen}
                           for ev, lb in steps]}
    for t, steps in FUNNELS
]

blob = {
    "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    "daily": daily, "events": events, "models": models,
    "funnels": funnels, "silent": silent, "fired": fired,
    "pending": sorted(NOT_YET_DEPLOYED - set(seen)),
    "declared_n": len(DECLARED),
    "quality": quality,
    "totals": {"events": total_events, "users": total_users,
               "days": len(days), "from": days[0] if days else "—", "to": days[-1] if days else "—"},
}

TPL = open(os.path.join(HERE, "web.template.html")).read()
out = TPL.replace("/*__DATA__*/", json.dumps(blob, ensure_ascii=False))
open(os.path.join(HERE, "web-events.html"), "w").write(out)
print(f"web-events.html · {total_events:,} events · {len(fired)}/{len(DECLARED)} declared events fired")
