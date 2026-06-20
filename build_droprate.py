#!/usr/bin/env python3
"""Build drop-rate.html — per-feature 'Drop Rate by Cutoff' funnel tables."""
import json, os, datetime
import funnels

HERE = os.path.dirname(os.path.abspath(__file__))
raw = json.load(open(os.path.join(HERE, "funnel_data.json")))

def to_int(v):
    try: return int(v)
    except (TypeError, ValueError): return 0

daily, total = [], None
for r in raw:
    d = r.get("d")
    row = {k: to_int(v) for k, v in r.items() if k != "d"}
    if not d:                       # ROLLUP grand-total row (period distinct)
        total = row
    else:
        row["d"] = d
        daily.append(row)
daily.sort(key=lambda r: r["d"], reverse=True)   # newest first

feat = {}
for fid, f in funnels.FEATURES.items():
    feat[fid] = {"label": f["label"], "steps": [[f"{fid}__{k}", lab] for k, lab, ev, ff in f["steps"]]}

data = {
    "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    "range": [daily[-1]["d"], daily[0]["d"]],
    "features": feat,
    "daily": daily,
    "total": total or {},
}

tpl = open(os.path.join(HERE, "droprate.template.html")).read()
out = tpl.replace('"__DATA_PLACEHOLDER__"', json.dumps(data, separators=(",", ":")))
open(os.path.join(HERE, "drop-rate.html"), "w").write(out)
print(f"built drop-rate.html | {len(daily)} days {data['range'][0]}..{data['range'][1]} | {len(feat)} features")
