#!/usr/bin/env python3
"""
Park Shark x Fly Brain - NC State. v3: both days precomputed, street-graph
journeys for per-hop brain decisions, per-day permit rules.

DATA LAYERS (exactly what is real vs assumed):
  REAL (official NCSU Transportation GIS): lot polygons, names, zones,
       SPACES, per-permit-type space counts (incl. HC, EV, PY, V), deck/surface.
  ASSUMED (written by us, labeled, each with a live upgrade path):
       - 4 archetype hour curves (commuter/resident/visitor/service)
         -> upgrade: per-lot history once sensors/gate counts exist
       - 9 destination busyness curves + peak cars/h
         -> upgrade: Google Popular Times (live + historical), NCSU course
            schedule (weekday), gopack events
       - campus traffic congestion hour curve on graph edges
         -> upgrade: TomTom/HERE flow on real OSM street segments
       - weekend permit relaxation, avg dwell times, walk speed
  DERIVED: occupancy=baseline(permit mix)+gravity-assigned demand; band;
       P(open usable spot); fill rate; wait-or-drive; fly senses.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "ncstate_parking_raw.geojson")
STREETS = os.path.join(HERE, "ncstate_streets.geojson")   # optional: real OSM streets

DEST = {"name": "Riddick Hall (Hack Day venue)", "lat": 35.7867, "lon": -78.6688,
        "coord_basis": "approximate - set exact pin before demo"}
SCEN = {"sat": 12, "weekday": 10}          # hour snapshot per day for the notebook
PERSONA = {"label": "student driving to Hack Day, no NCSU permit", "permit_zone": None,
           "willing_to_pay": True}
AVG_DWELL = {"visitor": 90, "pay": 110, "commuter": 300, "deck": 240, "resident": 900}

ARCH = {
 "commuter": [.08,.06,.05,.05,.06,.08,.18,.45,.72,.88,.93,.95,.94,.93,.90,.82,.68,.50,.35,.25,.18,.14,.11,.09],
 "resident": [.92,.93,.94,.94,.94,.93,.88,.78,.65,.55,.50,.48,.47,.48,.52,.58,.68,.78,.85,.88,.90,.91,.92,.92],
 "visitor":  [.05,.04,.04,.04,.05,.06,.10,.25,.50,.68,.75,.78,.78,.75,.70,.62,.52,.42,.33,.27,.22,.15,.09,.06],
 "service":  [.10,.08,.08,.08,.10,.15,.35,.60,.75,.80,.80,.78,.76,.75,.72,.65,.50,.35,.25,.18,.14,.12,.11,.10],
}
SATM = {"commuter": .15, "resident": .95, "visitor": .45, "service": .25}
# assumed campus street congestion by hour, 0..1 (upgrade: TomTom flow)
TRAF = {"weekday": [.05,.03,.02,.02,.03,.08,.25,.55,.80,.65,.50,.55,.60,.55,.55,.65,.80,.90,.70,.45,.30,.20,.12,.08],
        "sat":     [.04,.02,.02,.02,.02,.03,.06,.10,.18,.28,.35,.40,.42,.40,.38,.35,.32,.30,.28,.25,.18,.12,.08,.05]}

PCOLS = {"A4":"commuter","AB":"commuter","AS_":"service","B":"commuter","C":"commuter",
 "C_CC":"commuter","C_DD":"commuter","CD":"commuter","CL":"commuter","F":"commuter",
 "GV":"service","LD":"service","LO":"service","PY":"visitor","RC":"resident","RD":"resident",
 "RE":"resident","RF":"resident","RH_CC":"resident","RS":"resident","RV":"resident",
 "RW":"resident","SV":"service","SV_UV":"service","UE":"service","UV":"service",
 "V":"visitor","VC":"visitor","VP":"visitor","W":"commuter","ZIP":"visitor","RCS":"resident","C_CB":"commuter"}
RES = [c for c,k in PCOLS.items() if k=="resident"]; VIS=["PY","V","VC","VP","ZIP"]

DESTS = [  # name, lat, lon, peak cars/h (ASSUMED), curve shape, sat multiplier
 ("Riddick / engineering NE", 35.7867,-78.6688, 60,"class",1.0),
 ("D.H. Hill Library", 35.7876,-78.6694, 50,"library",.45),
 ("Talley Student Union", 35.7838,-78.6709, 70,"social",.55),
 ("Carmichael Gym", 35.7832,-78.6671, 45,"gym",.60),
 ("Bell Tower / Holladay", 35.7859,-78.6637, 30,"class",.20),
 ("Hunt Library (Centennial)", 35.7702,-78.6766, 45,"library",.40),
 ("EB I-III / Oval Dr (Centennial)", 35.7716,-78.6737, 60,"class",.20),
 ("McKimmon Center", 35.7817,-78.6855, 40,"events",.70),
 ("Reynolds Coliseum", 35.7840,-78.6688, 25,"events",.50),
]
SHAPES = {
 "class":  [0,0,0,0,0,.05,.15,.5,.9,1,.95,.9,.85,.9,.85,.7,.5,.3,.15,.1,.05,0,0,0],
 "library":[.05,.02,0,0,0,0,.05,.15,.4,.6,.7,.75,.8,.85,.9,.95,1,.95,.9,.85,.8,.6,.3,.1],
 "social": [.05,.02,0,0,0,0,.1,.3,.5,.6,.8,1,.95,.8,.7,.7,.8,.9,.85,.7,.5,.3,.15,.08],
 "gym":    [0,0,0,0,0,.2,.5,.6,.5,.4,.4,.5,.6,.5,.5,.6,.8,1,.95,.8,.6,.4,.2,.05],
 "events": [0,0,0,0,0,0,.1,.3,.6,.8,.8,.7,.7,.7,.6,.5,.4,.5,.7,.8,.6,.3,.1,0],
}
HACK = {"cars":35, "curve":[0]*8+[.6,1,1,.9,.9,1,.9,.7,.3]+[0]*7}
GATES = [  # campus entry points for the fly's journey (coords APPROX)
 ("Hillsborough St / Dan Allen", 35.7901,-78.6712),
 ("Western Blvd / Dan Allen", 35.7827,-78.6757),
 ("Avent Ferry / Western", 35.7800,-78.6797),
 ("Centennial: Main Campus Dr", 35.7718,-78.6815),
]
TAU = 6.0; MPM = 80.0

def centroid(g):
    rings = g["coordinates"] if g["type"]=="Polygon" else max(g["coordinates"], key=lambda r: len(r[0]))
    pts = rings[0]
    return sum(p[1] for p in pts)/len(pts), sum(p[0] for p in pts)/len(pts)

def dmin(a_lat,a_lon,b_lat,b_lon):
    dx=(a_lon-b_lon)*111320*math.cos(math.radians(a_lat)); dy=(a_lat-b_lat)*110540
    return math.hypot(dx,dy)*1.35/MPM

def wins01(vals):
    m=sum(vals)/len(vals); sd=(sum((v-m)**2 for v in vals)/len(vals))**.5 or 1
    cl=[min(max(v,m-2*sd),m+2*sd) for v in vals]; lo,hi=min(cl),max(cl)
    return [(v-lo)/(hi-lo) if hi>lo else .5 for v in cl]

def main():
    fc=json.load(open(RAW)); lots=[]
    for f in fc["features"]:
        p,g=f["properties"],f["geometry"]; spaces=p.get("SPACES") or 0
        if not g or spaces<5: continue
        la,lo=centroid(g); w=dmin(la,lo,DEST["lat"],DEST["lon"])
        if w>30: continue
        mix={}
        for c,k in PCOLS.items():
            n=p.get(c) or 0
            if n>0: mix[k]=mix.get(k,0)+n
        if not mix: mix={"commuter":spaces}
        tot=sum(mix.values()); deck="deck" in (p.get("Type") or "").lower()
        vis=sum(p.get(c) or 0 for c in VIS); res=sum(p.get(c) or 0 for c in RES)
        prof=max(mix,key=mix.get)
        dwell=AVG_DWELL["deck" if deck else {"commuter":"commuter","resident":"resident","visitor":"visitor","service":"commuter"}[prof]]
        use={}; risk={}
        base_use=min(max(vis+(p.get(PERSONA["permit_zone"]) or 0 if PERSONA["permit_zone"] else 0),0),spaces)
        use["weekday"]=base_use; use["sat"]=min(max(base_use,spaces-res),spaces)
        for d in use: risk[d]=max(0.,1-use[d]/spaces) if spaces else 1.
        base={d:[sum(ARCH[k][h]*(n/tot)*(SATM[k] if d=="sat" else 1) for k,n in mix.items())
                 for h in range(24)] for d in ("weekday","sat")}
        lots.append(dict(name=p.get("NAME") or f"Lot {p.get('OBJECTID')}",lat=la,lon=lo,
            spaces=spaces,zone=(p.get("ZONE_") or "").strip(),type=p.get("Type"),deck=deck,
            profile=prof,hc=p.get("HC") or 0,ev=p.get("EV") or 0,pay=vis,
            price_hr=2. if vis else 0.,walk=round(w,1),dwell=dwell,
            usable=use,risk={k:round(v,3) for k,v in risk.items()},
            base=base,dem={d:[0.]*24 for d in base},ring=g))

    dests_out=[]
    for name,dla,dlo,peak,shape,satm in DESTS:
        curve=SHAPES[shape]
        cand=[(l,dmin(l["lat"],l["lon"],dla,dlo)) for l in lots]
        for d in ("weekday","sat"):
            mult=satm if d=="sat" else 1.
            cc=[(l,l["usable"][d]*math.exp(-wm/TAU)) for l,wm in cand if wm<12 and l["usable"][d]>0]
            t=sum(w for _,w in cc) or 1
            for l,wt in cc:
                for h in range(24):
                    l["dem"][d][h]+=peak*mult*curve[h]*(wt/t)*(l["dwell"]/60)/max(l["spaces"],1)
        dests_out.append({"name":name,"lat":dla,"lon":dlo,"peak_cars_hr":peak,"shape":shape,
                          "basis":"ASSUMED curve - upgrade: Google Popular Times / course schedule"})
    for d in ("weekday","sat"):  # Hack Day event (sat only in reality; keep sat)
        if d!="sat": continue
        cc=[(l,l["usable"][d]*math.exp(-dmin(l["lat"],l["lon"],DEST["lat"],DEST["lon"])/TAU))
            for l in lots if dmin(l["lat"],l["lon"],DEST["lat"],DEST["lon"])<12 and l["usable"][d]>0]
        t=sum(w for _,w in cc) or 1
        for l,wt in cc:
            for h in range(24):
                l["dem"][d][h]+=HACK["cars"]*HACK["curve"][h]*(wt/t)*1.5/max(l["spaces"],1)

    for l in lots:
        l["hours"]={}
        for d in ("weekday","sat"):
            hh=[]
            for h in range(24):
                o=min(.99,l["base"][d][h]+l["dem"][d][h]); on=min(.99,l["base"][d][(h+1)%24]+l["dem"][d][(h+1)%24])
                band=.10+.06*(l["dem"][d][h]>.02)
                fu=max(0.,l["usable"][d]*(1-o)); pf=1-math.exp(-fu/3) if l["usable"][d] else 0.
                wait=round(min(l["dwell"]/max(l["spaces"]*(1-o)+.5,.5),60),1) if o>.9 and l["usable"][d] else None
                hh.append({"occ":round(o,3),"lo":round(max(0,o-band),3),"hi":round(min(1,o+band),3),
                           "fill":round(on-o,3),"p_free":round(pf,3),"wait_min":wait})
            l["hours"][d]=hh
        del l["base"],l["dem"]

    # ---------------- journey graph: lots + gates + dest, k-NN edges ----------
    nodes=[{"id":"dest","name":DEST["name"],"lat":DEST["lat"],"lon":DEST["lon"],"kind":"dest"}]
    nodes+=[{"id":f"gate{i}","name":n,"lat":la,"lon":lo,"kind":"gate"} for i,(n,la,lo) in enumerate(GATES)]
    nodes+=[{"id":f"lot{i}","name":l["name"],"lat":l["lat"],"lon":l["lon"],"kind":"lot"} for i,l in enumerate(lots)]
    edges=[]
    for i,a in enumerate(nodes):
        ds=sorted(((dmin(a["lat"],a["lon"],b["lat"],b["lon"]),j) for j,b in enumerate(nodes) if j!=i))
        for w,j in ds[:5]:
            if w<9 and (min(i,j),max(i,j)) not in {(e["a"],e["b"]) for e in edges}:
                edges.append({"a":min(i,j),"b":max(i,j),"walk_min":round(w,1),
                              "drive_min":round(w*MPM/450,2)})   # ~27 km/h campus driving
    graph={"nodes":nodes,"edges":edges,"traffic_curve":TRAF,
           "traffic_basis":"ASSUMED campus congestion by hour; upgrade: TomTom/HERE flow on OSM segments",
           "edges_basis":"straight-line k-NN; upgrade: real OSM street graph (ncstate_streets.geojson)"}

    # ---------------- senses snapshots + journey spec for the notebook -------
    out_scen={}
    for d,h in SCEN.items():
        sweet,bitter,loom=[],[],[]
        for l in lots:
            hh=l["hours"][d][h]
            sweet.append(hh["p_free"]*math.exp(-l["walk"]/10)*(1.1 if l["deck"] else 1))
            bitter.append(.55*l["risk"][d]+.3*min(l["price_hr"]/4,1)+.15*(l["walk"]/30))
            loom.append(max(0,hh["fill"])*10+(.6 if hh["occ"]>.85 else 0))
        S,B,L=wins01(sweet),wins01(bitter),wins01(loom)
        rows=[]
        for i,l in enumerate(lots):
            rows.append({"lot":l["name"],"node":f"lot{i}","walk_min":l["walk"],
                "sugar_hz":round(200*S[i]),"bitter_hz":round(200*B[i]),"looming_hz":round(150*L[i]),
                "basis":{"p_free":l["hours"][d][h]["p_free"],"permit_risk":l["risk"][d],
                         "fill_per_hr":l["hours"][d][h]["fill"],"occ":l["hours"][d][h]["occ"]}})
        out_scen[d]={"hour":h,"lots":sorted(rows,key=lambda r:-r["sugar_hz"])[:14]}

    os.makedirs(os.path.join(HERE,"web"),exist_ok=True)
    json.dump({"generated_for":{"dest":DEST,"scenarios":SCEN,"persona":PERSONA},
        "source":"NCSU Transportation GIS (official lots, spaces, permit mix)",
        "assumed":"archetype curves, destination curves, traffic curve, weekend rules - see build_ncstate.py header",
        "destinations":dests_out,"lots":lots,"graph":graph},
        open(os.path.join(HERE,"web","data.json"),"w"))
    json.dump({"persona":PERSONA["label"],"dest_node":"dest","scenarios":out_scen,"graph":graph},
        open(os.path.join(HERE,"senses.json"),"w"))
    print(f"{len(lots)} lots, {len(nodes)} nodes, {len(edges)} edges")
    for d in SCEN:
        top=out_scen[d]["lots"][0]
        print(f"  {d} {SCEN[d]}:00 sweetest: {top['lot']} (sugar {top['sugar_hz']}, loom {top['looming_hz']})")

if __name__=="__main__": main()
