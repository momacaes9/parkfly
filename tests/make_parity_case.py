#!/usr/bin/env python3
"""Write tests/parity_case.json: fixed inputs + the Python model's outputs, for the JS parity test."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))
import evaluate, model, senses
from common import jload, jdump, ROOT

L, truth, days, geo = evaluate.load()
fit = truth["fitted"]; nL = len(L); N = [l["spaces"] for l in L]
rng = np.random.default_rng(42)
cases = []
for (di, ti, pct) in [(0, 54, 25), (1, 30, 10), (3, 120, 40), (4, 60, 0)]:
    kind = days[di]["day"]
    per = 0 if truth["start_min"] + ti * truth["step_min"] < fit["tau_pm_from_min"] else 1
    S = [model.occ_matrix(N[i], fit["tau"][i][per]) for i in range(nL)]
    masks = [model.place("scatter", int(round(pct / 100 * N[i])), geo[i]["xy"], geo[i]["ent_d"], N[i], rng) for i in range(nL)]
    if pct == 40: masks[2][:] = True
    occs = [days[di]["occ"][i][ti] for i in range(nL)]
    mu = np.array(fit["prior"][kind]["mu"])[:, ti]; sd = np.array(fit["prior"][kind]["sd"])[:, ti]
    across = {"D": np.array(fit["across"]["D"]), "rho0": fit["across"]["rho0"], "ell": fit["across"]["ell_m"]}
    for use in (False, True):
        post = model.infer(S, occs, masks, mu, sd, across if use else None)
        surf = senses.Surface(jload("fly_surface.json"))
        ts = [senses.tastes(N[i], post[i]["p_occ"], post[i]["post"], S[i], masks[i], occs[i], L[i]["walk_min"],
                            L[i]["price_hr"], 0.0, 0.02) for i in range(nL)]
        hz = [senses.to_hz(t) for t in ts]
        reads = [surf.read(*h) for h in hz]
        pick, v = senses.fly_pick(reads, hz)
        cases.append({"day": di, "ti": ti, "period": per, "across": use, "masks": [m.astype(int).tolist() for m in masks],
                      "p_occ": [np.round(p["p_occ"], 6).tolist() for p in post],
                      "f_mean": [round(p["f_mean"], 6) for p in post], "prior_s": [round(p["prior_s"], 6) for p in post],
                      "f10": [p["f10"] for p in post], "f90": [p["f90"] for p in post],
                      "naive": [round(model.naive(occs[i], masks[i]), 6) for i in range(nL)],
                      "tastes": [[round(t[k], 6) for k in ("sugar", "bitter", "loom", "e_free", "sd_free", "p_full")] for t in ts],
                      "reads": [[round(r[k], 4) for k in ("mn9", "giant_fibre", "mdn")] for r in reads],
                      "pick": int(pick), "verdicts": v})
jdump({"cases": cases}, "parity_case.json", base=os.path.join(ROOT, "tests"))
