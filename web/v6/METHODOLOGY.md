# Park Shark × Fly Brain — NC State. What the numbers actually are.

Nothing here is measured from a sensor. Every occupancy figure is a model estimate
with a stated band. This document says exactly which inputs are real, which are
assumed, how they combine, and what each layer licenses us to conclude.

---

## LAYER 0 — Facility truth (REAL)

**Source:** NC State OIT GIS, `Transportation/Transportation_OnlineCampusMap`,
layer 1 "Parking Areas" (public ArcGIS REST service), retrieved 2026-11-14.
214 polygons, 203 with a capacity, 22,657 spaces total. We keep the 144 within a
30-minute walk of Riddick Hall.

**Fields used, verbatim from their schema:**
- `NAME`, `ZONE_`, `Type` (Surface / Deck / Priv Deck / Gravel), `SPACES`
- Per-permit-type space counts as separate integer columns: `A4 AB AS_ B C C_CC
  C_DD CD CL F GV LD LO PY RC RD RE RF RH_CC RS RV RW SV SV_UV UE UV V VC VP W
  ZIP RCS C_CB`, plus `HC` (accessible) and `EV`.
- Polygon geometry (EPSG:4326 after reprojection by the server).

Second source: layer 0 "Paylot Entrances" — 27 points naming the visitor pay areas.

**Conclusion this licenses:** where every lot is, how big it is, who is allowed to
park in it, and how many accessible/EV spaces it has. These are facts, not estimates.

---

## LAYER 1 — Baseline occupancy curve per lot (REAL mix × ASSUMED shapes)

The novel part. Rather than one campus-wide curve, each lot gets a curve built from
**its own official permit composition**.

1. Every permit column is mapped to one of four behaviour archetypes:
   - `commuter` (A4, AB, B, C, CD, CL, F, W, C_CB…) — arrives ~8am, leaves ~5pm
   - `resident` (RC, RD, RE, RF, RH_CC, RS, RV, RW, RCS) — **inverted**: full
     overnight, empties during the day
   - `visitor` (PY, V, VC, VP, ZIP) — midday bell
   - `service` (AS_, GV, LD, LO, SV, SV_UV, UE, UV) — early start, flat
2. The lot's baseline for hour *h* is the **space-weighted blend** of those four
   archetype curves:
   `baseline[h] = Σ_k (spaces_k / total) × ARCH_k[h] × (weekend multiplier if Sat)`

**ASSUMED:** the four 24-hour archetype shapes and the weekend multipliers
(commuter ×0.15, resident ×0.95, visitor ×0.45, service ×0.25) are hand-written in
`build_ncstate.py`. They are not fitted to NC State data — no such data is public.

**Why this is still defensible:** the *weights* are official. A lot that is 90%
`RW` resident permits genuinely behaves inversely to a commuter lot, and the model
reproduces that from real composition rather than assumption. The shape is assumed;
the mix driving it is not.

**Upgrade path:** replace archetype shapes with per-lot histories once gate counts
or floor sensors report. The blend structure does not change.

---

## LAYER 2 — Destination demand, gravity-assigned (ASSUMED curves, REAL geometry)

People do not park in lots; they park *for* destinations. Nine campus destinations
carry an hourly busyness curve and a peak cars/hour figure. Each destination's
demand is distributed across nearby lots by a **gravity / Huff assignment**:

```
weight(lot) ∝ usable_capacity(lot) × exp( − walk_minutes / τ ),  τ = 6 min
share(lot)  = weight(lot) / Σ weights
added_occupancy[h] = peak × curve[h] × share × (dwell_hours) / spaces
```

Lots within 12 walking minutes of a destination compete for its demand; bigger and
closer lots absorb more. The Hack Day event is injected the same way at Riddick
Hall, 9:00–16:30.

**ASSUMED:** the nine curves, the peak cars/hour figures, τ = 6 min, average dwell
times (visitor 90 min, pay 110, commuter 300, deck 240, resident 900).
**REAL:** which lots are near which destination, and their usable capacities.

**Conclusion this licenses:** the *relative* ordering and timing of how demand
spreads across campus — when Talley gets busy, its nearest usable lots fill first
and overflow outward. It does not license a claim about absolute car counts.

