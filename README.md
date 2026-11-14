# 🪰 ParkFly

**[Live demo](https://parkfly-one.vercel.app/)** · **[Presentation slides](https://docs.google.com/presentation/d/1NMZ2MkxVWt5iTS0ScvXacDKuxeLWPxYafFl55cUWAJo/edit?usp=sharing)** · **[V6 campus map](https://parkfly-one.vercel.app/v6/)**

A parking simulation that turns partial observations into sensory inputs for a real fruit-fly connectome. Move the sensor slider, compare hidden-spot predictions, and test how a Giant-Fibre input lesion changes the fly's parking decision.

## How it works

1. Simulate occupancy on official NC State parking geometry. Individual spot positions are estimated.
2. Observe a chosen fraction of spots; infer the rest with a Bayesian fill model.
3. Encode availability, uncertainty and rising occupancy as sugar, bitter and looming inputs.
4. Read **commit / back off / divert** from saved spiking responses of the real **138,639-neuron** FlyWire/Shiu v783 graph.

The browser interpolates **480 recorded full-brain simulations**. Training selects among **81 sensory-encoder configurations** on 14 simulated days; the biological wiring stays fixed.

## Results at 25% sensing

| Experiment | Result | Comparison |
|---|---:|---:|
| Hidden-spot prediction accuracy, simulated | **81.88%** | Baseline **72.87%** |
| Brain-policy free-spot success, simulated | **151/156 (96.79%)** | Original encoder **150/156 (96.15%)** |
| Birmingham hidden-lot MAE, real historical data | **0.0473** | Baseline **0.0702** |

Brain-policy tests cover four held-out simulated days. Its one-case improvement has a 95% paired interval of **0–1.92 percentage points**, including zero. Birmingham uses 28 car parks and a chronological 51-day training / 22-day test split. These are separate experiments; neither establishes live NC State parking accuracy.

## Demo and data

**Use the main demo for judging:** https://parkfly-one.vercel.app/ . It contains the sensor experiment, accuracy curves, neural readouts and lesion toggle. The **V6 campus map** is an additional view with 144 lots, 17,527 official capacity spaces and 75 estimated layouts; its imported neural export covers the default weekday 10am scenario. Other settings use labeled heuristic scores.

NC State supplies official geometry and capacity through `/api/ncsu`, **not live occupancy**. The default basemap is the official NC State campus map (NC State University GIS), with OpenStreetMap, Carto and an offline polygon view as automatic fallbacks. Optional browser GPS updates estimated travel inputs after permission. Parking occupancy, stall layouts and travel times are simulated or estimated.

**Libraries:** NumPy, SciPy sparse, pandas and PyArrow for the connectome; Leaflet for maps. FAFBseg/Navis/Plotly skeleton visualization is optional. Flybody is not used.

[Detailed model report](https://parkfly-one.vercel.app/lab/README.md) · [Colab notebook](colab/fly_surface.ipynb) · [Demo script and Q&A](https://parkfly-one.vercel.app/lab/demo.html)

Sources: FlyWire; Shiu et al. 2024; NC State Transportation GIS; OpenStreetMap; Birmingham UCI #482; NC State Fly Brain Starter. Source methods adapted from [parkshark](https://github.com/momacaes9/parkshark). No AI-generated images.
