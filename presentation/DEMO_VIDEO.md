# 🪰 ParkFly — recorded demo video, about 5:45

Fala em inglês. Grave o app real em 1366×768 ou maior; use captura da tela, sem imagens geradas. Feche notificações, e-mail, abas de login e qualquer token. O vídeo deve mostrar o mouse e as mudanças dos controles. Não use GPS pessoal na gravação.

## 0:00–0:25 · Cold open: a decisão da mosca

Imagem: Fly brain, cena do demo 5, encoder Original, Giant Fibre intacto. Mostre DIVERT; marque a lesão e mostre COMMIT. Volte ao início do demo para a próxima tomada.

Narração:

> What changes when you cut an escape circuit out of a real fly connectome? In this parking simulation, its readout changes from divert to commit. ParkFly uses the real FlyWire brain wiring to study decisions under incomplete observations.

Texto curto na tela: REAL CONNECTOME · SIMULATED ENVIRONMENT.

## 0:25–1:15 · Sparse observations

Imagem: mapa, 0 → 25 → 100 → 25% observações. Mostre anéis e a nota de avaliação abaixo da curva.

> We simulate occupancy on official NC State parking geometry, with four hundred seventy-eight estimated spot positions. We hide most of that state and let a Bayesian model infer the rest. Observed spots have rings; inferred spots show a probability and confidence.
>
> At twenty-five percent coverage, held-out unobserved-spot accuracy is about eighty-two percent, versus seventy-three percent for a uniform baseline. Brier probability error is about point-one-two-three versus point-one-seven-nine. The dashboard separates single-snapshot performance from averages on held-out simulated days.

Texto: UNSENSED ACCURACY ≈82% VS ≈73% · SIMULATED TEST.

## 1:15–2:00 · The real model and its libraries

Imagem: abra Real fly-brain network; depois Simulator settings & libraries. Mostre o número de neurônios, conexões e execuções. Se necessário, pause brevemente a narração para o público ler.

> The numerical engine follows the NC State starter: pandas loads neuron and annotation tables, NumPy holds voltages and spikes, and SciPy stores the signed wiring as a sparse matrix. The model has one hundred thirty-eight thousand, six hundred thirty-nine neurons and fifteen million nonzero weighted connections.
>
> We measured four hundred eighty full-brain simulations across eighty sensory combinations, two brain conditions, and three seeds. Each run simulates two hundred milliseconds from rest. The browser interpolates those measured rates; recorded rasters are labeled as playback.

Texto: 80 INPUTS × 2 CONDITIONS × 3 SEEDS = 480 RUNS.

## 2:00–2:55 · Signals and causal intervention

Imagem: sentidos e três medidores; cena do demo 5. Deixe o mouse na caixa de lesão por um segundo antes de clicar. Mostre GF próximo de 146 Hz e depois 0 Hz no caso selecionado.

> Availability and a short trip become sugar. Uncertainty becomes bitter. Rising fill and near-full risk become looming. The outputs are MN9 for commit, MDN for back off, and Giant Fibre for divert.
>
> This is the original-encoder lesion scene. The simulated lot has five spots free now and zero fifteen minutes later. Cutting the Giant Fibre’s input columns prevents it from firing, and the selected verdict changes. This is a causal circuit demonstration; aggregate accuracy is evaluated separately.

Texto: GF INPUT LESION · SAME SCENE · DIFFERENT READOUT.

## 2:55–4:10 · Training algorithm and measured gain

Imagem: encoder Calibrated; mostre o gráfico de acerto, depois Original e Calibrated no seletor. Volte para Calibrated. Abra How accuracy was measured.

> The learning step calibrates four parking-to-sense parameters. The connectome itself stays fixed. We search eighty-one configurations on fourteen simulated training days, then evaluate on four different days with identical observations across policies.
>
> At twenty-five percent coverage, calibration succeeds in one hundred fifty-one of one hundred fifty-six cases, versus one hundred fifty for the original encoder. That is ninety-six-point-eight versus ninety-six-point-two percent. Mean modeled walking-plus-failure cost drops from one-point-seven-six to one-point-five-eight minutes.
>
> The gain is one case. Its ninety-five percent paired interval is zero to one-point-nine-two percentage points. Four simulated days do not establish real-world improvement. The app exposes the original encoder, nearest-lot rule, oracle, and lesion outcomes so the result stays auditable.

Texto: 151/156 VS 150/156 · +0.64 pp · 95% INTERVAL: 0 TO 1.92 pp.

## 4:10–4:55 · Broader inference evidence

Imagem: Spillover e Placement; mantenha legendas SIMULATED e REAL visíveis.

> We also test how partial observations spread through the environment. On twenty-eight real Birmingham car parks, learning on fifty-one days and testing on twenty-two later days, sensing a quarter of the lots reduces hidden-lot error by thirty-two-point-five percent. That checks across-lot inference.
>
> In the simulated placement experiment, spread clusters have about thirteen percent lower Brier error than entrance clusters at the same budget. These are separate measures of inference quality and experimental design.

Texto: BIRMINGHAM: REAL 2016 DATA · PLACEMENT: SIMULATED.

## 4:55–5:45 · Reproducibility and closing

Imagem: abra Simulator settings & libraries; mostre o link de download do notebook e o relatório de resultados. Termine com a visão do mapa e o título 🪰 ParkFly.

> The full-brain notebook uses public data without a FlyWire token. FAFBseg, Navis and Plotly support an optional skeleton view; that view needs private authentication and is not required for the decision pipeline. Flybody is a possible future embodiment, not a component we claim to have built.
>
> ParkFly connects sparse observations to a real biological circuit, measures what its decisions achieve, and shows how an intervention changes behavior. The environment is simulated, the wiring is real, and the next step is broader testing with measured occupancy. Try the lab and inspect the methods at parkfly-one dot vercel dot app.

## Edição e gravação

- Preserve os eventos importantes em tempo real: slider, troca do encoder e clique da lesão. Não acelere esses trechos de forma que esconda comportamento.
- Pode cortar tempo de rolagem ou carregamento; não monte cenas para fingir uma melhoria numérica.
- Use legendas curtas, com SIMULATED / REAL e o denominador 156.
- Se o esqueleto opcional não estiver rodando com token válido, use o grafo agregado real do app. Não afirme que a visualização 3D foi executada.
- Alvo de narração: 110–125 palavras por minuto, com pausas para ler os números. Ensaie antes de gravar a tomada final.
