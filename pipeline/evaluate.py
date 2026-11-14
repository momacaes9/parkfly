#!/usr/bin/env python3
"""
evaluate.py - every number the demo quotes about the simulated lots.

On held-out simulated test weekdays (seeds never used to fit tau or priors):
  1. sensor density vs accuracy: model vs the naive baseline, 0..95% sensed
  2. spillover: the same curve with the across-lot Gaussian switched on
  3. sensor placement: entrance-clustered vs spread vs frontier vs scattered
  4. decisions: the fly (measured connectome surface) vs no-neuron baselines
Writes web/data/results.json and results/*.png. Seeds fixed.
"""
import base64, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import jload, jdump, RESULTS, to_m
import model, senses

PCTS = list(range(0, 100, 5))
PLACE_PCTS = [10, 15, 20, 25, 30, 40, 50]
STRATS = ["scatter", "spread", "entrance", "frontier"]
N_MASKS = 4
FULL_PENALTY_MIN = 5.0      # ASSUMED minutes lost when the chosen lot turns out full


def load():
    lots = jload("lots.json"); truth = jload("truth.json")
    L = lots["lots"]; nL = len(L); T = truth["n_steps"]
    days = []
    for d in truth["days"]:
        occ = []
        for i in range(nL):
            n = L[i]["spaces"]
            bits = np.unpackbits(np.frombuffer(base64.b64decode(d["occ"][i]), np.uint8))[:T * n]
            occ.append(bits.reshape(T, n).astype(bool))
        days.append({**d, "occ": occ})
    geo = []
    for l in L:
        xy = np.array([to_m(a, b) for a, b in l["spots"]])
        e = np.array(to_m(*l["entrance"]))
        geo.append({"xy": xy, "ent_d": np.linalg.norm(xy - e, axis=1)})
    return L, truth, days, geo


