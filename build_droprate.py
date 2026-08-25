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

# Calendar gaps inside the range. The GA4 export for iip055 is read from
# `events_intraday_*` only, and Firebase treats intraday tables as transient — so days
# whose intraday table has already been dropped simply vanish. Without this, the page
# prints "2026-03-10 → 2026-08-20 · 133 ngày" and puts 07-18 directly beside 08-19 as if
# they were consecutive, which silently turns a 31-day hole into an apparent trend.
def _gaps(sorted_days):
    out = []
    for a, b in zip(sorted_days, sorted_days[1:]):
        da = datetime.date.fromisoformat(a)
        db = datetime.date.fromisoformat(b)
        if (db - da).days > 1:
            out.append({"after": a, "before": b, "missing": (db - da).days - 1})
    return out


_asc = [r["d"] for r in sorted(daily, key=lambda r: r["d"])]
gaps = _gaps(_asc)
span = (datetime.date.fromisoformat(_asc[-1]) - datetime.date.fromisoformat(_asc[0])).days + 1 if _asc else 0

data = {
    "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    "range": [daily[-1]["d"], daily[0]["d"]],
    "features": feat,
    "daily": daily,
    "total": total or {},
    "gaps": gaps,
    "coverage": {"days_with_data": len(_asc), "days_in_span": span,
                 "missing": span - len(_asc)},
}

tpl = open(os.path.join(HERE, "droprate.template.html")).read()
out = tpl.replace('"__DATA_PLACEHOLDER__"', json.dumps(data, separators=(",", ":")))
open(os.path.join(HERE, "drop-rate.html"), "w").write(out)
print(f"built drop-rate.html | {len(daily)} days {data['range'][0]}..{data['range'][1]} | {len(feat)} features")
if gaps:
    print(f"  ⚠ {data['coverage']['missing']} ngày THIẾU trong khoảng "
          f"({data['coverage']['days_with_data']}/{span} ngày có dữ liệu):")
    for g in gaps:
        print(f"    {g['after']} → {g['before']}  thiếu {g['missing']} ngày")
