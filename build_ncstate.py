#!/usr/bin/env python3
"""
Park Shark x Fly Brain - NC State build.

Reads NC State's official parking areas (ArcGIS GeoJSON saved as
ncstate_parking_raw.geojson next to this script). Until that file exists,
uses a small SEED dataset (clearly flagged: coords/capacities approximate).

Outputs:
  web/data.json    - lots + hourly occupancy estimate/band + senses per hour
  senses.json      - per-lot fly sense rates (Hz) for one scenario hour,
                     ready for the hackathon Colab notebook
Everything here is an ESTIMATE (no sensors exist). The basis of every number
is written into the output so the UI can show it.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "ncstate_parking_raw.geojson")

# ---------------------------------------------------------------- scenario
DEST = {"name": "Riddick Hall (Hack Day venue)", "lat": 35.7867, "lon": -78.6688,
        "coord_basis": "approximate - set exact pin before demo"}
SCENARIO_HOUR = 10          # Saturday 10:00, the event itself
SCENARIO_DAY = "sat"        # "weekday" | "sat"
PERSONA = {"label": "student driving to Hack Day, no NCSU permit",
           "permit_zone": None, "willing_to_pay": True}
EVENT_BOOST = 0.0           # set >0 if a game day (adds to occupancy of nearby lots)

# ------------------------------------------------- occupancy templates (ASSUMED)
# Hand-set hour curves per lot profile; these are the estimation basis until
# real data exists. Values = fraction of spaces occupied, weekday.
T = {
 "commuter": [.08,.06,.05,.05,.06,.08,.18,.45,.72,.88,.93,.95,.94,.93,.90,.82,.68,.50,.35,.25,.18,.14,.11,.09],
 "deck":     [.12,.10,.09,.09,.10,.12,.20,.42,.65,.80,.86,.88,.87,.86,.84,.78,.66,.52,.40,.32,.25,.20,.16,.13],
 "pay":      [.05,.04,.04,.04,.05,.07,.12,.30,.55,.70,.78,.82,.83,.80,.75,.68,.58,.48,.40,.35,.28,.18,.10,.07],
 "resident": [.92,.93,.94,.94,.94,.93,.88,.78,.65,.55,.50,.48,.47,.48,.52,.58,.68,.78,.85,.88,.90,.91,.92,.92],
 "visitor":  [.05,.04,.04,.04,.05,.06,.10,.25,.50,.68,.75,.78,.78,.75,.70,.62,.52,.42,.33,.27,.22,.15,.09,.06],
}
SAT_MULT = {"commuter": .18, "deck": .30, "pay": .45, "resident": .95, "visitor": .40}

PERMIT_COLS = ["A4","AB","AS_","B","C","C_CC","C_DD","CD","CL","F","GV","LD","LO",
               "RC","RD","RE","RF","RH_CC","RS","RV","RW","SV","SV_UV","UE","UV","W",
               "ZIP","RCS","C_CB"]
RES_COLS = {"RC","RD","RE","RF","RH_CC","RS","RV","RW"}

def seed():
    """Placeholder lots. Coordinates and capacities APPROXIMATE - replaced
    wholesale by ncstate_parking_raw.geojson."""
    rows = [
      ("Coliseum Parking Deck", 35.7833, -78.6706, 1150, "deck", 200, 40, 10),
      ("Dan Allen Parking Deck", 35.7852, -78.6721, 700, "deck", 80, 20, 6),
      ("Riddick Lot", 35.7872, -78.6679, 120, "commuter", 0, 4, 0),
      ("Jeter Drive Lot", 35.7846, -78.6650, 90, "commuter", 0, 2, 0),
      ("Brooks Hall Lot", 35.7900, -78.6633, 70, "commuter", 0, 2, 0),
      ("Hillsborough Visitor Spaces", 35.7892, -78.6662, 40, "pay", 40, 2, 0),
      ("Partners Way Deck (Centennial)", 35.7721, -78.6768, 1200, "deck", 300, 30, 12),
      ("Oval Drive West Lot (Centennial)", 35.7716, -78.6737, 250, "commuter", 20, 6, 4),
      ("Toshiba Lot (Centennial)", 35.7684, -78.6753, 180, "commuter", 0, 4, 0),
      ("Varsity Lot", 35.7805, -78.6826, 900, "commuter", 0, 10, 0),
    ]
    fs = []
    for i, (n, la, lo, sp, prof, py, hc, ev) in enumerate(rows):
        fs.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lo, la]},
                   "properties": {"NAME": n + " [SEED - approx]", "SPACES": sp, "ZONE_": prof.upper(),
                                  "Type": "Deck" if prof == "deck" else "Lot", "PY": py, "HC": hc,
                                  "EV": ev, "V": py // 2, "STATUS": "Active", "_seed": True,
                                  "_profile": prof}})
    return {"type": "FeatureCollection", "features": fs}

def centroid(geom):
    if geom["type"] == "Point":
        return geom["coordinates"][1], geom["coordinates"][0]
    rings = geom["coordinates"] if geom["type"] == "Polygon" else geom["coordinates"][0]
    pts = rings[0]
    la = sum(p[1] for p in pts) / len(pts); lo = sum(p[0] for p in pts) / len(pts)
    return la, lo

def walk_min(la, lo):
    dx = (lo - DEST["lon"]) * 111320 * math.cos(math.radians(la))
    dy = (la - DEST["lat"]) * 110540
    return math.hypot(dx, dy) * 1.35 / 80.0   # path factor / walking speed m per min

def profile_of(p):
    if p.get("_profile"): return p["_profile"]
    t = (p.get("Type") or "").lower(); z = (p.get("ZONE_") or "").upper()
    name = (p.get("NAME") or "").lower()
    if "deck" in t or "deck" in name: return "deck"
    res = sum(p.get(c) or 0 for c in RES_COLS)
    tot = p.get("SPACES") or 1
    if res > 0.5 * tot or z.startswith("R"): return "resident"
    if (p.get("PY") or 0) + (p.get("V") or 0) + (p.get("VP") or 0) > 0.5 * tot: return "pay"
    if (p.get("V") or 0) > 0: return "visitor"
    return "commuter"

def usable_spaces(p, spaces):
    """How many spaces this persona may legally use. Weekend assumption:
    most NCSU zones relax on weekends - flagged, verify signs."""
    pay = (p.get("PY") or 0) + (p.get("V") or 0) + (p.get("VP") or 0)
    if PERSONA["permit_zone"]:
        pay += p.get(PERSONA["permit_zone"], 0) or 0
    if SCENARIO_DAY == "sat":
        res = sum(p.get(c) or 0 for c in RES_COLS)
        return max(pay, spaces - res)          # weekend: non-resident spaces usable (ASSUMED)
    return pay if PERSONA["willing_to_pay"] else 0

def main():
    if os.path.exists(RAW):
        fc = json.load(open(RAW)); src = "NCSU Transportation GIS (official)"
        fc["features"] = [f for f in fc["features"] if (f["properties"].get("SPACES") or 0) > 0]
    else:
        fc = seed(); src = "SEED placeholder - swap in ncstate_parking_raw.geojson"
        print("!! using SEED data:", RAW, "not found")

    lots = []
    for f in fc["features"]:
        p = f["properties"]; la, lo = centroid(f["geometry"])
        w = walk_min(la, lo)
        if w > 35: continue                     # keep lots within reach of the venue
        spaces = p.get("SPACES") or 0
        prof = profile_of(p)
        base = T[prof]; mult = SAT_MULT[prof] if SCENARIO_DAY == "sat" else 1.0
        occ = [min(.99, v * mult + EVENT_BOOST) for v in base]
        band = 0.10 if not p.get("_seed") else 0.18   # wider band on seed data
        use = min(usable_spaces(p, spaces), spaces)
        risk = max(0.0, 1 - use / spaces) if spaces else 1.0
        hours = []
        for h in range(24):
            o = occ[h]
            fill = occ[(h + 1) % 24] - o
            free_use = max(0.0, use * (1 - o))
            p_free = 1 - math.exp(-free_use / 3) if use else 0.0
            hours.append({"occ": round(o, 3), "lo": round(max(0, o - band), 3),
                          "hi": round(min(1, o + band), 3), "fill": round(fill, 3),
                          "p_free": round(p_free, 3)})
        lots.append({
            "name": p.get("NAME") or "Lot", "lat": la, "lon": lo, "spaces": spaces,
            "zone": p.get("ZONE_"), "type": p.get("Type"), "profile": prof,
            "usable": use, "permit_risk": round(risk, 3),
            "covered": prof == "deck" or "deck" in (p.get("Type") or "").lower(),
            "pay_spaces": (p.get("PY") or 0) + (p.get("V") or 0) + (p.get("VP") or 0),
            "hc": p.get("HC") or 0, "ev": p.get("EV") or 0,
            "walk_min": round(w, 1), "price_hr": 2.0 if (p.get("PY") or 0) else 0.0,
            "hours": hours, "ring": f["geometry"] if f["geometry"]["type"] != "Point" else None,
            "seed": bool(p.get("_seed")),
        })

    # ---------------- fly senses for the scenario hour (winsorized at 2 SD, per handbook)
    def wins(vals):
        m = sum(vals) / len(vals)
        sd = (sum((v - m) ** 2 for v in vals) / len(vals)) ** .5 or 1
        cl = [min(max(v, m - 2 * sd), m + 2 * sd) for v in vals]
        lo_, hi_ = min(cl), max(cl)
        return [(v - lo_) / (hi_ - lo_) if hi_ > lo_ else 0.5 for v in cl]

    h = SCENARIO_HOUR
    sweet = [l["hours"][h]["p_free"] * math.exp(-l["walk_min"] / 10) for l in lots]
    bitter = [0.6 * l["permit_risk"] + 0.4 * min(l["price_hr"] / 4, 1) for l in lots]
    loom = [max(0.0, l["hours"][h]["fill"]) * 10 + (0.5 if l["hours"][h]["occ"] > .85 else 0) for l in lots]
    S, B, L = wins(sweet), wins(bitter), wins(loom)
    senses = []
    for i, l in enumerate(lots):
        l["senses"] = {"sugar_hz": round(200 * S[i]), "bitter_hz": round(200 * B[i]),
                       "looming_hz": round(150 * L[i])}
        senses.append({"lot": l["name"], "walk_min": l["walk_min"], **l["senses"],
                       "basis": {"p_free": l["hours"][h]["p_free"], "permit_risk": l["permit_risk"],
                                 "fill_per_hr": l["hours"][h]["fill"], "occ": l["hours"][h]["occ"]}})

    os.makedirs(os.path.join(HERE, "web"), exist_ok=True)
    json.dump({"generated_for": {"dest": DEST, "day": SCENARIO_DAY, "hour": h, "persona": PERSONA},
               "source": src, "honesty": "All occupancy values are model estimates from assumed "
               "hour templates; no sensor has reported. Bands reflect that. Permit rules simplified; "
               "check posted signs.", "lots": lots},
              open(os.path.join(HERE, "web", "data.json"), "w"))
    json.dump({"scenario": f"{SCENARIO_DAY} {h}:00 -> {DEST['name']}", "persona": PERSONA["label"],
               "lots": senses}, open(os.path.join(HERE, "senses.json"), "w"), indent=1)
    print(f"built {len(lots)} lots ({src}); scenario {SCENARIO_DAY} {h}:00")
    for s in sorted(senses, key=lambda x: -x["sugar_hz"])[:8]:
        print(f"  {s['lot'][:44]:46s} sugar {s['sugar_hz']:3d}  bitter {s['bitter_hz']:3d}  loom {s['looming_hz']:3d}  walk {s['walk_min']:4.1f}m")

if __name__ == "__main__":
    main()
