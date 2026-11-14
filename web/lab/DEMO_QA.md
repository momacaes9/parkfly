# ParkFly — judge Q&A and numbers

Respostas prontas em inglês. Leia a seção de métricas antes de apresentar. Prefira uma resposta curta e ofereça o detalhe se o juiz pedir.

## 1. Is this actually using the fly brain data?

Yes. We use the real signed FlyWire/Shiu v783 connectivity, its neuron table, and cell annotations. The browser’s action readouts come from measured simulations of that fixed network. MN9, MDN and DNp01 are actual labeled output groups, and the lesion changes their behavior.

## 2. What exactly did you train?

We trained the parking-to-sense encoder: walk discount, uncertainty gain, fill-rise gain and near-full gain. We did not change the biological synapses. We searched 81 settings on 14 simulated training days, then fixed the encoder before evaluating four other days.

## 3. How much better did it get?

At 25% coverage it found a free spot in 151 of 156 cases, versus 150 for the original encoder: 96.79% versus 96.15%. Mean modeled cost was 1.583 versus 1.763 minutes. This is a small synthetic-data result, and we show that explicitly.

## 4. Is that statistically significant?

We do not make that claim. The paired 95% interval is 0 to 1.92 percentage points using whole-day bootstrap resampling. There are only four test days; observations within a day are correlated. More independently simulated days and real observations are needed.

## 5. Are all 156 test cases independent?

No. They are 39 arrival-time snapshots on each of four simulated days. That is why we resample days, not isolated arrivals, for uncertainty. Coverage points reuse the same days and should not be treated as new independent deployments.

## 6. Is the full brain running in the browser?

The full numerical simulations run offline. We export an 80-point sensory grid for intact and lesioned brains with three seeds: 480 runs. The browser performs trilinear interpolation of those measured output rates. The raster is recorded canonical playback. Device GPS and the parking posterior update interactively.

## 7. Why use a fly at all?

The starter provides sensory-to-action circuits that fit a concrete experimental question: good, bad and looming inputs producing approach, retreat and escape. Parking supplies a controllable environment for testing encoding, partial observations and causal circuit changes. We compare it against ordinary rules rather than assuming biology is optimal.

## 8. Did the fly beat a simple baseline?

At 25% in this test, the calibrated fly has 151/156 successes and 1.583-minute modeled cost. Nearest-lot has 150/156 and 1.599 minutes. The original fly has 150/156 and 1.763 minutes. The gain is small; there is no universal-superiority claim. The oracle reaches 154/156 at 1.471 minutes.

## 9. Why isn’t the oracle at 100%?

In two test cases, every eligible candidate lot is full. Even a policy with perfect state information cannot choose an available eligible spot in those cases.

## 10. What does the lesion prove?

It proves that the selected readout responds to a specific circuit intervention. We zero the Giant Fibre’s incoming columns because our verdict reads its firing rate. The original starter’s outgoing-row lesion is a different valid intervention: the neuron can still fire while its downstream effect is cut. We use the input lesion to make the readout change interpretable.

## 11. Did you cherry-pick that scene?

We deliberately selected a reproducible held-out scene to demonstrate the intervention: five free spots now, zero fifteen minutes later, DIVERT versus COMMIT. That example is separate from the full 156-case accuracy evaluation at each coverage. It is not presented as an unbiased estimate of benefit.

## 12. Does lesioning make overall accuracy worse?

At 25% coverage, calibrated intact and calibrated lesioned success rates tie at 96.79%. Their mean costs are 1.583 and 1.567 minutes. The selected scene illustrates behavior; aggregate data do not establish that intact wiring improves this parking policy overall.

## 13. Why is the dashboard showing 94% but you say 82%?

The live KPI is the selected snapshot and observation mask. The held-out chart averages many snapshots and masks. At 25%, within-lot held-out accuracy is 81.88%, or 82.04% with simulated spillover, versus 72.87% naive. Those estimates describe different evaluation scopes from one live snapshot.

## 14. What is Brier score?

It is the mean squared error between a predicted occupancy probability and the simulated occupied/free outcome, evaluated on unsensed spots. Lower is better. At 25%, within-lot Brier is 0.1232 versus 0.1789 naive; adding simulated across-lot conditioning gives 0.1226. Probability calibration can matter even when a 0.5-threshold accuracy score changes little.

## 15. What do the uncertainty bands mean?

The occupancy-density band is one standard deviation over evaluated simulated moments/layouts. The fly success band is a 95% interval from resampling whole test days. Birmingham’s quoted SD describes variability across random sensor masks. We label these separately because they measure different variation.

## 16. What is official NC State data?

The public GIS API provides geometry, capacities and permit information. It currently returns 214 features; 203 active/existing positive-capacity polygons are displayed. The focus model has seven permit sections in six physical facilities, with 478 estimated spot positions. Occupancy is simulated; this feed supplies no live stall availability.

## 17. What is real in the Birmingham experiment?

Actual 2016 occupancy observations. We convert counts to rates, remove broken rows, round UK-local timestamps to half hours, and retain 28 sufficiently covered lots using training data. We train on 51 days, test on 22 later days, and compare both methods on identical hidden targets. There is no interpolation across the split. Birmingham has no coordinates, so covariance is empirical.

