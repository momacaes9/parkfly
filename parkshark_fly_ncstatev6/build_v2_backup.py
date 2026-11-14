#!/usr/bin/env python3
"""
Park Shark x Fly Brain - NC State occupancy estimation (no sensors yet).

Methodology (each layer swaps to live data later without changing the shape):
 1. BASELINE: each lot's hourly curve = blend of archetype curves weighted by
    its real permit mix (NCSU GIS per-permit space counts). A lot full of
    resident permits behaves inverted vs a commuter lot. (Same idea as the
    Duke Tier 3 campus template, but calibrated per lot by who may park there.)
 2. DEMAND: destinations (buildings/venues) carry hourly busyness curves;
    each destination's parking demand is spread over nearby lots by a
    gravity/Huff assignment: weight ~ usable_capacity x exp(-walk/tau).
    Live Popular-Times / traffic-flow data plugs in here later.
 3. Derived per lot/hour: occupancy + band, P(open usable spot), fill rate
    (d occ/dt -> the fly's LOOMING), sweetness (SUGAR), friction (BITTER),
    and a wait-or-drive estimate when nearly full (queueing: avg dwell /
    (spaces x turnover)).
All numbers are estimates and labeled so. Posted signs control reality.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "ncstate_parking_raw.geojson")

DEST = {"name": "Riddick Hall (Hack Day venue)", "lat": 35.7867, "lon": -78.6688,
        "coord_basis": "approximate - set exact pin before demo"}
SCENARIO_HOUR = 12
SCENARIO_DAY = "sat"            # "weekday" | "sat"
PERSONA = {"label": "student driving to Hack Day, no NCSU permit", "permit_zone": None,
           "willing_to_pay": True}
AVG_DWELL_MIN = {"visitor": 90, "pay": 110, "commuter": 300, "deck": 240, "resident": 900}

# ---- archetype hourly occupancy curves (ASSUMED baseline; weekday) ----------
ARCH = {
 "commuter": [.08,.06,.05,.05,.06,.08,.18,.45,.72,.88,.93,.95,.94,.93,.90,.82,.68,.50,.35,.25,.18,.14,.11,.09],
 "resident": [.92,.93,.94,.94,.94,.93,.88,.78,.65,.55,.50,.48,.47,.48,.52,.58,.68,.78,.85,.88,.90,.91,.92,.92],
 "visitor":  [.05,.04,.04,.04,.05,.06,.10,.25,.50,.68,.75,.78,.78,.75,.70,.62,.52,.42,.33,.27,.22,.15,.09,.06],
 "service":  [.10,.08,.08,.08,.10,.15,.35,.60,.75,.80,.80,.78,.76,.75,.72,.65,.50,.35,.25,.18,.14,.12,.11,.10],
}
SAT = {"commuter": .15, "resident": .95, "visitor": .45, "service": .25}

PCOLS = {"A4":"commuter","AB":"commuter","AS_":"service","B":"commuter","C":"commuter",
 "C_CC":"commuter","C_DD":"commuter","CD":"commuter","CL":"commuter","F":"commuter",
 "GV":"service","LD":"service","LO":"service","PY":"visitor","RC":"resident","RD":"resident",
 "RE":"resident","RF":"resident","RH_CC":"resident","RS":"resident","RV":"resident",
 "RW":"resident","SV":"service","SV_UV":"service","UE":"service","UV":"service",
 "V":"visitor","VC":"visitor","VP":"visitor","W":"commuter","ZIP":"visitor","RCS":"resident","C_CB":"commuter"}
RES = [c for c, k in PCOLS.items() if k == "resident"]
VIS = ["PY", "V", "VC", "VP", "ZIP"]

# ---- destination demand layer (curves ASSUMED; Popular-Times hook later) ----
# cars/hour at peak, weekday curve shape, sat multiplier
DESTS = [
 ("Riddick Hall / engineering NE", 35.7867, -78.6688, 60, "class", 1.0 if SCENARIO_DAY=="sat" else 1.0),
 ("D.H. Hill Library", 35.7876, -78.6694, 50, "library", .45),
 ("Talley Student Union", 35.7838, -78.6709, 70, "social", .55),
 ("Carmichael Gym", 35.7832, -78.6671, 45, "gym", .60),
 ("Bell Tower / Holladay", 35.7859, -78.6637, 30, "class", .20),
 ("Hunt Library (Centennial)", 35.7702, -78.6766, 45, "library", .40),
 ("EB I-III / Oval Dr (Centennial)", 35.7716, -78.6737, 60, "class", .20),
 ("McKimmon Center", 35.7817, -78.6855, 40, "events", .70),
 ("Reynolds Coliseum", 35.7840, -78.6688, 25, "events", .50),
]
SHAPES = {
 "class":   [0,0,0,0,0,.05,.15,.5,.9,1,.95,.9,.85,.9,.85,.7,.5,.3,.15,.1,.05,0,0,0],
 "library": [.05,.02,0,0,0,0,.05,.15,.4,.6,.7,.75,.8,.85,.9,.95,1,.95,.9,.85,.8,.6,.3,.1],
 "social":  [.05,.02,0,0,0,0,.1,.3,.5,.6,.8,1,.95,.8,.7,.7,.8,.9,.85,.7,.5,.3,.15,.08],
 "gym":     [0,0,0,0,0,.2,.5,.6,.5,.4,.4,.5,.6,.5,.5,.6,.8,1,.95,.8,.6,.4,.2,.05],
 "events":  [0,0,0,0,0,0,.1,.3,.6,.8,.8,.7,.7,.7,.6,.5,.4,.5,.7,.8,.6,.3,.1,0],
}
HACK_DAY = {"dest": "Riddick Hall / engineering NE", "cars": 35,
            "curve": [0]*8 + [.6,1,1,.9,.9,1,.9,.7,.3] + [0]*7}   # 9am-4:30pm event
TAU_WALK = 6.0        # min; demand assignment decay
WALK_M_PER_MIN = 80.0

def centroid(g):
    if g["type"] == "Point": return g["coordinates"][1], g["coordinates"][0]
    rings = g["coordinates"] if g["type"] == "Polygon" else max(g["coordinates"], key=lambda r: len(r[0]))
    pts = rings[0]
    return sum(p[1] for p in pts)/len(pts), sum(p[0] for p in pts)/len(pts)

def walk_min(a_lat, a_lon, b_lat, b_lon):
    dx = (a_lon-b_lon)*111320*math.cos(math.radians(a_lat)); dy = (a_lat-b_lat)*110540
    return math.hypot(dx, dy)*1.35/WALK_M_PER_MIN

def wins01(vals):
    m = sum(vals)/len(vals); sd = (sum((v-m)**2 for v in vals)/len(vals))**.5 or 1
    cl = [min(max(v, m-2*sd), m+2*sd) for v in vals]
    lo, hi = min(cl), max(cl)
    return [(v-lo)/(hi-lo) if hi > lo else .5 for v in cl]

def main():
    fc = json.load(open(RAW))
    lots = []
    for f in fc["features"]:
        p, g = f["properties"], f["geometry"]
        spaces = p.get("SPACES") or 0
        if not g or spaces < 5: continue
        la, lo = centroid(g)
        w_dest = walk_min(la, lo, DEST["lat"], DEST["lon"])
        if w_dest > 30: continue
        mix = {}
        for c, kind in PCOLS.items():
            n = p.get(c) or 0
            if n > 0: mix[kind] = mix.get(kind, 0) + n
        if not mix: mix = {"commuter": spaces}
        tot_mix = sum(mix.values())
        deck = "deck" in (p.get("Type") or "").lower()
        vis_sp = sum(p.get(c) or 0 for c in VIS)
        res_sp = sum(p.get(c) or 0 for c in RES)
        use = vis_sp + (p.get(PERSONA["permit_zone"]) or 0 if PERSONA["permit_zone"] else 0)
        if SCENARIO_DAY == "sat":
            use = max(use, spaces - res_sp)      # weekend relaxation (ASSUMED - verify signs)
        use = min(max(use, 0), spaces)
        risk = max(0.0, 1 - use/spaces)
        profile = max(mix, key=mix.get)
        dwell = AVG_DWELL_MIN["deck" if deck else {"commuter":"commuter","resident":"resident",
                 "visitor":"visitor","service":"commuter"}[profile]]
        base = [sum(ARCH[k][h]*(n/tot_mix)*(SAT[k] if SCENARIO_DAY=="sat" else 1)
                    for k, n in mix.items()) for h in range(24)]
        lots.append(dict(name=p.get("NAME") or f"Lot {p.get('OBJECTID')}", lat=la, lon=lo,
            spaces=spaces, usable=use, risk=risk, zone=(p.get("ZONE_") or "").strip(),
            type=p.get("Type"), deck=deck, profile=profile,
            hc=p.get("HC") or 0, ev=p.get("EV") or 0, pay=vis_sp,
            price_hr=2.0 if vis_sp else 0.0, walk=round(w_dest, 1), dwell=dwell,
            base=base, demand=[0.0]*24, ring=g))

    # ---- demand layer: gravity assignment of destination cars to lots -------
    dests_out = []
    for name, dla, dlo, peak, shape, satm in DESTS:
        curve = SHAPES[shape]; mult = satm if SCENARIO_DAY == "sat" else 1.0
        cand = []
        for l in lots:
            wm = walk_min(l["lat"], l["lon"], dla, dlo)
            if wm < 12 and l["usable"] > 0:
                cand.append((l, l["usable"]*math.exp(-wm/TAU_WALK)))
        tot = sum(wt for _, wt in cand) or 1
        for l, wt in cand:
            for h in range(24):
                l["demand"][h] += peak*mult*curve[h]*(wt/tot)*(l["dwell"]/60)/max(l["spaces"],1)
        dests_out.append({"name": name, "lat": dla, "lon": dlo,
                          "demand_now": round(peak*mult*curve[SCENARIO_HOUR], 1)})
    for l in lots:                                   # Hack Day event on top
        wm = walk_min(l["lat"], l["lon"], DEST["lat"], DEST["lon"])
        if wm < 12 and l["usable"] > 0:
            share = l["usable"]*math.exp(-wm/TAU_WALK)
            tot = sum(x["usable"]*math.exp(-walk_min(x["lat"], x["lon"], DEST["lat"], DEST["lon"])/TAU_WALK)
                      for x in lots if walk_min(x["lat"], x["lon"], DEST["lat"], DEST["lon"]) < 12 and x["usable"] > 0)
            for h in range(24):
                l["demand"][h] += HACK_DAY["cars"]*HACK_DAY["curve"][h]*(share/max(tot, 1))*(90/60)/max(l["spaces"], 1)

    # ---- per-hour outputs ----------------------------------------------------
    for l in lots:
        hours = []
        for h in range(24):
            o = min(.99, l["base"][h] + l["demand"][h])
            o_next = min(.99, l["base"][(h+1) % 24] + l["demand"][(h+1) % 24])
            band = .10 + .06*(l["demand"][h] > .02)       # wider where demand layer active
            free_use = max(0.0, l["usable"]*(1-o))
            p_free = 1-math.exp(-free_use/3) if l["usable"] else 0.0
            wait = None
            if o > .9 and l["usable"]:
                turn = l["spaces"]*(1-o)+.5
                wait = round(min(l["dwell"]/max(turn, .5), 60), 1)   # min until a spot frees (queueing approx)
            hours.append({"occ": round(o,3), "lo": round(max(0,o-band),3), "hi": round(min(1,o+band),3),
                          "fill": round(o_next-o,3), "p_free": round(p_free,3), "wait_min": wait})
        l["hours"] = hours
        del l["base"], l["demand"]

    # ---- fly senses at scenario hour ----------------------------------------
    h = SCENARIO_HOUR
    sweet, bitter, loom = [], [], []
    for l in lots:
        hh = l["hours"][h]
        sweet.append(hh["p_free"]*math.exp(-l["walk"]/10)*(1.1 if l["deck"] else 1))  # covered = +sweet
        bitter.append(.55*l["risk"] + .3*min(l["price_hr"]/4, 1) + .15*(l["walk"]/30))
        loom.append(max(0, hh["fill"])*10 + (.6 if hh["occ"] > .85 else 0))
    S, B, L = wins01(sweet), wins01(bitter), wins01(loom)
    senses = []
    for i, l in enumerate(lots):
        l["senses"] = {"sugar_hz": round(200*S[i]), "bitter_hz": round(200*B[i]), "looming_hz": round(150*L[i])}
        senses.append({"lot": l["name"], "walk_min": l["walk"], **l["senses"],
                       "basis": {"p_free": l["hours"][h]["p_free"], "permit_risk": l["risk"],
                                 "fill_per_hr": l["hours"][h]["fill"], "occ": l["hours"][h]["occ"]}})

    os.makedirs(os.path.join(HERE, "web"), exist_ok=True)
    json.dump({"generated_for": {"dest": DEST, "day": SCENARIO_DAY, "hour": h, "persona": PERSONA},
        "source": "NCSU Transportation GIS (official lots, spaces, permit mix)",
        "method": {"baseline": "archetype hour curves blended by each lot's real permit mix",
                   "demand": "destination busyness assigned to lots by gravity (usable capacity x exp(-walk/tau)) + Hack Day event",
                   "upgrade_path": "Popular-Times/live traffic flow replaces assumed curves; sensors replace estimates"},
        "honesty": "Estimates from assumed curves over official static data; no sensor has reported. Signs control.",
        "destinations": dests_out, "lots": lots},
        open(os.path.join(HERE, "web", "data.json"), "w"))
    json.dump({"scenario": f"{SCENARIO_DAY} {h}:00 -> {DEST['name']}", "persona": PERSONA["label"],
               "lots": sorted(senses, key=lambda s: -s["sugar_hz"])[:12]},
              open(os.path.join(HERE, "senses.json"), "w"), indent=1)
    print(f"{len(lots)} lots | senses for top 12 by sugar")
    for s in sorted(senses, key=lambda x: -x["sugar_hz"])[:8]:
        print(f"  {s['lot'][:42]:44s} sugar {s['sugar_hz']:3d} bitter {s['bitter_hz']:3d} loom {s['looming_hz']:3d} walk {s['walk_min']:4.1f}")

if __name__ == "__main__":
    main()
