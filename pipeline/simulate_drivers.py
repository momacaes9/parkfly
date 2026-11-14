#!/usr/bin/env python3
"""
simulate_drivers.py - SIMULATED ground truth occupancy for the focus lots.

No sensor exists yet, so the "truth" we hide from the predictor comes from a
small agent-based simulation (every constant here is an ASSUMPTION, listed in
ASSUMPTIONS.md):
  * cars arrive by time of day (commuters with a permit, paying visitors)
  * each driver heads to a demand anchor (Hunt Library or the building a lot
    is named after); anchor demand has its own day-to-day multiplier, so
    nearby lots rise and fall together
  * lot choice: logit on walk minutes and how full the lot is; if full, next best
  * spot choice: soft-max over free spots by attractiveness rank, so lots fill
    mostly, not perfectly, in rank order
  * stays are log-normal; departures leave holes
Outputs web/data/truth.json (held-out test days + fitted priors) and
results/sim_occupancy.png.
"""
import base64, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import jload, jdump, RESULTS, to_m, walk_min
import model

START_MIN, END_MIN, STEP = 6 * 60, 20 * 60, 5
T = (END_MIN - START_MIN) // STEP + 1
TRAIN_WEEKDAY = list(range(100, 114)); TRAIN_SAT = list(range(200, 206))
TEST_WEEKDAY = [1, 2, 3, 4]; TEST_SAT = [50]
BETA_WALK, BETA_FULL = 0.9, 4.0
ANCHOR_W = {"Hunt Library": 0.40, "Partners I Lot": 0.15, "Textiles Lot": 0.12,
            "E.B. III / Entrepreneur Drive": 0.18, "Research Drive": 0.15}
ANCHOR_SD, DAY_SD = 0.25, 0.10
COMMUTER_FACTOR, VISITOR_FACTOR, SAT_MULT = 1.05, 3.0, 0.30


def simulate_day(lots, dest, seed, day="weekday"):
    rng = np.random.default_rng(seed)
    nL = len(lots)
    N = [l["spaces"] for l in lots]
    cxy = np.array([[l["x"], l["y"]] for l in lots])
    anchors = {"Hunt Library": np.array(to_m(dest["lat"], dest["lon"]))}
    for l in lots:
        if l["name"] in ANCHOR_W:
            anchors[l["name"]] = np.array([l["x"], l["y"]])
    names = list(ANCHOR_W)
    walk = {a: np.array([walk_min(np.linalg.norm(cxy[L] - anchors[a])) for L in range(nL)]) for a in names}
    pay = np.array([l["pay"] for l in lots])
    cap_c, cap_v = sum(n for n, p in zip(N, pay) if not p), sum(n for n, p in zip(N, pay) if p)
    daym = np.exp(rng.normal(0, DAY_SD)) * (SAT_MULT if day == "sat" else 1.0)
    am = {a: np.exp(rng.normal(0, ANCHOR_SD)) for a in names}
    drivers = []   # (arrive_min, stay_min, kind, anchor)
    for a in names:
        n = rng.poisson(cap_c * COMMUTER_FACTOR * ANCHOR_W[a] * daym * am[a])
        comp = rng.choice(4, n, p=[0.62, 0.18, 0.12, 0.08])
        t = np.array([8 * 60 + 25, 10 * 60 + 15, 12 * 60 + 50, 14 * 60 + 45])[comp] + \
            rng.normal(0, 1, n) * np.array([50, 60, 45, 60])[comp]
        med = np.where(t < 9.5 * 60, 7.2, np.where(t < 12 * 60, 4.5, 2.2)) * 60
        stay = med * np.exp(rng.normal(0, 1, n) * np.where(t < 9.5 * 60, 0.35, 0.5))
        drivers += [(t[i], stay[i], "c", a) for i in range(n)]
    nv = rng.poisson(cap_v * VISITOR_FACTOR * daym * am["Hunt Library"])
    tv = np.where(rng.random(nv) < 0.3, rng.normal(12.5 * 60, 50, nv), rng.uniform(8.5 * 60, 17 * 60, nv))
    drivers += [(tv[i], 96 * np.exp(rng.normal(0, 0.6)), "v", "Hunt Library") for i in range(nv)]
    drivers.sort(key=lambda d: d[0])

    occ = [np.zeros(n, bool) for n in N]
    leave = []            # (leave_min, lot, spot)
    snaps = [np.zeros((T, n), bool) for n in N]
    spill = 0
    di = 0
    for minute in range(START_MIN - 60, END_MIN + 1):
        if leave:
            keep = []
            for (tl, L, s) in leave:
                if tl <= minute: occ[L][s] = False
                else: keep.append((tl, L, s))
            leave = keep
        while di < len(drivers) and drivers[di][0] <= minute:
            ta, stay, kind, a = drivers[di]; di += 1
            if ta < START_MIN - 60: continue
            allowed = [L for L in range(nL) if pay[L] == (kind == "v")]
            fill = np.array([occ[L].mean() for L in allowed])
            u = -BETA_WALK * walk[a][allowed] - BETA_FULL * fill ** 3 + rng.gumbel(0, 1, len(allowed))
            for j, k in enumerate(np.argsort(-u)):
                L = allowed[k]
                free = np.flatnonzero(~occ[L])
                if len(free) == 0:
                    continue
                if j > 0: spill += 1
                temp = 1.5 + 0.03 * N[L]
                w = np.exp(-np.arange(len(free)) / temp)
                s = free[rng.choice(len(free), p=w / w.sum())]
                occ[L][s] = True
                leave.append((minute + stay, L, s))
                break
        if minute >= START_MIN and (minute - START_MIN) % STEP == 0:
            ti = (minute - START_MIN) // STEP
            for L in range(nL):
                snaps[L][ti] = occ[L]
    return snaps, {"drivers": len(drivers), "spilled": spill}


