# ParkFly: full context document

**Park Shark × Fruit Fly Brain · NC State Hack Day · Saturday, November 14, 2026**

This document gathers everything a builder (human or AI) needs in one place: the event, the judging rules, the Park Shark company and its earlier Duke work, the fly-brain science and code, the NC State data, the current state of this repo, its known bugs, and the plan. Read it end to end before writing code. `PROMPT.md` is the build order. This file is the reference.

---

## 1. The event

- **What:** a fruit-fly-brain hackathon at NC State ("Hack Day"), Saturday, Nov 14, 2026. Organizers provide a starter Colab notebook (`fly_brain_starter.ipynb`) and a handbook ("Fruit Fly Hackday Handbook").
- **Theme:** *"It's time to see how much you can create with a fruit fly's brain!"* Data-driven insights, creative applications (agent, simulation, game, full project), rapid prototyping from connectome to working prototype.
- **Demo:** live demonstration, **hard limit of 3 to 5 minutes**. Organizers discourage showing slides before the demo (it uses up demo time) and discourage **AI-generated slides or images**.

### Judging rubric (verbatim intent)
| # | Criterion | Scale | Weight | What it means for us |
|---|---|---|---|---|
| 0 | **Did they use the required data?** You must incorporate fruit fly brain data in a meaningful way. | Yes/No | **Gate**: no means not judged | The fly's decisions must come from real simulation runs on the real connectome, and the UI must show that provenance. |
| 1 | **Creativity / uniqueness.** Does it address the challenge in an engaging or creative way? | 1 to 5 | **Most weight** | The framing has to land in the first 20 seconds: "inferring the whole world from a few sparse senses" is a fly problem *and* a Park Shark problem. |
| 2 | **Functionality.** Does it work well enough to get the point across during the demo? | 1 to 5 | normal | Slider-driven live demo that never breaks, works offline, and updates in under 100 ms. |
| 3 | **Presentation.** Was the demo professional? Goal, purpose, limitations, next steps, concise. | 1 to 5 | normal | A rehearsed 4-minute script that names limitations and next steps. |

---

## 2. Park Shark (the company and the team)

- **Park Shark** is a pre-seed parking startup (raising $50K, ConvergeSouth 2026). Pitch: *"Your last mile parking quest, solved."* Live per-spot availability inside Google/Apple Maps, automatic payment on exit, no new app, no kiosk.
- **Hardware:** a radar/RF sensor, **about $65 per unit, covering 10 to 15 spots at once** (vs. $150+ per spot for ground sensors). Camera-free vehicle ID via TPMS signature. A camera exists only at the entrance gate for one brief identity correlation. Pilots: UNC Planning & Transportation (confirmed), City of Durham Municipal Lot #20 (planned); Chapel Hill and Carrboro interested.
- **Positioning:** the live per-spot data layer *underneath* lot operators, reservation apps (SpotHero, Arrive), operators (AirGarage, Metropolis) and enforcement.
- **Brand:** navy `#0D3F5A`, rust/orange `#D8814B` (accent variants `#E07B39`, `#F08C48`), cream `#F5F0E8`; status colors green `#4ADE80`, yellow `#FACC15`, red `#EF4444`; fonts **Changa One** (display) + **Barlow** (body). Landing page: https://parkshark.netlify.app/
- **Team:** Ishan (founder, product), Anne (Duke parking atlas, official data), Jacob (Tier 3 occupancy model), Monica (map, app and deployment). GitHub: `momacaes9`.

### Earlier work: ParkShark Duke (Triangle AI Hackathon 2026)
Repo https://github.com/momacaes9/parkshark · live https://parkshark-blond.vercel.app