**Upgrade path (the important one):** Google Popular Times gives measured hourly
busyness per destination, including a live "busier than usual" signal, which drops
straight into `curve[h]` without touching the assignment maths. On weekdays, NC
State's public course schedule gives building-level class headcounts by hour — a
cleaner demand signal than any commercial product. Commercial probe/GPS data
(StreetLight, INRIX) is the paid equivalent; Google Maps navigation-destination
counts are **not** publicly available, so the Popular Times route is the realistic one.

---

## LAYER 3 — Derived driver quantities

```
occupancy[h]   = baseline[h] + assigned_demand[h]          (capped at 0.99)
band           = ±10 points, widened to ±16 where layer 2 contributes
usable(you)    = visitor/pay spaces  (+ weekend: all non-resident spaces, ASSUMED)
permit_risk    = 1 − usable / total
free_now       = usable × (1 − occupancy)
P(open spot)   = 1 − exp(−free_now / 3)      Poisson-style: ≥1 of the usable spaces free
fill_rate[h]   = occupancy[h+1] − occupancy[h]
wait_minutes   = dwell / (spaces × (1 − occupancy))        shown only above 90% full
```

`wait_minutes` is an elementary queueing approximation — expected time until one of
the occupied spaces turns over — displayed next to the next-best lot's drive time so
the "wait or drive on" trade is explicit.

---

## LAYER 4 — Stall layouts (REAL outline + REAL count + GEOMETRIC inference)

For 63 surface lots (`make_layouts.py`):
1. Take the official polygon and the official `SPACES` count.
2. Find the lot's dominant axis (longest edge of its minimum-area rotated rectangle).
3. Lay double-loaded rows along that axis using US standard dimensions: 9 ft × 18 ft
   stalls (2.75 m × 5.5 m), 24 ft (7.3 m) drive aisles.
4. Keep only stalls whose footprint falls entirely inside the real polygon.
5. Compare the generated count with the official count and publish only if they
   agree to ≥45%; trim any overshoot from the outermost row.

**Validation:** several lots reproduce the official capacity exactly from geometry
alone — Wood Lot 73/73, Weaver Lot North 45/45, Carmichael 83/83, Boney Drive
238/238. That agreement is an independent check that the geometric model is sane.

**What it is not:** stall *positions* are inferred, not observed. Which stalls show
as taken follows the estimated occupancy, filling from the rows nearest the
entrance — it is not a per-car observation. Decks are excluded (multi-level).

**Upgrade path:** a parking-stall detector — ESRI's Mask R-CNN "Parking Spot
Detection — USA" model on ArcGIS Living Atlas — over 6-inch NC OneMap
orthoimagery recovers true stripe positions. That needs imagery access this build
does not have.

---

## LAYER 5 — Lot metrics → fly senses

Each lot's driver-relevant numbers become stimulation rates for three real sensory
populations. Raw scores are clipped at ±2 SD across all 144 lots (handbook
guidance) and mapped onto the fly's physiological ranges.

```
sugar   = P(open spot) × exp(−walk/10) × (1.1 if covered)      → 0–200 Hz  (LB3c, 32 cells)
bitter  = 0.55·permit_risk + 0.30·(price/$4) + 0.15·(walk/30)  → 0–200 Hz  (bitter GRNs, 42 cells)
looming = 10 × fill_rate + 0.6 if occupancy > 85%              → 0–150 Hz  (LC4 + LPLC2, 314 cells)
```

The reasoning: sugar is "this is food" (a space you can actually use, close by);
bitter is "this tastes wrong" (you may not be allowed, it costs, it is far);
looming is "something is rushing at me" (the lot is filling as you approach, which
is genuinely a threat expanding in time). Smell and wind are deliberately unused —
the handbook warns those populations send the network into runaway activity.

The per-lot detail page shows every term with its number, so each Hz figure is traceable.

---

## LAYER 6 — The brain (REAL connectome, no training)

- **Wiring:** FlyWire whole-brain connectome, Shiu et al. 2024 release —
  138,639 neurons, 15,091,983 signed synaptic connections
  (`Connectivity_783.parquet`, sign already applied by neurotransmitter identity).
