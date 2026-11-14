#!/usr/bin/env python3
"""Stitches web/index_template.html + the 4 data JSON files into web/index.html,
so the page runs by double-clicking the file (no server, no fetch, no CORS)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(HERE, "web")

def load_raw(name):
    p = os.path.join(W, name)
    return json.load(open(p)) if os.path.exists(p) else None

def dump(obj):
    return json.dumps(obj, separators=(",", ":"))

# decisions.json / journey.json are single-day objects (whichever day was last run).
# Wrap each as {day: {...}} so the page can key off DAY and still degrade gracefully
# if only one day has been computed.
dec_raw = load_raw("decisions.json")
jour_raw = load_raw("journey.json")
decisions_by_day = {dec_raw["day"]: dec_raw} if dec_raw else {}
journey_by_day = {jour_raw["day"]: jour_raw} if jour_raw else {}

tpl = open(os.path.join(W, "index_template.html")).read()
tpl = tpl.replace("__DATA_JSON__", dump(load_raw("data.json")))
tpl = tpl.replace("__DECISIONS_JSON__", dump(decisions_by_day))
tpl = tpl.replace("__JOURNEY_JSON__", dump(journey_by_day))
tpl = tpl.replace("__LAYOUTS_JSON__", dump(load_raw("layouts.json") or {}))
open(os.path.join(W, "index.html"), "w").write(tpl)
print(f"wrote web/index.html ({os.path.getsize(os.path.join(W,'index.html'))/1e6:.2f} MB) — self-contained, opens from file://")