- Google Maps view of **309 lots/decks** within 1.5 km of Duke's Wilkinson Building, pins labeled with free spaces, SVG stall schematics (16,012 stalls across 275 layouts), Gemini concierge, Google Pay TEST demo, Supabase sensor tables, Leaflet/OSM fallback.
- **Honesty culture** (keep it): every number is badged *measured*, *counted* or *estimated*; anything unsourced reads "Not published"; point-in-polygon joins only, never proximity guesses.
- **Pipeline we reuse:** `scripts/fetch_osm.py` (Overpass fetch) → `scripts/estimate_spaces.py` (stall estimation: project to UTM 17N, 1.2 m perimeter setback, subtract buildings, fit **2.6 × 5.4 m** bays with a **6.2 m** aisle, test 2 orientations × 8 grid offsets, keep the densest valid layout) → `scripts/build_main.py` (merge, capacity priority: published → OSM `capacity` tag → mapped stalls → roof × levels → estimated grid).
- **Tier 3 occupancy model** (`tier3_model/park_shark.py`): scikit-learn `HistGradientBoostingRegressor` with quantile loss (10/50/90), features hour, sin/cos hour, weekday, weekend, weather, holidays. Trained on public car parks in **Birmingham UK** (UCI dataset) and **The Hague**, weighted by similarity to a campus template. On campus-like lots it beats the hour×weekday baseline by **44% (MAE 0.129 vs 0.231)**; it loses on non-campus lots, and that trade is deliberate and documented.
- **Birmingham data:** `python3 tier3_model/fetch_data.py raw` downloads `https://archive.ics.uci.edu/static/public/482/parking+birmingham.zip` (verified reachable today). It covers ~30 car parks, Oct 4 to Dec 19 2016, readings about every 30 min from ~8:00 to 16:30, with columns `SystemCodeNumber, Capacity, Occupancy, LastUpdated`. **It has no coordinates**, so cross-lot structure must come from the empirical correlation of the lots' time series, not from distance. Cleaning rules from Tier 3: Occupancy is a car count, convert it to a rate; timestamps are UK local; round to the nearest half hour; drop broken rows. Citation: Stolfi, D. (2017), Parking Birmingham, UCI ML Repository, doi:10.24432/C51K5Z.

---

## 3. The project brief (from the Park Shark Hack Day PDF)

> **Direction.** Parking sensors are expensive, so no one instruments every spot. The question that matters for Park Shark is: **if we have exact occupancy for only 20 to 30% of spots, how well can we predict the rest?** We'll build the system that answers it, demoed on an NC State campus map, framed for the event's theme as a fly-brain problem: **inferring the full state of the world from a few sparse senses.**

**What to build:** an interactive dashboard of real NC State lots around one destination (e.g., **Hunt Library**). Each lot shows **per-spot predicted occupancy with a confidence band**. A **slider sets the percentage of spots that have "sensors"**; as it rises, predictions sharpen and an **accuracy curve climbs**. A **second toggle picks which whole lot is sensed**, showing predictions spill over to neighboring unsensed lots.

**How:**
1. **Map:** the Duke pipeline (OSM fetch → stall estimation → map build) re-aimed at an NC State bounding box.
2. **Ground truth:** a small driver simulation. Cars arrive by time of day, pick spots by walk distance and cost, and leave after random stays. This produces the "true" occupancy we hide from the predictor.
3. **Within-lot prediction:** spots fill roughly in order of attractiveness, so a scattered 20 to 30% of observed spots lets us fit **one fill-level parameter per lot** and give every unsensed spot a probability of being free.
4. **Across-lot prediction:** nearby lots share demand, so an exactly sensed lot updates its neighbors' estimates, **with uncertainty growing with distance**. Validated on real data (**Birmingham**) by hiding most lots and measuring the improvement.

**Pointed objectives (the checklist judges and the founder will look for):**
1. NC State map from real data: lots, capacities, stalls.
2. Simulator producing believable weekday occupancy for 3 to 4 lots.
3. Within-lot predictor **beats the naive baseline** (uniform guess from the sensed fraction) on spot-level accuracy.
4. Across-lot predictor shows a **measured accuracy gain on Birmingham** when 20 to 30% of lots are sensed vs. none.
5. **Sensor placement result:** spread-out sensors outperform entrance-clustered ones. *"This is the slide that matters for Park Shark beyond the hackathon."*
6. Demo slider working end to end: % sensed → sharper map + rising accuracy curve, **in under 60 seconds of walkthrough**.

> Why it is worth a day: objectives 3 to 5 are the actual research result, a **sensor-density-versus-accuracy curve**, which every Park Shark deployment will need, obtained before a single sensor exists.

---

## 4. The fly brain: science, data and code

### 4.1 The idea (from the handbook)
Someone mapped every neuron and synapse in a fruit fly's brain. Simulate each neuron as a simple spiking unit, wire them exactly as the map says, and the circuits just work: sugar on the mouth makes the feeding neuron fire; a looming shadow makes the escape neuron fire. **The wiring is the model.** Your job: (1) turn your problem's signals into stimulation of the fly's senses; (2) read the answer off neurons with known behaviours.

> **The rule:** if your problem can't be phrased as *"this tastes good / bad / looms at me" → "eat / back off / flee"*, a fly brain is the wrong tool.

Parking fits the rule: *a lot with a likely free spot close by tastes good; uncertainty, permit risk and price taste bitter; a lot filling up fast looms at you.* → *commit (eat) / back off / divert now (flee).*

