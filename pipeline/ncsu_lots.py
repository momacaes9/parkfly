#!/usr/bin/env python3
"""
ncsu_lots.py - real NC State parking lots -> web/data/lots.json

Source: NCSU Transportation GIS (official polygons, SPACES, permit zones),
cached in data/ncsu_parking_raw.geojson. OpenStreetMap (Overpass) is used only
to geocode the destination and to find the road nearest each lot (entrance).
Stall positions are ESTIMATED (pipeline/stalls.py); counts are official.
"""
import datetime, json, os, sys, urllib.parse, urllib.request

from shapely.geometry import shape, Point, Polygon, MultiPolygon, LineString
from shapely.ops import transform, unary_union, nearest_points
import warnings; warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, to_m, to_ll, walk_min, jdump
import stalls

NCSU_URL = ("https://gismaps.oit.ncsu.edu/arcgis/rest/services/Transportation/"
            "Transportation_OnlineCampusMap/MapServer/1/query?where=1%3D1&outFields=*&outSR=4326&f=geojson")
RAW = os.path.join(DATA, "ncsu_parking_raw.geojson")
OSM = os.path.join(DATA, "osm_hunt.json")
HUNT_FALLBACK = (35.7693, -78.6765)
PAY_RATE_HR = 2.0     # ASSUMED visitor pay rate ($/h); the GIS feed has no prices
# Focus lots: real NCSU features near Hunt Library, picked by distance and type (see ASSUMPTIONS.md)
FOCUS = ["Poulton Deck - Visitor Pay Area", "Poulton Deck - C", "Partners I Lot", "Main Campus Drive - C",
         "Textiles Lot", "E.B. III / Entrepreneur Drive", "Research Drive"]
CONTEXT_RADIUS_M = 1500


def fetch(url, dest, data=None, timeout=40):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    try:
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "parkfly-hackday/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
        open(dest, "wb").write(body)
        return True
    except Exception as e:
        print("[warn] fetch failed:", url[:70], e)
        return False


def osm():
    q = ('[out:json][timeout:25];('
         'nwr["name"~"Hunt"](35.765,-78.682,35.773,-78.671);'
         'way["highway"~"^(service|residential|tertiary|secondary|unclassified)$"](35.762,-78.686,35.776,-78.668);'
         ');out center geom tags;')
    ok = fetch("https://overpass.kumi.systems/api/interpreter", OSM,
               data=("data=" + urllib.parse.quote(q)).encode(), timeout=45)
    if not ok:
        return None
    try:
        return json.load(open(OSM))["elements"]
    except Exception:
        os.remove(OSM)
        return None


