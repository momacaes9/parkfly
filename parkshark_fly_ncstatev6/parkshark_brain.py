#!/usr/bin/env python3
"""
Whole-brain fly decisions for Park Shark, run locally.
LIF simulator per Shiu et al. 2024 parameters, same structure as the hack-day
starter notebook (numpy port). Produces decisions.json + journey.json for web/.
Usage: python3 parkshark_brain.py [sanity|run DAY]
"""
import json, math, sys, time
import numpy as np, pandas as pd, scipy.sparse as sp

SHIU = "/home/claude/philshiu/drosophila_brain_model/"
ANN = "/home/claude/flyconnectome/flywire_annotations/supplemental_files/Supplemental_file1_neuron_annotations.tsv"
HERE = "/home/claude/ncstate/"

print("loading brain...", flush=True)
neurons = pd.read_csv(SHIU + "Completeness_783.csv", index_col=0)
wiring = pd.read_parquet(SHIU + "Connectivity_783.parquet")
labels = pd.read_csv(ANN, sep="\t", low_memory=False)
N = len(neurons)
W = sp.csr_matrix((wiring["Excitatory x Connectivity"],
                   (wiring["Presynaptic_Index"], wiring["Postsynaptic_Index"])), shape=(N, N))
WT = W.T.tocsr()
row = {rid: i for i, rid in enumerate(neurons.index)}

def find(mask):
    return np.array([row[r] for r in labels.root_id[mask] if r in row])

sugar       = find(labels.cell_type == "LB3c")
bitter      = find(labels.cell_sub_class == "bitter")
looming     = find(labels.cell_type.isin(["LC4", "LPLC2"]))
giant_fibre = find(labels.cell_type == "DNp01")
mdn         = find(labels.cell_type == "MDN")
mn9         = np.array([row[720575940660219265]])
print({k: len(v) for k, v in dict(sugar=sugar, bitter=bitter, looming=looming,
       giant_fibre=giant_fibre, mdn=mdn, mn9=mn9).items()}, f"| N={N}, nnz={W.nnz}", flush=True)

def simulate(inputs, ms=200, Wt=WT, seed=0):
    dt, v0, vth, tm, ts, ref = 0.1, -52.0, -45.0, 20.0, 5.0, 2.2
    wsyn, kick, delay = 0.275, 250 * 0.275, int(1.8 / 0.1)
    rng = np.random.default_rng(seed)
    v, g = np.full(N, v0), np.zeros(N)
    last, counts = np.full(N, -1e9), np.zeros(N, np.int32)
    ring = np.zeros((delay, N))
    steps = int(ms / dt)
    decay = dt / ts
    for k in range(steps):
        t, slot = k * dt, k % delay
        g += ring[slot]; ring[slot] = 0.0
        for idx, hz in inputs:                       # external Poisson drive
            if hz > 0:
                fire = rng.random(len(idx)) < hz * dt / 1000.0
                if fire.any(): g[idx[fire]] += kick
        free = (t - last) > ref
        v[free] += dt * (v0 - v[free] + g[free]) / tm
        g -= decay * g
        spk = (v >= vth) & free
        if spk.any():
            si = np.flatnonzero(spk)
            counts[si] += 1; last[si] = t; v[si] = v0
            ring[slot] += wsyn * np.asarray(W[si].sum(axis=0)).ravel()  # delivered `delay` steps later
    return counts

def rate(c, idx, ms=200): return float(c[idx].mean() * 1000.0 / ms)

def sanity():
    t0 = time.time()
    tests = {"nothing": [], "sugar": [(sugar, 200)], "sugar+bitter": [(sugar, 200), (bitter, 200)],
             "looming": [(looming, 150)]}
    out = {}
    for name, inp in tests.items():
        c = simulate(inp)
        out[name] = dict(mn9=round(rate(c, mn9), 1), gf=round(rate(c, giant_fibre), 1),
                         mdn=round(rate(c, mdn), 1), active=int((c > 0).sum()))
        print(f"{name:14s} {out[name]}  [{time.time()-t0:.0f}s]", flush=True)
    ok = (out["nothing"]["active"] < 50 and out["sugar"]["mn9"] > 20
          and out["sugar+bitter"]["mn9"] < out["sugar"]["mn9"] * 0.6
          and out["looming"]["gf"] > 5)
    print("SANITY", "PASS" if ok else "FAIL", flush=True)
    return ok

def brain(s_hz, b_hz, l_hz, seed=0, Wt=WT):
    inp = [(g_, hz) for g_, hz in [(sugar, s_hz), (bitter, b_hz), (looming, l_hz)] if hz > 0]
    c = simulate(inp, seed=seed, Wt=Wt)
    return rate(c, mn9), rate(c, giant_fibre), rate(c, mdn)

