"""Shared helpers: paths, local metric projection, focus-lot choice."""
import json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
WEB = os.path.join(ROOT, "web", "data")
RESULTS = os.path.join(ROOT, "results")
for d in (DATA, WEB, RESULTS):
    os.makedirs(d, exist_ok=True)

LAT0, LON0 = 35.7693, -78.6765           # projection origin (near Hunt Library)
MX = 111320 * math.cos(math.radians(LAT0))
MY = 110540
PATH_FACTOR, WALK_M_PER_MIN = 1.35, 80.0  # straight line -> path; walking speed (ASSUMED)

def to_m(lat, lon):
    return (lon - LON0) * MX, (lat - LAT0) * MY

def to_ll(x, y):
    return y / MY + LAT0, x / MX + LON0

def walk_min(d_m):
    return d_m * PATH_FACTOR / WALK_M_PER_MIN

def jload(name, base=WEB):
    return json.load(open(os.path.join(base, name)))

def jdump(obj, name, base=WEB, **kw):
    p = os.path.join(base, name)
    json.dump(obj, open(p, "w"), **kw)
    print("wrote", os.path.relpath(p, ROOT), f"{os.path.getsize(p) / 1024:.0f} KB")
