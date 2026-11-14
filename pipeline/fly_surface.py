#!/usr/bin/env python3
"""
fly_surface.py - run the real connectome and export what the web app needs.

  python3 pipeline/fly_surface.py sanity     -> web/data/fly_sanity.json
  python3 pipeline/fly_surface.py surface    -> web/data/fly_surface.json
  python3 pipeline/fly_surface.py raster     -> web/data/fly_raster.json
  python3 pipeline/fly_surface.py all [--workers 8] [--seeds 3]

The response surface is a grid of (sugar, bitter, looming) input rates. For
each point we run the full 138k-neuron simulation from rest for 200 ms, for
several seeds, on the intact brain and on a brain whose Giant Fibre inputs are
cut. The web app interpolates this table, so every verdict on screen traces
back to real spiking runs. Partial results are saved as it goes.
"""
import argparse
import datetime
import itertools
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flybrain import Brain, WIRING_FILE  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "data")
GRID = {"sugar": [0, 50, 100, 150, 200], "bitter": [0, 50, 100, 200],
        "loom": [0, 50, 100, 150]}
OUTPUTS = ["mn9", "giant_fibre", "mdn", "dnp09"]
MS = 200

_B = None


def brain():
    global _B
    if _B is None:
        _B = Brain()
    return _B


def provenance(b, **extra):
    return {"dataset": "FlyWire FAFB v783 connectome, Shiu et al. 2024 signed connectivity",
            "wiring_file": WIRING_FILE, "n_neurons": int(b.N), "n_connections": b.n_connections,
            "model": "leaky integrate-and-fire, Shiu settings (-52 mV rest, -45 mV threshold, 20 ms membrane, "
                     "5 ms synapse, 2.2 ms refractory, 1.8 ms delay, 0.275 mV/synapse, 0.1 ms step)",
            "ms_per_run": MS, "group_sizes": {k: int(len(v)) for k, v in b.groups.items()},
            "script": "pipeline/fly_surface.py", "notebook": "colab/fly_surface.ipynb",
            "run_date": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), **extra}


def inputs_for(b, s, bt, lm):
    out = []
    if s > 0: out.append((b.groups["sugar"], s))
    if bt > 0: out.append((b.groups["bitter"], bt))
    if lm > 0: out.append((b.groups["looming"], lm))
    return out


def _run(job):
    brainmode, s, bt, lm, seed = job
    b = brain()
    W = None if brainmode == "intact" else b.lesioned("giant_fibre")
    c = b.simulate(inputs_for(b, s, bt, lm), ms=MS, W=W, seed=seed)
    res = {o: b.rate(c, o, MS) for o in OUTPUTS if len(b.groups[o])}
    res["active"] = int((c > 0).sum())
    return job, res


# ------------------------------------------------------------------ sanity
def sanity():
    b = brain()
    G = b.groups
    rows = []

    def add(name, expect, counts, ok, **extra):
        r = {"check": name, "expected": expect,
             "mn9_hz": round(b.rate(counts, "mn9"), 1), "giant_fibre_hz": round(b.rate(counts, "giant_fibre"), 1),
             "mdn_hz": round(b.rate(counts, "mdn"), 1), "neurons_active": int((counts > 0).sum()),
             "pass": bool(ok), **extra}
        rows.append(r); print(r, flush=True)
        return r

    c = b.simulate([]); add("no input", "silence", c, (c > 0).sum() == 0)
    c_s = b.simulate([(G["sugar"], 200)])
    add("sugar 200 Hz", "MN9 fires (eat)", c_s, b.rate(c_s, "mn9") > 10)
    c_sb = b.simulate([(G["sugar"], 200), (G["bitter"], 200)])
    add("sugar 200 + bitter 200 Hz", "MN9 drops a lot", c_sb, b.rate(c_sb, "mn9") < 0.6 * b.rate(c_s, "mn9"))
    c_l = b.simulate([(G["looming"], 150)])
    add("looming 150 Hz", "Giant Fibre fires (escape)", c_l, b.rate(c_l, "giant_fibre") > 0)
    c_ll = b.simulate([(G["looming"], 150)], W=b.lesioned("giant_fibre"))
    add("looming 150 Hz, Giant Fibre inputs cut", "no escape", c_ll, b.rate(c_ll, "giant_fibre") == 0)
    c_st, ex = b.simulate([(G["sugar"], 200)], ms=200, input_until_ms=100, late_from_ms=170)
    late = ex["late"].copy(); late[G["sugar"]] = 0
    add("sugar for 100 ms, then nothing", "activity dies out", c_st, late.sum() == 0,
        spikes_in_last_30ms=int(late.sum()))
    out = {"provenance": provenance(b, seed=0), "checks": rows, "all_pass": all(r["pass"] for r in rows)}
    json.dump(out, open(os.path.join(OUT, "fly_sanity.json"), "w"), indent=1)
    print("sanity all_pass =", out["all_pass"])
    return out