def verdict(e, f, b):
    if f > e: return "FLEE"
    if e < 5: return "BACK"      # no appetite either way
    return "BACK" if b > e else "EAT"

def run(day, journeys_only=False):
    SJ = json.load(open(HERE + "senses.json"))
    SC, G = SJ["scenarios"][day], SJ["graph"]
    hour = SC["hour"]; traf = G["traffic_curve"][day][hour]
    nodes = {n["id"]: n for n in G["nodes"]}
    nbrs = {}
    for e in G["edges"]:
        a, b = G["nodes"][e["a"]]["id"], G["nodes"][e["b"]]["id"]
        nbrs.setdefault(a, []).append((b, e)); nbrs.setdefault(b, []).append((a, e))
    def dist(u, v):
        a, b = nodes[u], nodes[v]
        dx = (a["lon"]-b["lon"])*111320*math.cos(math.radians(a["lat"])); dy = (a["lat"]-b["lat"])*110540
        return math.hypot(dx, dy)

    rows = []
    if journeys_only:
        rows = json.load(open(HERE + "web/decisions.json"))["decisions"]
    for l in ([] if journeys_only else SC["lots"]):
        e, f, b = brain(l["sugar_hz"], l["bitter_hz"], l["looming_hz"])
        rows.append({**{k: l[k] for k in ("lot","node","walk_min","sugar_hz","bitter_hz","looming_hz")},
                     "eat_mn9_hz": round(e,1), "flee_gf_hz": round(f,1), "back_mdn_hz": round(b,1),
                     "verdict": verdict(e,f,b)})
        print(f"  lot {l['lot'][:36]:38s} eat {e:5.1f} flee {f:5.1f} back {b:5.1f} -> {verdict(e,f,b)}", flush=True)
    rows.sort(key=lambda r: -r["eat_mn9_hz"])
    targets = [r["node"] for r in rows if r["verdict"] == "EAT"] or [r["node"] for r in rows]

    def journey(gate, seed):
        tq = list(targets); target = tq.pop(0); u = gate; path = []
        for step in range(24):
            cands = sorted(nbrs.get(u, []), key=lambda x: dist(x[0], target))[:3]
            if not cands: break
            best = None
            for v, e in cands:
                prog = (dist(u, target) - dist(v, target)) / max(dist(u, target), 1)
                tl = next((l for l in SC["lots"] if l["node"] == target), None)
                s = min(round(200*max(0, min(1, .5+.5*prog))*(1.2 if v == target else 1)), 200)
                bz = min(round(180*traf*min(e["drive_min"]/2, 1)), 200)
                lm = min(round((tl["looming_hz"] if tl else 0)*(1 if v == target else .4)), 150)
                ee, ff, bb = brain(s, bz, lm, seed=seed+step)
                vd = verdict(ee, ff, bb)
                path.append({"from": u, "to": v, "sugar": s, "bitter": bz, "loom": lm,
                             "eat": round(ee,1), "flee": round(ff,1), "back": round(bb,1),
                             "verdict": vd, "taken": False})
                if vd == "FLEE" and v == target and tq:
                    target = tq.pop(0); path[-1]["diverted_to"] = nodes[target]["name"]
                if vd != "FLEE" and (best is None or ee > best[2]): best = (v, e, ee)
            if best is None: best = (cands[0][0], cands[0][1], 0)
            for p in reversed(path):
                if p["from"] == u and p["to"] == best[0]: p["taken"] = True; break
            u = best[0]
            if u == target or dist(u, target) < 150:
                return {"seed": seed, "gate": gate, "final": nodes[target]["name"], "arrived": True, "path": path}
        return {"seed": seed, "gate": gate, "final": nodes[u]["name"], "arrived": False, "path": path}

    flies = []
    for s in (1, 2, 3):
        f = journey("gate0", s)
        hops = sum(1 for p in f["path"] if p["taken"])
        print(f"  fly seed {s}: {hops} hops -> {f['final']} ({'landed' if f['arrived'] else 'searching'})", flush=True)
        flies.append(f)

    json.dump({"day": day, "hour": hour, "persona": SJ["persona"], "decisions": rows},
              open(HERE + "web/decisions.json", "w"))
    json.dump({"day": day, "hour": hour, "flies": flies}, open(HERE + "web/journey.json", "w"))
    print("wrote web/decisions.json + web/journey.json for", day, flush=True)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "sanity"
    if mode == "sanity": sanity()
    else: run(sys.argv[2] if len(sys.argv) > 2 else "weekday", journeys_only=(mode=="journeys"))