### 4.2 The model (Shiu et al. 2024, Nature, doi:10.1038/s41586-024-07763-9)
- Leaky integrate-and-fire. Rest **−52 mV**, threshold **−45 mV**, membrane τ **20 ms**, synapse τ **5 ms**, refractory **2.2 ms**, delay **1.8 ms**, **0.275 mV per synapse**, step **0.1 ms**.
- Weight = synapse count × sign. ACh excites; GABA, glutamate and histamine inhibit. Use Shiu's signed file, never raw transmitter predictions.
- Input: Poisson spikes on sensory neurons at 0 to 200 Hz. Output: firing rate of known output neurons.

### 4.3 Senses and outputs
| Sense | Neurons in starter | Meaning | Status |
|---|---|---|---|
| Sugar | `cell_type == "LB3c"` | good, approach | solid |
| Bitter | `cell_sub_class == "bitter"` | bad, suppresses eating | solid |
| Looming | `cell_type in ["LC4","LPLC2"]` | threat, sudden change | solid, triggers escape |
| Smell, wind | — | — | **seizes (everything fires forever); skip** |

| Output | Neuron | Behaviour | Our meaning |
|---|---|---|---|
| `mn9` | root_id `720575940660219265` (from Shiu) | extend proboscis, eat | **commit to this lot** (rate = how strongly) |
| `giant_fibre` | `DNp01` | escape jump | **divert now** (any spike overrides) |
| `mdn` | `MDN` | walk backwards | **back off / keep looking** |
| `DNp09` | `DNp09` | walk forward | optional: "advance toward the lot" |

### 4.4 The starter notebook (what it actually does)
Colab: https://colab.research.google.com/drive/1yvokSEsWGbSBbsGVhYrR9thfjRXfCpHr
1. `pip install fafbseg==3.2.3 navis==1.12.0 plotly crackle-codec`
2. FlyWire token via `getpass` (only for the 3D Giant Fibre render; **never commit a token**). Token page: https://global.daf-apis.com/auth/api/v1/create_token
3. 3D render of DNp01 with `navis.plot3d(flywire.get_skeletons(...))`.
4. Load the whole brain **with no token**:
   ```python
   SHIU = "https://github.com/philshiu/Drosophila_brain_model/raw/main/"
   neurons = pd.read_csv(SHIU + "Completeness_783.csv", index_col=0)
   wiring  = pd.read_parquet(SHIU + "Connectivity_783.parquet")
   labels  = pd.read_csv("https://github.com/flyconnectome/flywire_annotations/raw/main/supplemental_files/"
                         "Supplemental_file1_neuron_annotations.tsv", sep="\t", low_memory=False)
   N = len(neurons)
   W = sp.csr_matrix((wiring["Excitatory x Connectivity"],
                      (wiring["Presynaptic_Index"], wiring["Postsynaptic_Index"])), shape=(N, N))
   ```
   `W[pre, post]`: **rows are presynaptic, columns are postsynaptic.**
5. `simulate(inputs, ms=200, W=W, seed=0)` returns a spike count per neuron; `rate(counts, group, ms=200)` returns the mean Hz of a group. Each run is 200 ms of brain time, starts from rest, and takes **a few seconds on CPU**.
6. Expected sanity results: nothing → nothing; sugar 200 Hz → MN9 fires (~50 Hz); sugar + bitter → MN9 drops a lot; looming 150 Hz → Giant Fibre fires.
7. Lesion example from the notebook: `keep = np.ones(N); keep[giant_fibre] = 0; W_lesion = (sp.diags(keep) @ W).tocsr()`. This zeroes the **rows** of W, so the Giant Fibre **still fires but nobody hears it**.

### 4.5 Handbook gotchas
- **Signs make or break it.** One mislabeled inhibitory neuron and a region seizes.
- **Run the six sanity checks before building anything:** no input → silence; sugar → MN9 ~50 Hz; sugar + bitter → MN9 drops; looming → Giant Fibre; Giant Fibre silenced → no escape; input stops → activity dies. If any fail, the wiring is wrong, not the idea.
- **Reset between decisions:** 100 to 200 ms from rest each time; feed memory back in as input if needed.
- **Clip inputs at about 2 standard deviations** so one outlier doesn't max out a sense.
- **Compare against a dumb baseline.** The fly is a weird fixed filter, not an optimizer.
- Compute: CPU is enough; Colab T4 or Modal for thousands of runs.

