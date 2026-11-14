"""P4 real-data check: Birmingham (UCI #482, 30 car parks, Oct-Dec 2016).
Sense a random 25% of car parks, predict the other 75% by Gaussian conditioning on the
residual covariance K learned from the first 70% of days; test on the last 30%.
Baseline ("none sensed") = hour x weekday mean from training days.
Birmingham has no coordinates -> K is EMPIRICAL (residual covariance), not distance-based.

  python3 pipeline/birmingham_validate.py            # downloads UCI zip (needs internet)
  python3 pipeline/birmingham_validate.py --zip path # use a local zip
  python3 pipeline/birmingham_validate.py --selftest # SYNTHETIC code-path test, never ships to the UI
Writes web/data/birmingham.json + results/birmingham_gain.png
"""
import argparse, io, os, sys, zipfile, urllib.request
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, RESULTS, jdump

URL = "https://archive.ics.uci.edu/static/public/482/parking+birmingham.zip"
CACHE = os.path.join(ROOT, "data", "parking_birmingham.zip")
PCTS = [0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100]
DRAWS, SEED, RIDGE, TRAIN_FRAC = 200, 7, 0.02, 0.70

def load_real(zpath):
    if not os.path.exists(zpath):
        os.makedirs(os.path.dirname(zpath), exist_ok=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "parkfly-hackathon/0.1"})
        open(zpath, "wb").write(urllib.request.urlopen(req, timeout=120).read())
    z = zipfile.ZipFile(zpath)
    name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    raw = pd.read_csv(io.BytesIO(z.read(name)))
    df = pd.DataFrame({"lot": raw["SystemCodeNumber"].astype(str),
                       "ts": pd.to_datetime(raw["LastUpdated"], errors="coerce"),
                       "cap": raw["Capacity"].astype(float), "occ": raw["Occupancy"].astype(float)})
    df = df.dropna()
    df = df[(df.cap > 0) & (df.occ >= 0) & (df.occ <= df.cap * 1.05)]       # drop broken rows
    df["rate"] = (df.occ / df.cap).clip(0, 1)                               # counts -> rates
    df["slot"] = df.ts.dt.round("30min")                                    # UK local time, 30 min grid
    return df.groupby(["slot", "lot"]).rate.mean().unstack("lot"), df.groupby("lot").cap.median()

def load_synth():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2016-10-04", "2016-12-19 23:30", freq="30min")
    base = rng.uniform(.3, .8, 30); ph = rng.uniform(-2, 2, 30); shared = rng.normal(0, .08, len(idx)).cumsum() * .05
    M = np.array([np.clip(b + .25 * np.sin((idx.hour + idx.minute / 60 - 7) / 24 * 2 * np.pi - p) + shared + rng.normal(0, .04, len(idx)), 0, 1)
                  for b, p in zip(base, ph)]).T
    return pd.DataFrame(M, index=idx, columns=[f"S{i}" for i in range(30)]), pd.Series(300.0, index=[f"S{i}" for i in range(30)])