## 18. What does the 32.5% mean?

It is a relative reduction in hidden-lot occupancy MAE: 0.07016 to 0.04734 at 25% of lots sensed. That is roughly 7.02 to 4.73 occupancy percentage points of absolute error. The SD across 200 sensor draws is 0.00548. It measures across-lot inference, not fly decision accuracy.

## 19. How did you use the libraries well?

NumPy stores and updates neuron voltages, conductances, Poisson draws and spikes. SciPy CSR keeps the signed graph sparse and propagates spikes through the actual wiring. pandas joins neuron IDs to cell-type annotations; PyArrow reads the parquet connectivity. Fixed seeds and exported provenance make repeated experiments comparable. We reuse the starter’s LIF settings and test six expected responses before evaluating parking behavior.

## 20. Did you use FAFBseg, Navis, Plotly or flybody?

The supplied optional Colab cell uses FAFBseg 3.2.3, Navis 1.12.0 and Plotly for a Giant Fibre skeleton; it needs a private FlyWire token. That authenticated visualization was not required or verified here. The numerical decision pipeline uses the public-table NumPy/SciPy/pandas model. Flybody is a future embodiment option and is not part of the implemented application.

## 21. Why does the token error not stop the brain model?

The token authorizes skeleton/CAVE access for the optional visual view. The complete neuron, signed-wiring and annotation tables used by the numerical model are public. We keep those execution paths separate so the scientific simulation does not depend on a visualization credential.

## 22. How do you know the simulation is wired correctly?

All six checks passed: silence with no input; sugar activates MN9; bitter suppresses it; looming activates Giant Fibre; cutting its inputs makes its rate zero; activity decays after input stops. In the saved seed-zero sanity test, sugar produces 100 Hz MN9, sugar plus bitter 5 Hz, looming 265 Hz GF, and the GF-input lesion 0 Hz.

## 23. What are the biological model settings?

Leaky integrate-and-fire with rest −52 mV, threshold −45 mV, membrane time constant 20 ms, synaptic time constant 5 ms, refractory 2.2 ms, delay 1.8 ms, signed synapse scaling 0.275 mV, and a 0.1 ms time step. These follow the provided starter/Shiu settings. Each decision run starts from rest for 200 ms.

## 24. What is your biggest limitation?

External validity. Parking state and demand are simulated; geometry and capacities are official, but positions and travel costs are estimates. The encoder is fitted to that simulator, and the test set has four days. Our strongest biological demonstration is an interpretable intervention on real wiring. Broader simulation tests and measured parking observations are the next validation steps.

## 25. What is actually connected live?

The production app runs at https://parkfly-one.vercel.app. Its read-only NCSU proxy verifies official lot information. With browser permission, device GPS updates an explicitly estimated trip cost into the encoder; coordinates stay in page memory, while tile providers receive viewed-area requests. The brain response table is fixed measured data, and occupancy remains simulated.

## 26. Is the source on GitHub?

The project repository is momacaes9/parkfly. The implementation is committed locally, and production is deployed. At this handoff GitHub writes have returned HTTP 403, so do not claim the latest source is already on remote main. The deployed lab provides its measured JSON, model report and reproducible brain notebook; repository publication is a separate access step.

## Number card — keep beside the laptop

| Number | Meaning | Source |
|---|---|---|
| 138,639 | Real v783 neurons | fly_surface.json → provenance |
| 15,091,983 | Nonzero signed weighted neuron-pair connections | same |
| 480 | 80 inputs × 2 conditions × 3 seeds | same |
| 200 ms / 0.1 ms | Run duration / simulation step | starter + provenance |
| 14 / 4 days | Encoder training / held-out simulated evaluation | fly_calibration.json |
| 81 | Encoder candidates | same |
| 2184 | Training decision cases over four coverages | same |
| 156 | Test cases at each coverage, 39 × 4 days | same |
| 151 vs 150 | Successful cases at 25%, calibrated vs original | same |
| 96.79% vs 96.15% | Those fractions as percentages | same |
| +0.64 pp; interval 0–1.92 pp | Small paired gain with day-bootstrap interval | same |
| 1.583 vs 1.763 min | Modeled cost, calibrated vs original | same |
| 81.88% vs 72.87% | Within-lot unsensed accuracy at 25% | results.json |
| 0.1232 vs 0.1789 | Within-lot Brier at 25% | same |
| 0.1226 | Brier with simulated spillover | same |
| 0.1270 vs 0.1453 | Spread vs entrance Brier | same |
| 28 lots; 51/22 days | Retained real Birmingham data / split | birmingham.json |
| 32.5% | Birmingham relative MAE reduction | same |

## Avoid these claims

- “We trained 139,000 neurons on parking.” Say the encoder was trained and the connectome was fixed.
- “The live map shows measured parking availability.” Say official geometry/capacity plus simulated occupancy.
- “The one-case gain is statistically proven.” Explain the four-day sample and zero-inclusive interval.
- “The fly always beats simple rules” or “the lesion always hurts accuracy.” Show the comparisons.
- “Our raster is live brain activity” or “we built a flybody robot.” Explain the actual playback and scope.