### 4.6 Other resources
FlyWire https://flywire.ai · Codex https://codex.flywire.ai (look up MN9, DNp01, etc.) · fafbseg docs https://fafbseg-py.readthedocs.io · Shiu model https://github.com/philshiu/Drosophila_brain_model · BANC (brain + nerve cord, 169k, adds jump muscle TTMn) · Male CNS v1.0 (June 2026) https://male-cns.janelia.org · neuPrint https://neuprint.janelia.org · flybody (MuJoCo fly body) https://github.com/TuragaLab/flybody · FlyWire paper doi:10.1038/s41586-024-07558-y.

Handbook project ideas, for reference: trading bot (momentum → sugar/bitter, crash → looming, MN9 = position size, GF = sell all; "lost money, but less than holding"), drone dodging, game agent, anomaly pager, fly in a body, **lesion lab** ("the real science use"), male vs female.

---

## 5. NC State data (verified live today)

### 5.1 Official NCSU parking polygons (primary source)
```
https://gismaps.oit.ncsu.edu/arcgis/rest/services/Transportation/Transportation_OnlineCampusMap/MapServer/1/query?where=1%3D1&outFields=*&outSR=4326&f=geojson
```
- Returns **214 polygon features** (~1.2 MB). Fields include `NAME, SPACES, ZONE_, Type (Surface/Deck), STATUS, HC, EV, PY (pay), V (visitor), VP, Motorcycle` and per-permit space counts `A4, AB, AS_, B, C, C_CC, C_DD, CD, CL, F, GV, LD, LO, RC, RCS, RD, RE, RF, RH_CC, RS, RV, RW, SV, SV_UV, UE, UV, W, ZIP, C_CB`.
- **A physical deck is split into several features by permit section** (e.g., *Partners Way Deck - Visitor Pay Area* 99, *Partners Way Deck - C/CC* 630, *Partners Way Deck - C* 99, *Partners Way Deck Extension (Upper)* 207). Group sections into physical facilities by name prefix and geometry overlap, and keep per-section counts.
- Lots near **Hunt Library (Centennial Campus)** found today: Partners I Lot (76, C), Partners II Lot (63, C/CC), Partners II Lots - F (226), Oval Drive (49, C), Oval Drive (43, C), Oval West Deck (595, C), Partners Way Deck (sections above), Hunt Library Annex Lot (2, SV), Varsity Lot / Varsity Research Lot.
- Lots near main campus: Riddick Lot (70, B), Coliseum Deck (CD 1694, RE 223, visitor pay 275 + 66), Dan Allen Deck (C/DD 991, visitor pay 225), Dan Allen Carriageway visitor pay (31).
- Weekend rule (ASSUMED, verify signs): most NCSU permit zones relax on weekends; residence zones (`R*`) do not.

### 5.2 OpenStreetMap
`overpass_q.txt` in this repo queries `amenity=parking` ways/relations and `building=parking` in bbox `(35.755,-78.700,35.800,-78.650)`. Use OSM for drive-aisle/entrance hints, `parking_space` stalls if any exist, and buildings to subtract. NCSU polygons win for names and capacities.