def main():
    if not fetch(NCSU_URL, RAW, timeout=60):
        sys.exit("no NCSU data (endpoint and cache both unavailable)")
    fc = json.load(open(RAW))
    els = osm()
    dest = {"name": "Hunt Library", "lat": HUNT_FALLBACK[0], "lon": HUNT_FALLBACK[1],
            "basis": "approximate (OSM lookup failed)"}
    roads = []
    if els:
        for e in els:
            t = e.get("tags", {})
            if "Hunt" in t.get("name", "") and "Library" in t.get("name", "") and t.get("building"):
                c = e.get("center") or e
                dest = {"name": t["name"], "lat": c["lat"], "lon": c["lon"],
                        "basis": f"OpenStreetMap {e['type']}/{e['id']} centroid"}
            if t.get("highway") and e.get("geometry"):
                roads.append(LineString([to_m(p["lat"], p["lon"]) for p in e["geometry"]]))
    print("destination:", dest)
    dxy = Point(to_m(dest["lat"], dest["lon"]))
    road_net = unary_union(roads) if roads else None

    def geom_m(f):
        return transform(lambda x, y, z=None: to_m(y, x), shape(f["geometry"]))

    feats = {}
    context = []
    for f in fc["features"]:
        p = f["properties"]
        g = geom_m(f)
        if not g.is_valid:
            g = g.buffer(0)
        d = g.centroid.distance(dxy)
        if d > CONTEXT_RADIUS_M:
            continue
        name = (p.get("NAME") or "Lot").strip()
        if name in FOCUS and (p.get("SPACES") or 0) > 0:
            feats[name] = (p, g)
        gs = g.simplify(1.5)
        polys = list(gs.geoms) if isinstance(gs, MultiPolygon) else [gs]
        context.append({"name": name, "spaces": p.get("SPACES") or 0, "zone": (p.get("ZONE_") or "").strip(),
                        "type": p.get("Type"), "focus": name in FOCUS,
                        "polys": [[[round(v, 6) for v in to_ll(x, y)] for x, y in pg.exterior.coords] for pg in polys]})

    lots = []
    deck_done = {}
    for name in FOCUS:
        if name not in feats:
            print("[warn] focus lot missing in NCSU data:", name)
            continue
        p, g = feats[name]
        n = int(p["SPACES"])
        if road_net is not None:
            a, b = nearest_points(g.boundary, road_net)
            ent, ent_basis = (a.x, a.y), "lot boundary point nearest an OSM road"
        else:
            a, _ = nearest_points(g.boundary, dxy)
            ent, ent_basis = (a.x, a.y), "lot boundary point nearest the destination (no OSM roads)"
        is_deck = "deck" in (p.get("Type") or "").lower()
        if is_deck:
            base = name.split(" - ")[0]
            if base not in deck_done:   # one schematic lattice for the whole deck, split by section
                tot = sum(int(feats[k][0]["SPACES"]) for k in FOCUS if k in feats and k.split(" - ")[0] == base)
                pts = stalls.lattice(g, tot)
                pts.sort(key=lambda q: Point(q).distance(Point(ent)))
                deck_done[base] = pts
            pts = deck_done[base][:n]; deck_done[base] = deck_done[base][n:]
            method = "schematic lattice (deck interior not mapped; official count)"
        else:
            pts, method = stalls.layout(g, n, ent)
        # attractiveness: walk to destination + a little for driving in from the entrance (ASSUMED 0.3)
        score = [Point(q).distance(dxy) + 0.3 * Point(q).distance(Point(ent)) for q in pts]
        order = sorted(range(len(pts)), key=lambda i: score[i])
        spots = []
        for i in order:
            la, lo = to_ll(*pts[i])
            spots.append([round(la, 6), round(lo, 6)])
        zone = (p.get("ZONE_") or "").strip()
        pay = zone == "PY"
        c = g.centroid
        la, lo = to_ll(c.x, c.y)
        lots.append({
            "id": len(lots), "name": name, "spaces": n, "zone": zone, "type": p.get("Type"),
            "pay": pay, "price_hr": PAY_RATE_HR if pay else 0.0, "hc": p.get("HC") or 0, "ev": p.get("EV") or 0,
            "lat": round(la, 6), "lon": round(lo, 6), "x": round(c.x, 1), "y": round(c.y, 1),
            "walk_min": round(walk_min(c.distance(dxy)), 1),
            "entrance": [round(v, 6) for v in to_ll(*ent)], "entrance_basis": ent_basis,
            "layout_method": method, "spots": spots,   # sorted most attractive first: index = rank
        })
        print(f"  {name:36s} {n:4d} spaces  walk {lots[-1]['walk_min']:4.1f} min  {method}")

    jdump({"generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "source": "NCSU Transportation GIS (official polygons and space counts); stall positions estimated",
           "source_url": NCSU_URL, "dest": dest, "lots": lots, "context": context,
           "assumptions": {"pay_rate_hr": PAY_RATE_HR, "walk": "straight line x1.35 at 80 m/min",
                           "rank": "walk distance to destination + 0.3 x distance to lot entrance"}},
          "lots.json")


if __name__ == "__main__":
    main()