def run(P, cap):
    # Split before learning means, selecting coverage, or filling missing values.
    # No interpolation: a held-out value must never enter the training matrix.
    days = np.array(sorted(set(P.index.date)))
    cut = days[int(len(days) * TRAIN_FRAC)]
    tr, te = P[P.index.date < cut].copy(), P[P.index.date >= cut].copy()
    cols = tr.columns[tr.notna().mean() >= .6]
    tr, te = tr[cols], te[cols]
    if len(cols) < 2:
        raise ValueError("At least two sufficiently covered training lots are required")
    key = lambda d: (d.index.day_of_week, d.index.hour * 2 + d.index.minute // 30)
    kt, ke = key(tr), key(te)
    mu = tr.groupby([kt[0], kt[1]]).mean()
    hour_mu = tr.groupby(kt[1]).mean()
    def lookup(d, k):
        vals = mu.reindex(list(zip(k[0], k[1]))).to_numpy()
        fallback = hour_mu.reindex(k[1]).to_numpy()
        return np.where(np.isfinite(vals), vals,
                        np.where(np.isfinite(fallback), fallback, tr.mean().to_numpy()))
    Rtr = tr - lookup(tr, kt)
    MUte, Yte = lookup(te, ke), te.to_numpy()
    Rte = Yte - MUte
    # Pairwise empirical covariance; PSD projection handles incomplete timestamps.
    K = Rtr.cov(min_periods=20).fillna(0).to_numpy()
    eig, Q = np.linalg.eigh((K + K.T) / 2)
    K = (Q * np.maximum(eig, 1e-8)) @ Q.T
    n = len(cols); rng = np.random.default_rng(SEED)
    mae_none = float(np.nanmean(np.abs(Rte)))
    out, sd, baseline, base_sd, cars_out, cars_base, gains = [], [], [], [], [], [], []
    capacities = cap.reindex(cols).to_numpy()
    for p in PCTS:
        k = max(0, round(n * p / 100))
        maes, bases, cm, cb, gs = [], [], [], [], []
        if k == n:
            # There are no hidden targets at 100%; error is undefined, not zero.
            for series in (out, sd, baseline, base_sd, cars_out, cars_base, gains):
                series.append(None)
            continue
        for _ in range(DRAWS if k else 1):
            S = rng.choice(n, k, replace=False) if k else np.array([], int)
            H = np.setdiff1d(np.arange(n), S)
            valid = np.isfinite(Rte[:, S]).all(axis=1) if k else np.ones(len(te), bool)
            if not valid.any():
                continue
            target = Yte[valid][:, H]
            base = MUte[valid][:, H]
            if k:
                A = K[np.ix_(S, S)] + RIDGE * np.diag(np.maximum(np.diag(K)[S], 1e-8))
                weights = np.linalg.solve(A, K[np.ix_(S, H)])
                pred = base + Rte[valid][:, S] @ weights
            else:
                pred = base
            error = np.abs(target - np.clip(pred, 0, 1))
            base_error = np.abs(target - base)
            if not np.isfinite(error).any():
                continue
            m, bm = float(np.nanmean(error)), float(np.nanmean(base_error))
            maes.append(m); bases.append(bm)
            cm.append(float(np.nanmean(error * capacities[H])))
            cb.append(float(np.nanmean(base_error * capacities[H])))
            gs.append(100 * (1 - m / bm) if bm else 0)
        if not maes:
            raise ValueError(f"No evaluable held-out observations at {p}% sensed")
        out.append(float(np.mean(maes))); sd.append(float(np.std(maes)))
        baseline.append(float(np.mean(bases))); base_sd.append(float(np.std(bases)))
        cars_out.append(float(np.mean(cm))); cars_base.append(float(np.mean(cb)))
        gains.append(float(np.std(gs)))
    i25 = PCTS.index(25)
    return dict(n_lots=int(n), n_train_days=int((days < cut).sum()), n_test_days=int((days >= cut).sum()),
                pcts=PCTS, mae_none=mae_none, mae_none_matched=baseline, mae_none_matched_sd=base_sd,
                mae_spill=out, mae_spill_sd=sd, draws=DRAWS,
                gain_at_25=dict(mae_none=baseline[i25], mae_spill=out[i25], mae_spill_sd=sd[i25],
                                gain_pct=100 * (1 - out[i25] / baseline[i25]), gain_pct_sd=gains[i25],
                                mae_cars_none=cars_base[i25], mae_cars_spill=cars_out[i25]),
                provenance=dict(source=URL, seed=SEED, train_fraction=TRAIN_FRAC, split_date=str(cut),
                                baseline="training hour x day-of-week mean; hour mean fallback",
                                covariance="training residuals only, pairwise empirical, PSD projection",
                                cleaning="UK local timestamps rounded to 30 min; no interpolation",
                                evaluation="both methods scored on the same hidden lots and observed timestamps",
                                endpoint_100="null: no hidden lots remain")), P

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--zip", default=CACHE); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    P, cap = load_synth() if a.selftest else load_real(a.zip)
    R, P = run(P, cap)
    R["note"] = (f"REAL Birmingham UK data (UCI #482), {R['n_lots']} car parks. Trained on first {R['n_train_days']} days, tested on last {R['n_test_days']}. "
                 f"Covariance learned from data (no coordinates). Mean of {DRAWS} random draws, ±SD.")
    if a.selftest:
        R["note"] = "SYNTHETIC SELF-TEST - NOT REAL DATA"; print("SELFTEST (synthetic) - not writing to web/data"); 
    else:
        jdump(R, "birmingham.json")
    g = R["gain_at_25"]
    print(f"{R['n_lots']} lots | train {R['n_train_days']}d test {R['n_test_days']}d | none MAE {g['mae_none']:.4f} -> spill@25% {g['mae_spill']:.4f} (±{g['mae_spill_sd']:.4f}) = {g['gain_pct']:.1f}% better ({g['mae_cars_none']:.1f} -> {g['mae_cars_spill']:.1f} cars)")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    f, ax = plt.subplots(figsize=(6, 3.4)); m = np.array(R["mae_spill"], dtype=float); s = np.array(R["mae_spill_sd"], dtype=float)
    ax.plot(PCTS, R["mae_none_matched"], color="gray", ls="--", label="hour × weekday (same hidden lots)")
    ax.plot(PCTS, m, color="#2a9d5c", lw=2.5, label="spillover"); ax.fill_between(PCTS, m - s, m + s, color="#2a9d5c", alpha=.2)
    ax.set_xlabel("% of car parks sensed"); ax.set_ylabel("MAE (occupancy rate)"); ax.legend(); ax.set_title("Birmingham" + (" [SYNTHETIC]" if a.selftest else " (real)"))
    f.tight_layout(); f.savefig(os.path.join(RESULTS, "birmingham_gain_SYNTH.png" if a.selftest else "birmingham_gain.png"), dpi=130)