### 5.3 Destinations
- **Hunt Library** (the brief's example), Centennial Campus, approx. 35.7693, −78.6765. Geocode from OSM to confirm.
- **Hack Day venue**: this repo currently says *Riddick Hall* with an approximate pin flagged "set exact pin before demo". Geocode it from OSM (`name~"Riddick"`) instead of trusting the hard-coded value.

---

## 6. Current state of this repo (`momacaes9/parkfly`)

| File | What it does today |
|---|---|
| `build_ncstate.py` | Reads `ncstate_parking_raw.geojson` if present, else a 10-lot **SEED** set (approximate coords). Hand-set 24-hour occupancy templates per profile (commuter/deck/pay/resident/visitor), Saturday multipliers, permit usability for a "no-permit student" persona, walk minutes (straight line × 1.35 path factor / 80 m/min). Writes `web/data.json` (lots + 24 h estimates with ±band) and `senses.json` (sugar/bitter/looming Hz per lot for Saturday 10:00 → Riddick Hall), winsorized at 2 SD. |
| `fly_decides_parking.ipynb` | Runs after the organizers' starter. Uploads `senses.json`, one 200 ms brain run per lot, verdict `FLEE` if GF > 5 Hz, `BACK OFF` if MDN > MN9, else `EAT`. Dumb baseline (sugar − bitter − looming). Lesion cell. Exports `decisions.json`. |
| `web/index.html` | Leaflet map (vendored), Park Shark branding, hour slider, per-lot cards with estimate band, sense bars, and fly verdict when `decisions.json` exists. |
| `senses.json`, `web/data.json` | Built from SEED data. |

**It does not yet do the brief:** no per-spot model, no simulator, no sensor-density slider, no accuracy curve, no across-lot spillover, no Birmingham validation, no sensor-placement result.

### 6.1 Known bugs and weaknesses (fix them)
1. **The lesion cell proves nothing.** `W_lesion = sp.diags(keep) @ W` silences the Giant Fibre's **outputs** (rows), but the verdict reads `rate(c, giant_fibre)`, which still fires. The verdict is identical intact vs. lesioned. Fix: lesion its **inputs** (`W @ sp.diags(keep)`, zeroing columns) so it cannot fire, *or* keep the output lesion and read a downstream readout. Then show the behavioral change.
2. **`p_free` saturates at 1.0** for every lot (`1 − exp(−free/3)` hits 1 with more than ~10 free spaces), so sugar depends only on walk time. Replace it with the posterior from the within-lot model.
3. **Bitter is all-or-nothing** (200 Hz for every paid deck, 0 elsewhere) because min-max normalization over few lots maps any price to the max.
4. **SEED coordinates and capacities are approximate.** The real NCSU endpoint works; use it.
5. **Verdict thresholds are arbitrary** (GF > 5 Hz). Calibrate them from the measured response surface and the sanity checks.
6. **One seed, one MN9 neuron:** rates are noisy. Average 2 to 3 seeds.
7. Venue pin is approximate (see 5.3).

---

## 7. The concept we are building: **ParkFly**

> **A fly never sees the whole world. It reads a few senses and acts, and it rarely lands in the wrong place. Park Shark will never put a sensor on every spot. ParkFly reads 25% of a parking lot, infers the other 75%, and lets a real fruit-fly brain decide where to park.**

The two halves click together:
1. **Sparse sensing → full state (the Park Shark research result).** Within-lot fill model + across-lot spillover, measured against baselines, with a sensor-density-vs-accuracy curve and a sensor-placement result.
2. **Full state → decision (the fly).** Each lot's posterior becomes tastes:
   - **sugar** = expected number of free spots you may legally use, discounted by walk time
   - **bitter** = **uncertainty** (posterior spread) + permit risk + price. *Uncertainty tastes bitter.*
   - **looming** = the lot is filling fast or is nearly full (predicted fill rate and P(full on arrival))
   The real connectome answers with MN9 (commit), MDN (back off) and Giant Fibre (divert now).

**The demo moment:** with few sensors the fly hesitates, because everything tastes a little bitter. Slide sensors up and the fly commits. Lesion the Giant Fibre and the fly drives straight into a lot that is filling up. That is real connectome behavior, driven by our sensor-density result.

### 7.1 Why the fly can run live in a browser
One brain run takes seconds, too slow for a slider. So in Colab we **precompute the fly's response surface**: a grid of (sugar, bitter, looming) input rates → mean MN9 / Giant Fibre / MDN rates over 2 to 3 seeds, for the intact brain and the Giant-Fibre-lesioned brain. Export it to `fly_surface.json` with provenance (neuron count, connection count, seeds, grid, run date, Shiu file version 783). The web app trilinearly interpolates that surface in real time. Every verdict on screen traces back to real spiking simulations on the real wiring. Also export a **spike raster** (a few hundred tracked neurons: sensory, outputs and a random sample) for 3 canonical scenarios so the UI can show the brain "thinking", plus the **sanity-check table**.

---

## 8. Honesty rules (Park Shark house style; judges reward it)
- Every number on screen is computed by code in this repo or in the exported Colab results. **No hand-typed metrics.**
- Label everything: *simulated ground truth*, *estimated*, *official NCSU count*, *Birmingham (real, 2016, UK)*.
- No real sensor exists yet: the ground truth is a simulation. Say it out loud and say why it is still useful (it isolates the inference question; Birmingham checks the across-lot part on real data).
- The fly is a fixed filter, not an optimizer. Always show the dumb baseline next to it.
- Seeds fixed, results reproducible, assumptions listed in one place.
- Never commit the FlyWire token or any key.

## 9. Glossary
- **Fill level f:** the fraction of a lot's spots occupied, 0 to 1.
- **Attractiveness rank r:** the order in which a spot tends to fill (closest to entrance/destination first).
- **Fill frontier:** the rank around which spots flip from mostly occupied to mostly free; sensors there carry the most information.
- **Spillover:** an exactly sensed lot shifting its neighbors' estimates.
- **Response surface:** the fly's output rates as a function of the three input rates.
- **MN9 / DNp01 / MDN:** feeding motor neuron / Giant Fibre escape command / moonwalker descending neuron.
