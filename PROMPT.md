# Build prompt for Claude (Fable): ParkFly

> Paste everything below the line into Claude Code (model: Claude Fable 5.2) opened on a clone of `https://github.com/momacaes9/parkfly`. Also have `https://github.com/momacaes9/parkshark` cloned next to it (`../parkshark`) so it can reuse the Duke pipeline and the Birmingham loader.

---

You are the lead engineer of **Park Shark** at the **NC State fruit-fly-brain Hack Day (Saturday, Nov 14, 2026)**. We are here to **win**. Today you build **ParkFly**: a live, honest, beautiful demo that answers Park Shark's real research question and runs every parking decision through a **real 139,000-neuron fruit-fly connectome**.

**Read `CONTEXT.md` in this repo first, end to end.** It holds the event rules, the judging rubric, the Park Shark brief, the fly-brain science and starter code, the verified NC State data endpoint, the current repo state and its known bugs. This prompt is the build order. When the two disagree, this prompt wins.

## 0. How you work today
- **Always demoable.** After every phase, the app must open and run. Commit at each checkpoint with a clear message. Never leave `main` broken.
- **Act, don't ask**, unless you are blocked on a credential or an irreversible choice. Pick sensible defaults and write them down in `ASSUMPTIONS.md`.
- **Verify by running.** Run every script, open the page in a browser, click every control, read the console. A feature is done when you have seen it work, not when you have written it.
- **Honesty is a feature.** Every number on screen is computed by code here or exported from the Colab run. Label *simulated*, *estimated*, *official NCSU*, *Birmingham (real)*. No hand-typed metrics. Fixed seeds.
- **Secrets:** never commit the FlyWire token or any key. The brain wiring (Shiu `Connectivity_783.parquet`) needs no token.
- Keep the existing Park Shark look: navy `#0D3F5A`, rust `#D8814B`, cream `#F5F0E8`, **Changa One** + **Barlow**. No AI-generated images anywhere.

## 1. The pitch you are building toward (memorize it)
> *A fly never sees the whole world. It reads a few senses and acts, and it rarely lands in the wrong place. Park Shark will never put a sensor on every spot. ParkFly reads 25% of a parking lot, infers the other 75%, and lets a real fruit-fly brain decide where to park.*