def pack(a):
    return base64.b64encode(np.packbits(a.astype(np.uint8).ravel()).tobytes()).decode()


PM_FROM_MIN = 12 * 60 + 30   # after this the lot drains and holes scatter: softer frontier


def fit_tau(S_days, n, sel):
    """Maximum-likelihood softness of the fill frontier, using the true fill.
    sel: bool over time steps (morning fill-up or afternoon drain)."""
    S_days = [x[sel] for x in S_days]
    best, best_ll = None, -np.inf
    for tau in np.concatenate([np.arange(0.5, 6, 0.25), np.arange(6, 40, 1.0)]):
        ll = 0.0
        r = np.arange(n)
        for snaps in S_days:
            f = snaps.mean(1)
            P = np.clip(model.sigmoid((f[:, None] * n - r[None, :] - 0.5) / tau), 1e-9, 1 - 1e-9)
            ll += (np.log(P) * snaps + np.log(1 - P) * (~snaps)).sum()
        if ll > best_ll:
            best, best_ll = float(tau), ll
    return best


def main():
    d = jload("lots.json")
    lots, dest = d["lots"], d["dest"]
    nL = len(lots)
    runs = {}
    for kind, seeds in (("weekday", TRAIN_WEEKDAY + TEST_WEEKDAY), ("sat", TRAIN_SAT + TEST_SAT)):
        for s in seeds:
            runs[(kind, s)] = simulate_day(lots, dest, s, kind)
    fitted = {"tau": [], "prior": {}, "train_seeds": {"weekday": TRAIN_WEEKDAY, "sat": TRAIN_SAT}}
    for L in range(nL):
        tmin = START_MIN + np.arange(T) * STEP
        tr = [runs[("weekday", s)][0][L] for s in TRAIN_WEEKDAY]
        fitted["tau"].append([fit_tau(tr, lots[L]["spaces"], tmin < PM_FROM_MIN),
                              fit_tau(tr, lots[L]["spaces"], tmin >= PM_FROM_MIN)])
    fitted["tau_pm_from_min"] = PM_FROM_MIN
    Z = {}
    for kind, seeds in (("weekday", TRAIN_WEEKDAY), ("sat", TRAIN_SAT)):
        F = np.array([[runs[(kind, s)][0][L].mean(1) for L in range(nL)] for s in seeds])  # day, lot, time
        mu, sd = F.mean(0), np.maximum(F.std(0, ddof=1), model.SD_FLOOR)
        fitted["prior"][kind] = {"mu": np.round(mu, 4).tolist(), "sd": np.round(sd, 4).tolist()}
        Z[kind] = (F - mu[None]) / sd[None]
    # across-lot kernel: correlation of standardized weekday residuals vs centroid distance
    z = Z["weekday"].transpose(1, 0, 2).reshape(nL, -1)
    C = np.corrcoef(z)
    xy = np.array([[l["x"], l["y"]] for l in lots])
    D = np.maximum(np.linalg.norm(xy[:, None] - xy[None], axis=2), 15.0)
    np.fill_diagonal(D, 0.0)
    iu = np.triu_indices(nL, 1)
    best = (1e9, None, None)
    for rho0 in np.arange(0.2, 1.001, 0.05):
        for ell in np.arange(50, 3001, 25):
            err = ((C[iu] - rho0 * np.exp(-D[iu] / ell)) ** 2).sum()
            if err < best[0]:
                best = (err, float(rho0), float(ell))
    fitted["across"] = {"rho0": round(best[1], 3), "ell_m": best[2], "D": np.round(D, 1).tolist(),
                        "empirical_corr": np.round(C, 3).tolist(),
                        "note": "fit on simulated training weekdays; correlation of fill residuals vs distance"}
    print("tau per lot:", fitted["tau"], "| across: rho0", best[1], "ell", best[2], "m")

    days = []
    for kind, seeds in (("weekday", TEST_WEEKDAY), ("sat", TEST_SAT)):
        for s in seeds:
            snaps, info = runs[(kind, s)]
            days.append({"id": f"{kind}-{s}", "day": kind, "seed": s, **info,
                         "occ": [pack(snaps[L]) for L in range(nL)],
                         "fill": [np.round(snaps[L].mean(1), 3).tolist() for L in range(nL)]})
            print(f"  test {kind} seed {s}: {info}  peak fill per lot:",
                  [round(float(snaps[L].mean(1).max()), 2) for L in range(nL)])
    jdump({"label": "SIMULATED ground truth (agent-based driver model, seeded). Not sensor data.",
           "step_min": STEP, "start_min": START_MIN, "n_steps": T, "lots": [l["name"] for l in lots],
           "spaces": [l["spaces"] for l in lots], "days": days, "fitted": fitted,
           "encoding": "occ[lot] = base64(packbits(matrix[time, spot rank])), big-endian bits"}, "truth.json")

    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(13, 4.2), sharey=True)
        hrs = (START_MIN + np.arange(T) * STEP) / 60
        for k, (kind, seed) in enumerate((("weekday", TEST_WEEKDAY[0]), ("sat", TEST_SAT[0]))):
            for L in range(nL):
                ax[k].plot(hrs, runs[(kind, seed)][0][L].mean(1), label=f"{lots[L]['name']} ({lots[L]['spaces']})")
            ax[k].set_title(f"Simulated {kind}, seed {seed}"); ax[k].set_xlabel("hour"); ax[k].grid(alpha=.3)
        ax[0].set_ylabel("fraction occupied"); ax[0].legend(fontsize=7)
        fig.suptitle("ParkFly driver simulation (SIMULATED, not sensor data)")
        fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "sim_occupancy.png"), dpi=110)
    except Exception as e:
        print("plot skipped:", e)


if __name__ == "__main__":
    main()
