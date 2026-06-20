#!/usr/bin/env python3
"""Build the Genius daily event console: pivot BQ JSON exports into a compact
data blob and inject it into the dashboard HTML template."""
import json, os, datetime, re

HERE = os.path.dirname(os.path.abspath(__file__))

def load(name):
    with open(os.path.join(HERE, name)) as f:
        return json.load(f)

per_event = load("per_event.json")      # [{d, event_name, events, users}]
totals    = load("daily_totals.json")   # [{d, dau, new_users, sessions, total_events}]

# ---- ordered day axis ----
days = sorted({r["d"] for r in totals})
day_idx = {d: i for i, d in enumerate(days)}
N = len(days)

# ---- feature grouping from the event spec taxonomy ----
GROUPS = [
    ("splash",     "Splash & ATT"),
    ("onboarding", "Onboarding"),
    ("paywall",    "Paywall & IAP"),
    ("home",       "Home & Settings"),
    ("enhance",    "Enhance"),
    ("i2i",        "Image → Image"),
    ("i2v",        "Image → Video"),
    ("seedance2",  "Seedance"),
    ("tryon",      "Try-on Jersey"),
    ("wclooks",    "World Cup Looks"),
    ("wcvideo",    "World Cup Video"),
    ("service",    "Service Quality"),
    ("auto",       "App / Automatic"),
    ("other",      "Other"),
]
GROUP_LABEL = dict(GROUPS)

AUTO = {"first_open","session_start","user_engagement","screen_view","app_update",
        "os_update","app_remove","app_clear_data","app_exception","firebase_campaign",
        "dynamic_link_first_open","dynamic_link_app_open","dynamic_link_app_update",
        "notification_foreground","notification_receive","notification_open","notification_dismiss",
        "in_app_purchase","ad_impression","ad_click","scroll","click","page_view"}

def group_of(name):
    if name in AUTO or name.startswith(("notification_","firebase_","dynamic_link_")):
        return "auto"
    if name.startswith(("splash","att_")) or name == "app_install_referrer":
        return "splash"
    if name.startswith("showcase"):
        return "onboarding"
    if name.startswith("iap_") or name.startswith("confirm_purchased") or name in (
        "purchased_not_acknowledged","undefined_confirm_purchased_fail"):
        return "paywall"
    if name.startswith(("home","see_all_style","setting")):
        return "home"
    if name.startswith("enhan"):
        return "enhance"
    if name.startswith("i2i"):
        return "i2i"
    if name.startswith("i2v"):
        return "i2v"
    if name.startswith("seedance2"):
        return "seedance2"
    if name.startswith("tryon"):
        return "tryon"
    if name.startswith("wclooks"):
        return "wclooks"
    if name.startswith("wcvideo"):
        return "wcvideo"
    if name.startswith("service"):
        return "service"
    return "other"

# ---- pivot per-event ----
events = {}   # name -> {g, e:[..], u:[..]}
for r in per_event:
    name = r["event_name"]
    if name not in events:
        events[name] = {"g": group_of(name), "e": [0]*N, "u": [0]*N}
    i = day_idx[r["d"]]
    events[name]["e"][i] = int(r["events"])
    events[name]["u"][i] = int(r["users"])

# ---- daily totals as parallel arrays ----
def col(key):
    m = {r["d"]: int(r[key]) for r in totals}
    return [m.get(d, 0) for d in days]

totals_arr = {
    "dau":          col("dau"),
    "new_users":    col("new_users"),
    "sessions":     col("sessions"),
    "total_events": col("total_events"),
}

data = {
    "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    "days": days,
    "groups": [{"id": g, "label": l} for g, l in GROUPS],
    "totals": totals_arr,
    "events": events,
}

# ---- inject into template ----
with open(os.path.join(HERE, "template.html")) as f:
    tpl = f.read()
blob = json.dumps(data, separators=(",", ":"))
out = tpl.replace('"__DATA_PLACEHOLDER__"', blob)
with open(os.path.join(HERE, "index.html"), "w") as f:
    f.write(out)

print(f"built index.html  | {N} days {days[0]}..{days[-1]}  | {len(events)} events  | {len(blob)/1024:.0f} KB data")