Two halves that click together:
1. **Sparse senses → full state** (Park Shark's research result): within-lot fill model + across-lot spillover, measured against baselines → a **sensor-density-vs-accuracy curve** and a **sensor-placement result**.
2. **Full state → decision** (the fly): each lot's posterior becomes tastes. **Sugar** = expected free usable spots, discounted by walk. **Bitter** = uncertainty + permit risk + price (*uncertainty tastes bitter*). **Looming** = the lot is filling fast or likely full on arrival. The connectome answers: **MN9** = commit, **MDN** = back off, **Giant Fibre (DNp01)** = divert now.

The demo moment: few sensors → the fly hesitates; slide sensors up → it commits; lesion the Giant Fibre → it drives into a filling lot.

## 2. Repo layout to end with
```
parkfly/
  README.md  CONTEXT.md  PROMPT.md  ASSUMPTIONS.md  DEMO.md
  build_ncstate.py              # kept as an entry point; calls pipeline/
  pipeline/
    ncsu_lots.py                # fetch + cache official NCSU polygons, group deck sections
    stalls.py                   # per-spot coordinates inside each focus lot (port of parkshark estimate_spaces.py)
    simulate_drivers.py         # ground-truth occupancy (agent-based)
    within_lot.py               # fill-level posterior per lot -> per-spot P(free) + band
    across_lot.py               # Gaussian spillover between lots
    birmingham_validate.py      # real-data test of across-lot prediction
    sensor_placement.py         # spread vs entrance-clustered vs frontier
    senses.py                   # posterior -> sugar/bitter/looming Hz (2 SD clip)
    export_web.py               # writes web/data/*.json
  colab/
    fly_surface.ipynb           # NEW: sanity checks + response surface + raster -> JSON
    fly_decides_parking.ipynb   # fixed version of the existing notebook
  web/
    index.html  app.js  style.css  vendor/leaflet*
    data/  lots.json  truth.json  fly_surface.json  fly_raster.json  fly_sanity.json
           results.json  birmingham.json
  results/                      # CSV + PNG of every curve, for the README and Q&A
  tests/                        # pytest for the math, node --test for the JS model
```
Python 3.11+, numpy, pandas, scipy, shapely, pyproj (geometry). Web: plain HTML/JS, no build step, Leaflet already vendored, a tiny inline-SVG or canvas chart (no heavy chart library needed). Everything the demo needs is local JSON so it **works offline**; map tiles are the only network dependency and the app must still look fine when tiles fail (cream background + lot polygons + spots).

## 3. Phases, in priority order

### P0. Map from real data (target: first 45 min)
1. `pipeline/ncsu_lots.py`: fetch the official NCSU endpoint in `CONTEXT.md` §5.1 (cache to `data/ncsu_parking_raw.geojson`, use the cache if offline). Keep `SPACES > 0`, `STATUS` active. **Group deck sections into physical facilities** (name prefix before " - " plus geometry overlap) while keeping per-section counts (visitor/pay/permit).
2. Geocode **Hunt Library** and **Riddick Hall** from OSM (Overpass `name~`), store both; default destination = **Hunt Library** (the brief), switchable to the Hack Day venue.
3. Choose **3 to 4 focus lots** around Hunt Library for per-spot modeling. Prefer surface lots so spots render as dots: candidates are *Partners I Lot (76)*, *Partners II Lot (63)*, *Oval Drive (49)*, *Oval Drive (43)*; plus *Partners Way Deck* as a deck (render levels as a compact grid schematic). Verify names and distances from the data; pick the best 3 to 4 within ~10 min walk. All other NCSU lots render as polygons with official capacity only.
4. `pipeline/stalls.py`: port `../parkshark/scripts/estimate_spaces.py` (UTM 17N, 1.2 m setback, 2.6 × 5.4 m bays, 6.2 m aisle, 2 orientations × 8 offsets). **Then reconcile with the official `SPACES`**: if the grid gives more bays than `SPACES`, keep the `SPACES` bays nearest the entrance side; if fewer, label the shortfall. Each spot gets `id, lat, lon, lot_id, level (decks), dist_to_entrance_m, walk_to_dest_min`. Entrance = OSM `amenity=parking_entrance` or the polygon point nearest a service road; record which.
5. Replace SEED data everywhere. Keep the "SEED" fallback only if the endpoint and cache both fail, and badge it loudly.
**Checkpoint:** web map shows real NCSU polygons, focus lots with per-spot dots, destination pin. Commit.

### P1. Ground truth simulator (target: +45 min)
`pipeline/simulate_drivers.py`, seeded, 1-minute steps, snapshots every 5 minutes, 06:00 to 20:00, for **3 weekday seeds + 1 Saturday**:
- Arrivals: non-homogeneous Poisson per lot-catchment with a weekday shape (morning ramp 07:00 to 09:30, midday churn, afternoon departures). Scale volumes so the closest focus lot peaks ~90 to 97% full around 10:00 to 13:00 and farther ones lower. Saturday ≈ 25 to 40% of weekday.
- Driver types: permit commuter (long stay, lognormal median ~6.5 h) and visitor (median ~1.5 h). Permit eligibility from NCSU per-permit counts (simplified; write the simplification in `ASSUMPTIONS.md`).
- **Lot choice:** multinomial logit over allowed lots on −β_walk·walk_min − β_cost·price − β_full·(expected search) + Gumbel noise. If the chosen lot is full, try the next best (log the spill; it is real demand spillover).
- **Spot choice inside a lot:** softmax over **free** spots by attractiveness (distance to entrance + walk to destination), temperature tuned so fill order is mostly, not perfectly, by rank. This is the physical reason the within-lot model works; state it in the README.
- Output `web/data/truth.json`: per focus lot, a bit-packed or run-length occupancy matrix [time × spot] per seed (keep the file < 3 MB), plus lot-level occupancy curves.
- Plot `results/sim_occupancy.png` and sanity-check believability against the Tier 3 campus template shape and a Birmingham weekday curve. Note what you compared.
**Checkpoint:** a time scrubber in the UI replays the simulated day, spots turn red/green. Commit.

### P2. Within-lot predictor + slider + accuracy curve (target: +60 min). **This is objective 6. Protect it.**
Implement the model **twice, identically**: `pipeline/within_lot.py` (for offline curves) and in `web/app.js` (live). Add a test that both give the same numbers on a fixed case.
- Spots ranked by attractiveness: r = 0 … N−1.
- Likelihood: P(occupied_i | f) = σ((f·N − r_i) / τ). τ is fit once by maximum likelihood on simulated training seeds and held fixed (report it).
- **Posterior over f** on a 101-point grid: prior from the time-of-day mean for that lot (training seeds) with a reasonable spread, times the likelihood of the sensed spots. Posterior predictive per unsensed spot: P(occ_i) = Σ_f post(f)·σ(...). **Band** per spot and per lot: 10th to 90th percentile of f mapped through the model; also an 80% credible interval on the lot's free count.
- **Baseline (the brief's naive one):** every unsensed spot gets P(occ) = fraction occupied among that lot's sensed spots.
- **Metrics on unsensed spots only:** accuracy at 0.5 threshold, **Brier score**, and log loss. Report all three: the uniform baseline can look fine on raw accuracy when a lot is nearly full or empty; Brier exposes it. Accuracy curve = metric vs. % sensed (0, 5, 10 … 100), averaged over many random sensor masks × time snapshots × seeds, with a ±1 SD band. Test seeds ≠ the seeds used to fit τ and the prior.
- **UI:** a big **"% of spots with sensors"** slider (default 25%, a shaded 20 to 30% "Park Shark zone"). Moving it redraws sensed spots (solid ring, exact color) vs inferred spots (fill color = P(free), opacity = confidence), updates each lot's "free spots: 23 (19 to 27)" label, and moves a marker along the live accuracy curve (model line vs baseline line). Update < 100 ms. A "reshuffle sensors" button. A time scrubber.
- Precompute the full curves in Python to `results.json` and draw them; the live marker uses the in-browser computation for the current mask. They must agree (test it).
**Checkpoint:** the 60-second walkthrough works: slide 0 → 25 → 100%, map sharpens, curve climbs, model beats baseline. Commit and deploy (see §6).

### P3. The fly brain (Colab; start it EARLY, in parallel with P1/P2, because the runs take time)
Create `colab/fly_surface.ipynb`. It reuses the organizers' starter cells verbatim (install, load Shiu 783 wiring and labels, `find`, `simulate`, `rate`), then:
1. **Sanity table** (handbook): no input; sugar 200; sugar 200 + bitter 200; looming 150; looming 150 with the Giant Fibre **input-lesioned**; and "input stops → activity dies" (run with input for 100 ms then none for 100 ms; add an `input_until_ms` argument to a copy of `simulate`). Export `fly_sanity.json` (rates + pass/fail + expected). If a check fails, stop and fix wiring before anything else.
2. **Response surface:** sugar ∈ {0, 50, 100, 150, 200} × bitter ∈ {0, 50, 100, 200} × looming ∈ {0, 50, 100, 150} Hz, **2 seeds each** (3 if time allows), 200 ms, from rest. Record mean MN9, Giant Fibre, MDN (and DNp09 if found) rates and their SD. Do the same grid for the **Giant-Fibre-lesioned brain**, where lesion means zeroing the GF's **input columns** (`W @ sp.diags(keep)`), so it cannot fire. Note: the existing notebook's output lesion (`sp.diags(keep) @ W`) leaves the GF firing and does not change our verdict, which is a bug. Run a coarse 3×3×3 grid first so we have *something*, then the full grid. Save partial results as you go (Colab can disconnect). Optional speedup: a torch/cupy port of `simulate` on the T4 GPU, validated against the numpy version on the sanity table.
3. **Spike raster:** track ~300 neurons (all MN9/GF/MDN, a sample of sugar/bitter/looming inputs, ~200 random others) for 3 scenarios: *sweet close lot*, *uncertain lot*, *lot filling fast*. Export spike times to `fly_raster.json` (< 1 MB).
4. **Provenance block** in every JSON: `n_neurons`, `n_connections`, wiring file name and version (783), seeds, grid, ms, run date, notebook name.
5. Optional: export the DNp01 skeleton (needs the FlyWire token, entered with getpass, never saved) as a light JSON polyline for a small 3D/2D render in the UI. Stretch only.
6. Fix `colab/fly_decides_parking.ipynb` (lesion bug, multi-seed average, thresholds from the surface) so it still works standalone on `senses.json`.

`pipeline/senses.py` + `web/app.js` (same logic): from each lot's posterior at the arrival time, compute
- sugar_raw = E[free usable spots] × exp(−walk_min / 8)
- bitter_raw = a·posterior SD of free count (normalized) + b·permit_risk + c·price
- loom_raw = predicted fill over the next 15 min + P(full on arrival)
Winsorize at 2 SD across candidate lots (handbook), map into the **responsive range of the measured surface** (read it from `fly_surface.json`; don't assume 0 to 200 is all useful). Interpolate the surface trilinearly → MN9, GF, MDN. **Verdict rules derived from the surface and the sanity table**, written in `ASSUMPTIONS.md`: GF above its looming-test level → **DIVERT 🏃**; MDN > MN9 → **BACK OFF ↩**; else **COMMIT 🍽** with strength = MN9 Hz. The fly's pick = the COMMIT lot with the highest MN9.

**Fly panel in the UI:** three live neuron gauges (MN9 / MDN / GF, in Hz, labeled with real cell names), the three taste bars per lot, the verdict per lot on the map, the raster animation (canvas, plays the precomputed spikes of the closest canonical scenario; label it as such), a **Lesion Giant Fibre** toggle that switches to the lesioned surface, and a provenance footer ("decisions interpolated from N real spiking simulations of the FlyWire/Shiu 783 connectome, 138k+ neurons; computed <date>"). Use the real numbers from the JSON.

**Decision quality curve (the bridge between the two halves):** in the simulator, at many arrival times, let the fly pick a lot from posteriors at sensor density s; score = 1 if the picked lot truly had a usable free spot on arrival, plus the walk minutes. Compare **fly** vs **dumb baseline** (nearest lot with the highest posterior free fraction, no neurons) vs **oracle** (true state). Plot success rate vs % sensed. Report honestly even if the fly loses; the handbook's trading bot "lost money, but less than holding" is the tone.
**Checkpoint:** fly verdicts live on the map, gauges move with the slider, lesion toggle changes behavior on the "filling fast" lot. Commit and deploy.

### P4. Across-lot spillover + Birmingham validation
1. `pipeline/across_lot.py`: lot fill residuals z_L = f_L − μ_L(t) ~ Gaussian with covariance K. **NC State:** K_LM = σ²·exp(−d_LM / ℓ) on walking distance (σ, ℓ fit on simulated seeds, stated). An exactly sensed lot (toggle) conditions the Gaussian; unsensed lots get an updated mean and a variance that **grows with distance** from sensed lots; this updated distribution becomes the within-lot prior. UI: a **"sense this whole lot"** toggle on each lot (or a dropdown), and halos/band widths on neighbors that visibly tighten nearest the sensed lot.
2. `pipeline/birmingham_validate.py` (real data): load Birmingham via `../parkshark/tier3_model/fetch_data.py raw` and its cleaning rules (counts → rates, UK local time, round to 30 min, drop broken rows). Birmingham has **no coordinates**, so estimate K **empirically** from residual correlations on the first ~70% of days; test on the last ~30%. For many random draws, sense 20 to 30% of lots, predict the rest by Gaussian conditioning; compare to **none sensed** (hour × weekday mean from training days). Report MAE (rate and cars), the gain with a ±SD over draws, and the curve over 0 to 100% of lots sensed. Export `birmingham.json` and `results/birmingham_gain.png`. Show the number in the UI ("validated on 30 real car parks in Birmingham, UK: hiding 75% of lots, sensing 25% cuts error by X%").
**Checkpoint:** commit, deploy.

### P5. Sensor placement (the slide that matters for Park Shark)
`pipeline/sensor_placement.py`. Use **Park Shark's real hardware constraint: one sensor sees a contiguous cluster of 10 to 15 spots (~$65)**. Same budget (e.g., 25% of spots) under:
- **entrance-clustered:** clusters on the most attractive spots near the entrance,
- **spread:** clusters evenly spaced across the attractiveness range,
- **frontier (our bonus):** clusters centered where the lot's fill frontier usually sits at peak hours,
- **random scattered spots** as a non-physical reference.
Measure the within-lot metrics over the simulated days. Expected intuition, verify rather than assume: entrance spots are almost always full, so they saturate and say little about the fill level; spread or frontier clusters see the edge. Plot `results/placement.png`; in the UI, a **placement selector** (Spread / Entrance / Frontier) next to the slider that redraws sensors and updates the curve. Express the result in Park Shark terms: *"With 2 sensors in Partners I, spread placement predicts the other ~50 spots with Brier X vs Y for entrance placement."* (Fill the numbers from the run.)

### P6. Polish (only once P0 to P4 work)
- First screen readable on a 1366×768 projector: big fonts, high contrast, light theme default.
- A **"Demo mode"** button that walks the 6 beats of `DEMO.md` with one key press each (→ arrow), never requiring typing. Escape exits.
- `README.md`: one-screen summary (hook, live link, a real screenshot, how it works, results table with the real numbers, run instructions, honesty, team, credits: FlyWire, Shiu et al. 2024, NCSU Transportation GIS, OSM ODbL, Birmingham UCI).
- `DEMO.md`: the script below, with the real numbers filled in.

## 4. Data contracts (keep the web app dumb and fast)
- `lots.json`: `{generated_at, dest:{hunt,riddick}, source, lots:[{id,name,sections:[{name,spaces,permit,pay}],spaces,type,levels,polygon,walk_min,price_hr,permit_risk,focus:bool, spots?:[{id,lat,lon,rank,level}]}]}`
- `truth.json`: `{step_min:5, start:"06:00", seeds:[{id,day:"weekday|sat", lots:{lot_id:{occ:"<rle or base64 bits>"}}}], fitted:{tau, prior:{lot_id:[mean per step]}, across:{sigma,ell}}}`
- `fly_surface.json`: `{provenance:{...}, grid:{sugar:[],bitter:[],loom:[]}, intact:{mn9:[[[...]]],gf:...,mdn:...,sd:{...}}, lesion_gf:{...}}`
- `results.json`: within-lot curves (model/baseline × accuracy/Brier/logloss × % sensed, mean and SD), placement results, decision-quality curve, τ, test seeds.
Keep total `web/data` under ~8 MB.

## 5. Demo script (target 4:00, hard max 5:00). Live, no slides first.
1. **0:00 Hook (20 s).** "A fly never sees the whole world: it reads a few senses and acts. Park Shark sensors cost $65 and cover 10 to 15 spots, so no one will sense every spot. Question: if we sense only 25%, can we read the whole lot? And can a real fly brain decide where to park?"
2. **0:20 Sparse → full (45 s).** Slider 0% → 25% → 100%. "Solid rings are sensors, everything else is inferred, with confidence." Curve climbs; "our model beats the naive baseline by X Brier at 25%."
3. **1:05 Spillover (30 s).** Sense the whole Partners I lot; neighbors tighten, uncertainty grows with distance. "On real Birmingham data, sensing 25% of lots cuts error by X%."
4. **1:35 Placement (30 s).** Spread vs Entrance. "Same two sensors; spread wins by X. This is how Park Shark will install."
5. **2:05 The fly decides (60 s).** Taste bars, neuron gauges, raster. Slide sensors down: uncertainty tastes bitter, MN9 drops, the fly backs off. Slide up: it commits to <lot>. "These are interpolated from N real spiking simulations of the 139k-neuron FlyWire connectome." Toggle **Lesion Giant Fibre** on the lot filling fast: the fly no longer diverts and drives into a full lot.
6. **3:05 Honest close (40 s).** Limitations: ground truth is simulated; within-lot validated in simulation, across-lot on real Birmingham data; the fly is a fixed filter, so we show the baseline (and whether it wins). Next: Park Shark's UNC and Durham pilots replace the simulator with real per-spot data; the curve tells each deployment how many sensors to buy.
Q&A prep in `DEMO.md`: why a fly (the handbook rule fits: good/bad/looming → eat/back off/flee); what if the fly loses to the baseline; how τ and the prior were fit and on which seeds; why Brier and not only accuracy; Birmingham has no coordinates, so we used empirical covariance; what changes for decks; cost per spot of the result.

## 6. Deploy
Static site from `web/`. Use Vercel (`npx vercel --prod` with root `web/`, project name `parkfly`) or GitHub Pages from `web/`; pick whichever works first and put the live link at the top of the README. Also keep it runnable with `python3 -m http.server -d web 8000`. The laptop must be able to run the demo offline from the local server.

## 7. Definition of done (check every box, by running it)
- [ ] Real NCSU lots on the map; 3 to 4 focus lots with per-spot dots; no SEED data.
- [ ] Simulator: believable weekday curves for the focus lots, saved plot, seeds listed.
- [ ] Within-lot model beats the naive baseline on Brier (and report accuracy and log loss) across 10 to 40% sensed, on held-out seeds.
- [ ] Birmingham: measured gain at 20 to 30% of lots sensed vs none, with SD.
- [ ] Placement: spread (and frontier) vs entrance-clustered, measured.
- [ ] Fly: sanity table passes; response surface (intact + lesioned) exported with provenance; verdicts live in the UI; lesion toggle changes behavior; fly vs baseline decision curve reported honestly.
- [ ] Slider walkthrough < 60 s, updates < 100 ms, works offline, no console errors.
- [ ] Python and JS models agree (test); `pytest` and `node --test` pass.
- [ ] README with real numbers and screenshot; DEMO.md; ASSUMPTIONS.md; deployed link.
- [ ] No secrets in git (`git grep -i token` clean).

Start now: read `CONTEXT.md`, then kick off the Colab fly runs (P3 steps 1 and 2) so they compute while you build P0 to P2.
