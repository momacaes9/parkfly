# 🪰 ParkFly — live demo, 6 minutes

Fala em inglês; comandos de palco em português. O roteiro acompanha os seis passos do botão Demo. Treine com cronômetro. Se os 5–7 minutos incluírem perguntas, use o corte de 5 minutos e reserve 1–2 minutos para Q&A. O contexto inicial do evento indicava 3–5 minutos: há também um corte de 4 minutos no final.

## Antes de subir ao palco

- Abra https://parkfly-one.vercel.app em uma aba já carregada; zoom do navegador 100%.
- Clique Demo. Use → para avançar; ← volta; Escape sai. Não digite durante a apresentação.
- O demo limpa GPS, volta para Hunt Library e fixa o sorteio dos sensores. Não abra permissões de localização durante a fala.
- Mostre o app primeiro. Deixe a apresentação de apoio para Q&A.
- Tenha o servidor local aberto como reserva: `python3 -m http.server 8765 -d web`.

## 0:00–0:30 · 1. O experimento

Ação: comece com o mapa e 0% de observações; não comece com slides.

> What should an agent do when it can only observe part of its world: commit, back off, or divert? ParkFly explores that question using the real wiring of a fruit fly’s brain. We built a parking simulation at NC State, hide most of the occupancy, and translate the uncertainty into sensory inputs for the fly. The environment is simulated; the connectome is real.

## 0:30–1:30 · 2. Observações esparsas → mapa estimado

Ação: → para 25%; arraste 0 → 25 → 100 → 25. Aponte os anéis e a nota abaixo da curva, não leia a métrica de um instante como resultado médio.

> Each dot is one estimated parking position. Rings mark observed spots. The other colors are inferred occupancy probabilities. We fit a Bayesian fill-frontier model: spots tend to fill in an attractiveness order, and a few observations help locate that frontier.
>
> At twenty-five percent observation coverage, held-out accuracy on the unobserved spots is about eighty-two percent, versus seventy-three percent for a uniform baseline. Brier probability error is about point-one-two-three versus point-one-seven-nine, roughly thirty-one percent lower. These are simulated test results. The large live numbers describe this selected moment; the chart summarizes many held-out moments. At one hundred percent, no unobserved targets remain, so those metrics become not applicable.

## 1:30–2:10 · 3. Outra fonte de evidência

Ação: → para Spillover. O demo observa um lote inteiro automaticamente.

> Nearby lots share demand, so observing one lot also changes the uncertainty about others. We checked this inference component on real Birmingham observations. After coverage filtering, twenty-eight car parks remain. We learn on the first fifty-one days and test on the next twenty-two. At twenty-five percent of lots sensed, hidden-lot error falls from about seven to four-point-seven occupancy percentage points: a thirty-two-point-five percent reduction. That validates the across-lot inference component.

## 2:10–2:40 · 4. Desenho do experimento

Ação: → para Placement; clique Entrance e depois Spread, mantendo 25%.

> The observation pattern matters too. We compare clusters with the same observation budget. Spread placement has Brier error point-one-two-seven, versus point-one-four-five at the entrance: about thirteen percent lower. The fill-frontier strategy leads the clustered strategies. Scattered individual spots remain an idealized reference.

## 2:40–4:25 · 5. A rede decide e a lesão muda o circuito

Ação: → para Fly brain. O encoder fica Original para a cena causal. Aponte a linha REAL v783 e os três medidores. Marque Lesion Giant Fibre, espere o medidor zerar, desmarque se quiser repetir. Só abra o grafo/raster se houver tempo.

> Here is the biological part. The measured model has one hundred thirty-eight thousand, six hundred thirty-nine neurons and about fifteen million signed, weighted connections. We use the starter’s NumPy, SciPy sparse matrices, and pandas tables to simulate it with the Shiu settings.
>
> Sugar encodes availability and a short trip. Bitter encodes uncertainty and other costs. Looming encodes rising fill and near-full risk. We read MN9 for commit, MDN for back off, and the Giant Fibre for divert.
>
> We precomputed four hundred eighty full-brain runs: eighty input combinations, intact and lesioned brains, and three fixed seeds. Each run starts from rest and simulates two hundred milliseconds. The browser interpolates that measured response surface for interaction.
>
> This selected simulated lot has five free spots now and zero fifteen minutes later. Intact, the Giant Fibre drives a divert verdict. I now cut its incoming synapses. Its activity goes to zero and this readout changes to commit. This scene demonstrates a circuit intervention; the full test curve measures overall decision quality separately.

## 4:25–6:00 · 6. Treino, resultado e conclusão

Ação: → para o encoder Calibrated. Aponte 96.8%, custo de 1.58 min e How accuracy was measured. Fale devagar na limitação.

> We then train the parking-to-sense encoder while keeping the biological wiring fixed. Fourteen simulated training days select four encoding parameters from eighty-one configurations. The objective prioritizes finding a free spot, then breaks ties using modeled walking and failure cost. Four different days are held out for evaluation, and every policy receives the same observations.
>
> At twenty-five percent coverage, the calibrated encoder succeeds in one hundred fifty-one of one hundred fifty-six cases: ninety-six-point-eight percent. The original succeeds in one hundred fifty cases: ninety-six-point-two percent. Mean modeled cost falls from one-point-seven-six to one-point-five-eight minutes.
>
> That is one extra successful case. The ninety-five percent interval for the paired gain runs from zero to one-point-nine-two percentage points. It is a small simulation result, and the interval includes zero. We show the nearest-lot baseline, the oracle, and the lesion results too.
>
> ParkFly turns the starter connectome into a reproducible decision experiment: sparse observations, interpretable sensory encoding, real neural responses, and an observable intervention. The next step is broader simulation testing and validation with measured spot occupancy. Thank you.

## Corte de 5 minutos

Mantenha os seis passos. Reduza Spillover a uma frase com 32.5%; Placement a uma frase com 13%; não abra grafo/raster. Preserve a explicação do circuito, a lesão, 151/156 versus 150/156 e a limitação do intervalo. Reserve os dois minutos restantes de uma janela de sete minutos para perguntas.

## Corte de 4 minutos para limite oficial curto

- 0:00–0:20: primeira fala, reduzida a pergunta + cérebro real/ambiente simulado.
- 0:20–1:00: anéis e cores; 82% vs 73%; 0.123 vs 0.179.
- 1:00–1:20: Birmingham 32.5%; avance Placement rapidamente.
- 1:20–2:45: três sentidos, três saídas, 480 execuções e lesão.
- 2:45–4:00: treino 14 dias/teste 4 dias; 151/156 vs 150/156; custo e limitação; conclusão.

## Frase de emergência se o mapa de fundo falhar

> The basemap is unavailable, but the local official polygons, simulated spots, and brain-response data remain loaded. We can continue the experiment offline.

## Frase de emergência se pedirem para encerrar

> Our main result is a reproducible bridge from sparse observations to a real connectome’s decisions, with measured baselines and a circuit lesion. The calibration gain is small and simulated, and we show that uncertainty explicitly.
