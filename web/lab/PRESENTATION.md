# ParkFly — presentation support, 5 backup slides

Use o app primeiro. Estas são notas e conteúdo textual para você montar apoio, sem imagens geradas. Mostre somente se o formato do evento permitir; os gráficos devem vir das exportações reais do projeto.

## Slide 1 — Sparse observations, biological decisions

Texto na tela:

**🪰 ParkFly**
Sparse observations → estimated state → real fly-circuit response.
NC State parking is the simulation environment.

Fala: “Our question is how a biological action circuit behaves when its view of the world is incomplete.”

Imagem permitida: captura real do app, results/production-screenshot.png. Mantenha SIMULATED OCCUPANCY legível.

## Slide 2 — The real connectome and the computation

Texto:

- 138,639 neurons; 15,091,983 nonzero signed weighted connections.
- NumPy state arrays; SciPy sparse wiring; pandas annotations; PyArrow parquet.
- Sugar / bitter / looming → MN9 / MDN / Giant Fibre.
- 480 full-brain runs, 200 ms each; browser interpolation.

Fala: “The wiring comes from the real v783 data. We keep its signs, groups and starter settings, then measure its response.”

Imagem: grafo agregado real do app ou raster com a legenda recorded. Não use uma imagem genérica como se fosse a conectividade medida.

## Slide 3 — What training means here

Texto:

- Biological wiring fixed.
- Four encoder parameters, 81 configurations.
- 14 simulated training days; 4 different test days.
- Same observations for every evaluated policy.

Fala: “Training calibrates the translation into senses. We prioritize finding a free spot, then break ties by walking-plus-failure cost.”

Diagrama textual: observations → posterior → calibrated senses → fixed connectome → action readout.

## Slide 4 — Results and their scale

| At 25% coverage | Calibrated | Original | Nearest |
|---|---:|---:|---:|
| Successful cases | 151/156 | 150/156 | 150/156 |
| Success | 96.79% | 96.15% | 96.15% |
| Modeled cost | 1.583 min | 1.763 min | 1.599 min |

Rodapé obrigatório: +0.64 percentage points; paired 95% interval 0–1.92 pp; four simulated test days.

Fala: “That is one extra case. We show its uncertainty instead of treating it as established real-world superiority.”

Imagem: gráfico Fly decision accuracy do app. Preserve a legenda e o texto de incerteza.

## Slide 5 — The intervention and the next experiment

Texto:

- GF input lesion changes a reproducible selected scene: DIVERT → COMMIT.
- The global intact/lesioned success rates tie at 25% in this test.
- Occupancy is simulated; external validity remains open.
- Next: broader simulated days and measured occupancy.

Fala: “The useful scientific artifact is a reproducible experiment: interpretable inputs, real wiring, baselines, and a visible circuit intervention.”

Referências curtas: Shiu et al. 2024; FlyWire v783; NC State starter; NCSU GIS. Bibliotecas opcionais para esqueleto: FAFBseg/Navis/Plotly. Flybody fica como trabalho futuro.

## Ordem para sete minutos totais

- Até 5:00: versão curta do demo ao vivo.
- 5:00–7:00: duas ou três perguntas; use os slides somente como apoio.
- Tenha os números 151/156, 150/156 e intervalo 0–1.92 pp visíveis na sua cola.