# ----------------------------------------------------------------- surface
def surface(workers, seeds, coarse=False):
    grid = {k: ([v[0], v[len(v) // 2], v[-1]] if coarse else v) for k, v in GRID.items()}
    pts = list(itertools.product(grid["sugar"], grid["bitter"], grid["loom"]))
    jobs = [(m, s, bt, lm, sd) for m in ("intact", "lesion_gf") for (s, bt, lm) in pts for sd in range(seeds)]
    # with the Giant Fibre's inputs cut and no looming, nothing differs from intact only through GF
    # itself; we still run every point so the lesioned table is measured, not assumed.
    print(f"{len(jobs)} runs on {workers} workers", flush=True)
    cache_path = os.path.join(OUT, "fly_runs.partial.json")
    acc = {}
    if os.path.exists(cache_path):
        saved = json.load(open(cache_path))
        for row in saved:
            job = tuple(row["job"])
            if job in jobs:
                acc[job] = row["rates"]
    t0, done = time.time(), len(acc)
    pending = [job for job in jobs if job not in acc]
    print(f"Resuming {done} cached runs; {len(pending)} remain", flush=True)
    path = os.path.join(OUT, "fly_surface.json")

    def dump(final):
        b = brain()
        outs = [o for o in OUTPUTS if len(b.groups[o])]
        table = {}
        for m in ("intact", "lesion_gf"):
            table[m] = {"sd": {}}
            for o in outs:
                mean = np.full((len(grid["sugar"]), len(grid["bitter"]), len(grid["loom"])), np.nan)
                sd = mean.copy()
                for (i, s), (j, bt), (k, lm) in itertools.product(*(enumerate(grid[a]) for a in ("sugar", "bitter", "loom"))):
                    vals = [acc[(m, s, bt, lm, x)][o] for x in range(seeds) if (m, s, bt, lm, x) in acc]
                    if vals:
                        mean[i, j, k] = np.mean(vals); sd[i, j, k] = np.std(vals)
                table[m][o] = np.round(mean, 2).tolist()
                table[m]["sd"][o] = np.round(sd, 2).tolist()
        doc = {"provenance": provenance(b, seeds=list(range(seeds)), n_runs=done, complete=final,
                                        lesion="giant_fibre (DNp01) input synapses cut: W @ diag(keep)"),
               "grid": grid, "axes": ["sugar", "bitter", "loom"], "units": "Hz", **table}
        target = path if final else path.replace(".json", ".partial.json")
        json.dump(json.loads(json.dumps(doc).replace("NaN", "null")), open(target, "w"))
        if final and os.path.exists(path.replace(".json", ".partial.json")):
            os.remove(path.replace(".json", ".partial.json"))

    with Pool(workers, initializer=brain) as pool:
        for job, res in pool.imap_unordered(_run, pending):
            acc[job] = res; done += 1
            if done % 10 == 0 or done == len(jobs):
                temp = cache_path + ".tmp"
                with open(temp, "w") as f:
                    json.dump([{"job": list(j), "rates": r} for j, r in acc.items()], f)
                os.replace(temp, cache_path)
                el = time.time() - t0
                print(f"  {done}/{len(jobs)}  {el:.0f}s  eta {el / done * (len(jobs) - done):.0f}s", flush=True)
                dump(done == len(jobs))
    if done == len(jobs): dump(True)
    print("wrote", path)


# ------------------------------------------------------------------ raster
def raster():
    b = brain()
    G = b.groups
    rng = np.random.default_rng(1)
    pick = lambda g, n: rng.choice(G[g], size=min(n, len(G[g])), replace=False)
    groups = [("sugar", pick("sugar", 20)), ("bitter", pick("bitter", 20)), ("looming", pick("looming", 40)),
              ("mn9", G["mn9"]), ("giant_fibre", G["giant_fibre"]), ("mdn", G["mdn"])]
    scen = {"sweet close lot": (200, 0, 0), "uncertain lot": (120, 150, 0), "lot filling fast": (120, 50, 150)}
    # other neurons: the most active ones in these scenarios, so the raster shows the brain working
    tot = np.zeros(b.N, int)
    for (s, bt, lm) in scen.values():
        tot += b.simulate(inputs_for(b, s, bt, lm))
    taken = np.concatenate([g for _, g in groups])
    tot[taken] = 0
    active = np.flatnonzero(tot > 0)
    other = rng.choice(active, size=min(220, len(active)), replace=False)
    groups.append(("interneurons (sample of active)", other))
    track = np.concatenate([g for _, g in groups])
    bounds, start = [], 0
    for name, g in groups:
        bounds.append({"group": name, "from": start, "to": start + len(g)}); start += len(g)
    out = {"provenance": provenance(b, seed=0, tracked=int(len(track))), "ms": MS, "rows": bounds, "scenarios": []}
    for name, (s, bt, lm) in scen.items():
        c, ex = b.simulate(inputs_for(b, s, bt, lm), track=track)
        out["scenarios"].append({"name": name, "sugar_hz": s, "bitter_hz": bt, "loom_hz": lm,
                                 "mn9_hz": round(b.rate(c, "mn9"), 1), "giant_fibre_hz": round(b.rate(c, "giant_fibre"), 1),
                                 "mdn_hz": round(b.rate(c, "mdn"), 1), "neurons_active": int((c > 0).sum()),
                                 "t": [p[0] for p in ex["spikes"]], "n": [p[1] for p in ex["spikes"]]})
        print(name, len(ex["spikes"]), "spikes", flush=True)
    json.dump(out, open(os.path.join(OUT, "fly_raster.json"), "w"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["sanity", "surface", "raster", "all", "time"])
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--coarse", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.what == "time":
        b = brain(); t = time.time()
        c = b.simulate([(b.groups["sugar"], 200)])
        print(f"N={b.N} nnz={b.n_connections} one run {time.time() - t:.1f}s mn9={b.rate(c, 'mn9'):.1f}Hz",
              {k: len(v) for k, v in b.groups.items()})
    if a.what in ("sanity", "all"):
        if not sanity()["all_pass"]:
            sys.exit("Sanity failed; response surface blocked")
    if a.what in ("surface", "all"): surface(a.workers, a.seeds, a.coarse)
    if a.what in ("raster", "all"): raster()