def main():
    L, truth, days, geo = load()
    nL = len(L); fit = truth["fitted"]; T = truth["n_steps"]
    tmin = truth["start_min"] + np.arange(T) * truth["step_min"]
    N = [l["spaces"] for l in L]
    Sam = [model.occ_matrix(N[i], fit["tau"][i][0]) for i in range(nL)]
    Spm = [model.occ_matrix(N[i], fit["tau"][i][1]) for i in range(nL)]
    S_at = lambda ti: Sam if tmin[ti] < fit["tau_pm_from_min"] else Spm
    across = {"D": np.array(fit["across"]["D"]), "rho0": fit["across"]["rho0"], "ell": fit["across"]["ell_m"]}
    mu = np.array(fit["prior"]["weekday"]["mu"]); sd = np.array(fit["prior"]["weekday"]["sd"])
    day_sel = (tmin >= 8 * 60) & (tmin <= 17 * 60)
    frontier = [mu[i][day_sel] * N[i] for i in range(nL)]
    wk = [d for d in days if d["day"] == "weekday"]
    times = [ti for ti in range(T) if tmin[ti] >= 7 * 60 and tmin[ti] <= 18 * 60 and (tmin[ti] % 30) == 0]

    def masks_for(strategy, pct, rng):
        return [model.place(strategy, int(round(pct / 100 * N[i])), geo[i]["xy"], geo[i]["ent_d"], N[i], rng,
                            frontier[i]) for i in range(nL)]

    def score(strategy, pct, use_across, seed=0):
        rng = np.random.default_rng(1000 + seed + pct)
        rows = []
        for d in wk:
            for ti in times:
                for _ in range(N_MASKS if strategy in ("scatter", "spread") else 1):
                    masks = masks_for(strategy, pct, rng)
                    occs = [d["occ"][i][ti] for i in range(nL)]
                    post = model.infer(S_at(ti), occs, masks, mu[:, ti], sd[:, ti], across if use_across else None)
                    pm, pn, tr = [], [], []
                    fe_m = fe_n = 0.0; right_m = right_n = 0; tot = 0
                    for i in range(nL):
                        u = ~masks[i]
                        nv = model.naive(occs[i], masks[i])
                        pm.append(post[i]["p_occ"][u]); tr.append(occs[i][u])
                        pn.append(np.full(u.sum(), nv))
                        true_free = (~occs[i][u]).sum()               # free spots among the unsensed
                        fe_m += abs((1 - post[i]["p_occ"][u]).sum() - true_free)
                        fe_n += abs((1 - nv) * u.sum() - true_free)
                        right_m += masks[i].sum() + ((post[i]["p_occ"][u] > 0.5) == occs[i][u]).sum()
                        right_n += masks[i].sum() + ((nv > 0.5) == occs[i][u]).sum()
                        tot += N[i]
                    pm, pn, tr = map(np.concatenate, (pm, pn, tr))
                    rows.append(model.metrics(pm, tr) + model.metrics(pn, tr) + (tmin[ti] < fit["tau_pm_from_min"],
                                right_m / tot, right_n / tot, fe_m / nL, fe_n / nL))
        a = np.array(rows, float)
        out = {}
        for j, k in enumerate(["acc", "brier", "logloss"]):
            out["model_" + k] = [round(float(a[:, j].mean()), 4), round(float(a[:, j].std()), 4)]
            out["naive_" + k] = [round(float(a[:, 3 + j].mean()), 4), round(float(a[:, 3 + j].std()), 4)]
        for j, k in ((7, "model_map_acc"), (8, "naive_map_acc"), (9, "model_free_mae"), (10, "naive_free_mae")):
            out[k] = [round(float(a[:, j].mean()), 4), round(float(a[:, j].std()), 4)]
        am = a[:, 6] > 0.5
        out["model_brier_am"], out["model_brier_pm"] = round(float(a[am, 1].mean()), 4), round(float(a[~am, 1].mean()), 4)
        out["naive_brier_am"], out["naive_brier_pm"] = round(float(a[am, 4].mean()), 4), round(float(a[~am, 4].mean()), 4)
        out["n_evals"] = len(rows)
        return out

    res = {"label": "Computed by pipeline/evaluate.py on SIMULATED held-out weekdays",
           "test_days": [d["id"] for d in wk], "train_seeds": fit["train_seeds"],
           "eval_times": "every 30 min, 07:00-18:00", "masks_per_eval": N_MASKS, "pcts": PCTS}
    print("density curve ...", flush=True)
    res["density"] = {"within": [score("scatter", p, False) for p in PCTS],
                      "spill": [score("scatter", p, True) for p in PCTS]}
    for p in (10, 25, 50):
        w, s = res["density"]["within"][PCTS.index(p)], res["density"]["spill"][PCTS.index(p)]
        print(f"  {p:3d}% sensed  Brier model {w['model_brier'][0]:.3f}  +spill {s['model_brier'][0]:.3f}  "
              f"naive {w['naive_brier'][0]:.3f} | acc {w['model_acc'][0]:.3f} vs {w['naive_acc'][0]:.3f}")
    print("placement ...", flush=True)
    res["placement"] = {"pcts": PLACE_PCTS, "cluster_size": model.CLUSTER,
                        "strategies": {s: [score(s, p, False, seed=7) for p in PLACE_PCTS] for s in STRATS}}
    i25 = PLACE_PCTS.index(25)
    for s in STRATS:
        r = res["placement"]["strategies"][s][i25]
        print(f"  25% {s:9s} Brier {r['model_brier'][0]:.3f}  acc {r['model_acc'][0]:.3f}")

    # ------------------------------------------ spillover: whole lots sensed, others blind
    print("whole-lot spillover ...", flush=True)
    sw = {"n_sensed_lots": [], "mae_prior": [], "mae_spill": [], "gain_pct": []}
    rng = np.random.default_rng(77)
    by_dist = {}
    for k in range(0, nL):
        e0, e1 = [], []
        for d in wk:
            for ti in times:
                for _ in range(3):
                    sensed = rng.choice(nL, k, replace=False) if k else []
                    masks = [np.full(N[i], i in sensed) for i in range(nL)]
                    occs = [d["occ"][i][ti] for i in range(nL)]
                    p0 = model.infer(S_at(ti), occs, masks, mu[:, ti], sd[:, ti], None)
                    p1 = model.infer(S_at(ti), occs, masks, mu[:, ti], sd[:, ti], across)
                    for i in range(nL):
                        if i in sensed: continue
                        f = occs[i].mean()
                        e0.append(abs(p0[i]["f_mean"] - f)); e1.append(abs(p1[i]["f_mean"] - f))
                        if k == 1:
                            dd = float(across["D"][i, sensed[0]])
                            by_dist.setdefault(int(dd // 100) * 100, []).append((e0[-1], e1[-1], p1[i]["prior_s"], p0[i]["prior_s"]))
        sw["n_sensed_lots"].append(k); sw["mae_prior"].append(round(float(np.mean(e0)), 4))
        sw["mae_spill"].append(round(float(np.mean(e1)), 4))
        sw["gain_pct"].append(round(100 * (1 - np.mean(e1) / np.mean(e0)), 1))
    sw["one_sensed_by_distance_m"] = {str(k): {"mae_prior": round(float(np.mean([v[0] for v in vs])), 4),
                                               "mae_spill": round(float(np.mean([v[1] for v in vs])), 4),
                                               "sd_after": round(float(np.mean([v[2] for v in vs])), 4),
                                               "sd_before": round(float(np.mean([v[3] for v in vs])), 4), "n": len(vs)}
                                      for k, vs in sorted(by_dist.items())}
    res["spill_whole"] = sw
    print("  sensed lots -> fill MAE of blind lots, prior vs spillover:",
          list(zip(sw["n_sensed_lots"], sw["mae_prior"], sw["mae_spill"], sw["gain_pct"])))
    print("  by distance:", sw["one_sensed_by_distance_m"])

    # ---------------------------------------------------------------- decisions
    print("decisions ...", flush=True)
    surf = senses.Surface(jload("fly_surface.json"))
    walk = np.array([l["walk_min"] for l in L]); price = np.array([l["price_hr"] for l in L])
    k15 = 15 // truth["step_min"]
    dtimes = [ti for ti in range(T) if 7.5 * 60 <= tmin[ti] <= 17 * 60 and tmin[ti] % 15 == 0]
    dec = {"pcts": [0, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100], "persona": "commuter with a C permit, heading to Hunt Library",
           "full_penalty_min": FULL_PENALTY_MIN, "policies": {}}
    cand = [i for i in range(nL) if not L[i]["pay"]]     # a permit holder does not pay: permit lots only
    dec["candidate_lots"] = [L[i]["name"] for i in cand]
    pol = {k: {"success": [], "minutes": []} for k in ("fly", "greedy", "nearest", "oracle")}
    for pct in dec["pcts"]:
        rng = np.random.default_rng(5000 + pct)
        acc = {k: [] for k in pol}
        for d in wk:
            for ti in dtimes:
                masks = masks_for("scatter", pct, rng)
                occs = [d["occ"][i][ti] for i in range(nL)]
                post = model.infer(S_at(ti), occs, masks, mu[:, ti], sd[:, ti], across)
                Ss = S_at(ti)
                ts = [senses.tastes(N[i], post[i]["p_occ"], post[i]["post"], Ss[i], masks[i], occs[i], walk[i],
                                    price[i], 0.0, mu[i, min(ti + k15, T - 1)] - mu[i, ti]) for i in range(nL)]
                hz = [senses.to_hz(t) for t in ts]
                reads = [surf.read(*h) for h in hz]
                free = np.array([(~occs[i]).sum() for i in range(nL)])
                order = [i for i in np.argsort(walk) if i in cand]
                best_real = next((int(i) for i in order if free[i] > 0), int(order[0]))
                picks = {"fly": cand[senses.fly_pick([reads[i] for i in cand], [hz[i] for i in cand])[0]],
                         "greedy": cand[int(np.argmax([ts[i]["sugar"] - ts[i]["bitter"] - ts[i]["loom"] for i in cand]))],
                         "nearest": int(order[0]), "oracle": best_real}
                for k, i in picks.items():
                    ok = free[i] > 0
                    mins = walk[i] if ok else FULL_PENALTY_MIN + walk[best_real]
                    acc[k].append((float(ok), float(mins)))
        for k in pol:
            a = np.array(acc[k])
            pol[k]["success"].append(round(float(a[:, 0].mean()), 4)); pol[k]["minutes"].append(round(float(a[:, 1].mean()), 3))
    dec["policies"] = pol; dec["n_decisions_per_point"] = len(wk) * len(dtimes)
    res["decision"] = dec
    for k in pol:
        print(f"  {k:8s} success@0/25/100%: {pol[k]['success'][0]:.3f} {pol[k]['success'][5]:.3f} {pol[k]['success'][-1]:.3f}"
              f"   minutes: {pol[k]['minutes'][0]:.2f} {pol[k]['minutes'][5]:.2f} {pol[k]['minutes'][-1]:.2f}")
    res["senses"] = {k: getattr(senses, k) for k in ("SUGAR_MAX_HZ", "BITTER_MAX_HZ", "LOOM_MAX_HZ", "UNC_FULL", "PRICE_FULL",
                                                    "WALK_SCALE_MIN", "FREE_SCALE", "RISE_FULL", "MN9_MIN_HZ", "GF_DIVERT_HZ")}
    jdump(res, "results.json")

    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 3, figsize=(16, 4.3))
        g = lambda key, src: np.array([r[key][0] for r in res["density"][src]])
        ax[0].plot(PCTS, g("naive_brier", "within"), "o-", c="#8a9bb5", label="naive baseline")
        ax[0].plot(PCTS, g("model_brier", "within"), "o-", c="#e07b39", label="fill model (within lot)")
        ax[0].plot(PCTS, g("model_brier", "spill"), "o-", c="#0d1f3c", label="fill model + spillover")
        ax[0].axvspan(20, 30, color="#e07b39", alpha=.12)
        ax[0].set(xlabel="% of spots with sensors", ylabel="Brier score on unsensed spots (lower is better)",
                  title="Sensor density vs accuracy (simulated test weekdays)"); ax[0].legend(); ax[0].grid(alpha=.3)
        for s, c in zip(STRATS, ["#8a9bb5", "#0d1f3c", "#ef4444", "#e07b39"]):
            ax[1].plot(PLACE_PCTS, [r["model_brier"][0] for r in res["placement"]["strategies"][s]], "o-", c=c, label=s)
        ax[1].set(xlabel="% of spots with sensors", ylabel="Brier (lower is better)",
                  title=f"Sensor placement (clusters of {model.CLUSTER})"); ax[1].legend(); ax[1].grid(alpha=.3)
        for k, c in zip(pol, ["#e07b39", "#0d1f3c", "#8a9bb5", "#4ade80"]):
            ax[2].plot(dec["pcts"], pol[k]["minutes"], "o-", c=c, label=k)
        ax[2].set(xlabel="% of spots with sensors", ylabel="mean minutes (walk + penalty if lot was full)",
                  title="Decision quality: fly vs baselines"); ax[2].legend(); ax[2].grid(alpha=.3)
        fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "curves.png"), dpi=110)
    except Exception as e:
        print("plot skipped:", e)


if __name__ == "__main__":
    main()
