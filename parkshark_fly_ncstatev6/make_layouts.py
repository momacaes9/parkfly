#!/usr/bin/env python3
"""
Stall-layout estimator for NC State lots and decks.

SURFACE LOTS
  Input (REAL): official polygon outline + official SPACES count (NCSU GIS).
  Input (GEOMETRY): US standard 9x18 ft stalls (2.75 x 5.5 m), 24 ft (7.3 m)
  aisles, double-loaded rows.
  Method: find the lot's dominant axis, lay rows along it, keep stalls whose
  footprint falls inside the real polygon, then reconcile against the official
  count and publish only decent fits.

PARKING DECKS (multi-level)
  A deck's footprint is one level. We fit stalls to that footprint to get
  stalls-per-level, then:
        levels = round(official capacity / stalls per level)
  Each level reuses the footprint plan; the top level is partial when the
  capacity does not divide evenly, which is what real decks look like (ramps
  and circulation eat the top deck). Published floor plans would be better,
  but NC State does not publish per-level drawings openly; capacity, footprint
  and standard geometry are what is actually available.

LIMITS: stall POSITIONS are inferred; stall COUNTS are official. Not a survey.
Production path: a parking-stall CV model (e.g. ESRI Parking Spot Detection,
Mask R-CNN) over 6-inch NC OneMap orthoimagery recovers true stripe positions.
"""
import json, math, os
from shapely.geometry import Polygon, box
from shapely.affinity import rotate

HERE = os.path.dirname(os.path.abspath(__file__))
STALL_W, STALL_L, AISLE = 2.75, 5.50, 7.30
MIN_AGREE = 0.45          # surface lots only
DECK_USABLE = 0.88        # share of a deck floor that is stalls, not ramp/core

def to_m(geom, lat0, lon0):
    kx = 111320 * math.cos(math.radians(lat0)); ky = 110540
    def conv(r): return [((x - lon0) * kx, (y - lat0) * ky) for x, y in r]
    if geom["type"] == "Polygon":
        return Polygon(conv(geom["coordinates"][0]))
    best, ba = None, -1
    for poly in geom["coordinates"]:
        p = Polygon(conv(poly[0]))
        if p.area > ba: best, ba = p, p.area
    return best

def layout(poly_m):
    rect = poly_m.minimum_rotated_rectangle
    xs, ys = rect.exterior.coords.xy
    edges = [((xs[i+1]-xs[i]), (ys[i+1]-ys[i])) for i in range(4)]
    ex, ey = max(edges, key=lambda e: e[0]**2 + e[1]**2)
    ang = math.degrees(math.atan2(ey, ex))
    aligned = rotate(poly_m, -ang, origin=poly_m.centroid)
    minx, miny, maxx, maxy = aligned.bounds
    band = 2 * STALL_L + AISLE
    stalls, rows = [], 0
    y = miny + 0.6
    while y + 2 * STALL_L <= maxy + 0.1:
        for side, y0 in ((0, y), (1, y + STALL_L)):
            x, col, any_ = minx + 0.6, 0, False
            while x + STALL_W <= maxx:
                if aligned.contains(box(x, y0, x + STALL_W, y0 + STALL_L)):
                    stalls.append({"x": x, "y": y0, "row": rows, "col": col}); col += 1; any_ = True
                x += STALL_W
            if any_: rows += 1
        y += band
    return stalls, ang, aligned

def main():
    data = json.load(open(os.path.join(HERE, "web", "data.json")))
    raw = json.load(open(os.path.join(HERE, "ncstate_parking_raw.geojson")))
    by = {}
    for f in raw["features"]:
        n = f["properties"].get("NAME")
        if n: by.setdefault(n, f)

    out, errs = {}, 0
    for l in data["lots"]:
        if l["spaces"] < 20 or l["name"] not in by: continue
        try:
            pm = to_m(by[l["name"]]["geometry"], l["lat"], l["lon"])
            if pm is None or pm.area < 300: continue
            stalls, ang, aligned = layout(pm)
            if not stalls: continue
            minx, miny, maxx, maxy = aligned.bounds
            mk = lambda s: {"id": f"{chr(65 + s['row'] % 26)}{s['col']+1}",
                            "x": round(s["x"]-minx, 2), "y": round(s["y"]-miny, 2),
                            "w": STALL_W, "h": STALL_L, "row": s["row"]}
            entry = {"lot": l["name"], "official_spaces": l["spaces"],
                     "angle_deg": round(ang, 1), "w_m": round(maxx-minx, 1), "h_m": round(maxy-miny, 1),
                     "outline": [[round(x-minx, 2), round(y-miny, 2)] for x, y in aligned.exterior.coords]}

            if l["deck"]:
                per = max(1, int(len(stalls) * DECK_USABLE))
                levels = max(1, round(l["spaces"] / per))
                base = [mk(s) for s in stalls[:per]]
                floors = []
                for lv in range(levels):
                    remaining = l["spaces"] - lv * per
                    n = per if remaining >= per else max(0, remaining)
                    floors.append({"level": lv + 1, "stalls": base[:n]})
                drawn = sum(len(f["stalls"]) for f in floors)
                entry.update({"deck": True, "levels": levels, "per_floor": per,
                              "floors": floors, "drawn": drawn,
                              "agreement": round(min(drawn, l["spaces"]) / max(drawn, l["spaces"]), 3),
                              "method": "deck: official footprint gives stalls per level; official capacity "
                                        "divided by that gives the level count; top level partial"})
            else:
                agree = min(len(stalls), l["spaces"]) / max(len(stalls), l["spaces"])
                if agree < MIN_AGREE: continue
                st = sorted(stalls, key=lambda s: (s["row"], s["col"]))
                if len(st) > l["spaces"]:
                    st = sorted(st, key=lambda s: (-s["row"], -s["col"]))[len(st)-l["spaces"]:]
                    st = sorted(st, key=lambda s: (s["row"], s["col"]))
                entry.update({"deck": False, "levels": 1, "drawn": len(st),
                              "agreement": round(agree, 3),
                              "floors": [{"level": 1, "stalls": [mk(s) for s in st]}],
                              "method": "surface: official outline + official capacity + standard "
                                        "9x18 ft stalls, 24 ft aisles"})
            out[l["name"]] = entry
        except Exception as e:
            errs += 1
    json.dump(out, open(os.path.join(HERE, "web", "layouts.json"), "w"))
    decks = [v for v in out.values() if v["deck"]]
    print(f"layouts: {len(out)} facilities ({len(decks)} decks), {errs} errors")
    for v in sorted(decks, key=lambda v: -v["official_spaces"])[:8]:
        print(f"  DECK {v['lot'][:34]:36s} {v['official_spaces']:5d} spaces = {v['levels']} levels x ~{v['per_floor']}")
    for v in sorted((x for x in out.values() if not x["deck"]), key=lambda v: -v["agreement"])[:6]:
        print(f"  LOT  {v['lot'][:34]:36s} drawn {v['drawn']:4d} / official {v['official_spaces']:4d}  agree {v['agreement']:.2f}")

if __name__ == "__main__":
    main()