- **Neurons:** leaky integrate-and-fire, Shiu parameters exactly — rest −52 mV,
  threshold −45 mV, membrane 20 ms, synaptic 5 ms, refractory 2.2 ms, delay 1.8 ms,
  0.275 mV per synapse, 0.1 ms timestep. Nothing is trained; the wiring is the model.
- **Readouts:** MN9 (proboscis extension = commit), DNp01 Giant Fibre (escape =
  divert now), MDN (walk backwards = back off).
- **Verdict rule:** escape drive vs feeding drive — `FLEE if GF > MN9`, else
  `BACK if MDN > MN9`, else `EAT`. Not a hand-set threshold.

**Sanity suite (handbook's own, all passing):**

| stimulus | MN9 | Giant Fibre | MDN | active neurons |
|---|---|---|---|---|
| nothing | 0 Hz | 0 Hz | 0 Hz | 0 |
| sugar 200 Hz | 290 Hz | 0 | 0 | 509 |
| sugar + bitter | 0 Hz | 0 | 0 | 299 |
| looming 150 Hz | 0 Hz | 335 Hz | 37.5 Hz | 1,771 |

**Graded response check** (sugar held at 150 Hz, looming increasing):
GF 55 → 162 → 255 → 332 Hz while MN9 falls 285 → 215 → 65 → 0 Hz. The circuit
trades the two drives off continuously; it is not a switch.

**Routing:** the campus is a graph of lots, four entry gates and the destination.
At each node the fly tastes up to three next hops — progress toward target = sugar,
street congestion on that edge = bitter, target's looming carried forward — and the
brain picks the hop. ~30–40 whole-brain runs per journey. If the Giant Fibre fires
on the target itself, the fly abandons it and re-targets the next-ranked lot.

**ASSUMED here:** the campus congestion-by-hour curve on graph edges, and the
straight-line k-nearest-neighbour graph standing in for the real street network.
Upgrade: TomTom or HERE flow (both free-tier, live, sub-hour) on a real OSM street
graph.

**Conclusion this licenses:** that a fixed biological circuit, fed honest parking
estimates, produces sensible and *varying* driver behaviour. It does not license a
claim that the fly is optimal — which is why the dumb baseline comparison and the
Giant-Fibre lesion control are both in the notebook.

---

## What is real vs assumed, in one table

| Quantity | Status |
|---|---|
| Lot location, outline, capacity, permit mix, ADA, EV | **REAL** (NCSU GIS) |
| Visitor pay areas | **REAL** (NCSU GIS) |
| Connectome wiring, neuron parameters, firing rates | **REAL** (FlyWire / Shiu 2024) |
| Stall count per lot | **REAL**; stall *positions* inferred |
| Archetype hour curves, weekend relaxation | ASSUMED |
| Destination busyness curves, peak cars/h, τ, dwell | ASSUMED |
| Street congestion curve, graph edges | ASSUMED |
| Prices ($2/hr where a pay area exists) | ASSUMED placeholder |
| Any claim that a specific space is free right now | **NOT CLAIMED** |

## References

- Shiu et al., *A Drosophila computational brain model reveals sensorimotor
  processing*, Nature 634 (2024). https://www.nature.com/articles/s41586-024-07763-9
- Dorkenwald et al., *Neuronal wiring diagram of an adult brain* (FlyWire), Nature
  634 (2024). https://www.nature.com/articles/s41586-024-07558-y
- Dasgupta, Stevens & Navlakha, *A neural algorithm for a fundamental computing
  problem*, Science 358 (2017) — the fly's sparse-hashing circuit.
- Pierce & Shoup, *Getting the prices right* (SFpark), JAPA 79 (2013) — occupancy
  sensing and pricing.
- Mathur et al., *ParkNet: drive-by sensing of road-side parking statistics*,
  MobiSys 2010 — mobile estimation of occupancy.
- Caliskan, Barthels, Scheuermann & Mauve, *Predicting parking lot occupancy in
  vehicular ad hoc networks*, IEEE VTC 2007 — queueing-based occupancy prediction.
- Birmingham parking occupancy dataset, UCI ML Repository #482.
- ESRI *Parking Spot Detection — USA* (Mask R-CNN), ArcGIS Living Atlas.
