# CVRP Solver - Analisi del Progetto

## Panoramica

Questo progetto implementa un risolutore per il **Capacitated Vehicle Routing Problem (CVRP)** utilizzando un **Algoritmo Genetico Ibrido (HGA)**. L'architettura è composta da:

- **Backend Python** (FastAPI + uvicorn): logica dell'algoritmo e API REST/WebSocket
- **Frontend React** (TypeScript + Vite): visualizzazione interattiva in tempo reale
- **Relazione LaTeX**: documentazione completa del progetto

## Algoritmo: Hybrid Genetic Algorithm (HGA)

### Perché HGA?

Scelto tra le opzioni disponibili (escluso Tabu Search) perché:

1. **Migliore esplorazione globale**: il GA esplora lo spazio delle soluzioni tramite crossover e mutazione
2. **Raffinamento locale**: la ricerca locale ibrida (2-opt, Or-opt, Relocate, Exchange) migliora le soluzioni
3. **Split Algorithm di Prins**: decodifica ottimale da permutazione a route, rispettando i vincoli di capacità
4. **Risultati competitivi**: letteratura accademica conferma l'efficacia dell'HGA su CVRP

### Componenti chiave

| Componente | Dettaglio |
|---|---|
| **Encoding** | Permutazione di clienti (escluso depot) |
| **Decodifica** | Split Algorithm O(n²) - DP ottimale |
| **Popolazione** | 100 individui (NN + Savings + random) — parametro configurabile via config YAML |
| **Selezione** | Tournament selection (k=3, configurabile) |
| **Crossover** | Order Crossover (OX), tasso configurabile (default 0.8) |
| **Mutazione** | Swap (40%), Insert (30%), Inversion (30%), tasso configurabile (default 0.1) |
| **Ricerca Locale** | 2-opt, Or-opt, Relocate, Exchange (steepest descent) |
| **Elitismo** | Configurabile (default 5) |
| **Criterio arresto** | 350,000 valutazioni fitness (configurabile) |
| **Varianti config** | 7 preset: Ultra, Small, Medium, Balanced, Large, Explore, Tuned |

### Operatori di Ricerca Locale

Tutti implementati con strategia **steepest descent** (best improvement):

- **2-opt** (intra-route): inverte segmenti di route per eliminare incroci
- **Or-opt** (intra-route): sposta segmenti di 1-3 nodi in posizioni migliori
- **Relocate** (inter-route): sposta clienti tra route diverse
- **Exchange** (inter-route): scambia coppie di clienti tra route

## Architettura Software

### Backend (`backend/`)

```
backend/
├── main.py              # FastAPI + WebSocket server
├── pyproject.toml        # Dipendenze (uv)
├── run_experiments.py    # Esecuzione protocollo sperimentale
├── tune_parameters.py    # Tuning automatico iperparametri (Optuna)
├── plot_convergence.py   # Generazione grafici (convergenza, rotte, radar, confronto)
├── format_latex.py       # Formattazione tabelle LaTeX
├── test_quick.py         # Test rapido
├── test_minimal.py       # Test unitario Numba
└── cvrp/
    ├── __init__.py
    ├── instance.py       # Parser formato CVRPLIB
    ├── hga.py            # Algoritmo Genetico Ibrido
    ├── numba_utils.py    # Operatori JIT Numba (Split, 2-opt, Or-opt)
    └── utils.py          # Utility (distanze, costi, feasibility)
```

### Configurazioni (`config/`)

```
config/
├── config_small.yaml     # Popolazione leggera (pop=10)
├── config_medium.yaml    # Popolazione media (pop=30)
├── config_large.yaml     # Popolazione grande (pop=100) — default
├── config_ultra.yaml     # Popolazione minima (pop=5)
├── config_explore.yaml   # Esplorazione aggressiva (mut=0.4)
├── config_balanced.yaml  # Bilanciato qualità/velocità (pop=60)
├── config_tuned.yaml     # Output Optuna (generato automaticamente)
└── config_optuna.yaml    # Metaparametri per il tuning
```

### Cluster (`cluster/`)

```
cluster/
├── run.sh                # Pipeline esperimenti SLURM
├── tune.sh               # Pipeline tuning Optuna SLURM
├── setup.sh              # Installazione dipendenze (pyproject.toml)
├── aliases.sh            # Alias e shortcut per il cluster
├── sync_cluster.ps1      # Sincronizzazione file con il cluster
└── clean.sh              # Pulizia workspace
```

#### Comunicazione WebSocket in tempo reale

- **Protocollo**: JSON su WebSocket (`ws://localhost:8000/ws`)
- **Threading**: algoritmo eseguito in thread separato (`asyncio.to_thread`)
- **Callback**: `loop.call_soon_threadsafe` → `asyncio.Queue` → drain task → WebSocket
- **Messaggi**: `run_start`, `progress`, `run_complete`, `experiment_complete`
- **Downsampling**: convergenza ridotta a ~200 punti/run per trasferimento efficiente

#### API REST

- `GET /api/instances` - lista istanze disponibili
- `GET /api/instance/{name}` - dettagli istanza (coordinate, domande, capacità)
- `GET /api/health` - health check

### Frontend (`frontend/`)

```
frontend/
├── index.html
├── package.json          # Bun package manager
├── vite.config.ts        # Proxy WebSocket/API verso backend
├── tsconfig.json
└── src/
    ├── main.tsx
    ├── App.tsx           # Componente principale + WebSocket + visualizzazione
    └── index.css         # Styling dark theme
```

#### Visualizzazioni

- **Route Canvas**: mappa 2D interattiva con rotte colorate, depot evidenziato, nodi proporzionali alla domanda
- **Convergence Chart**: grafico convergenza multi-run con legenda
- **Stats Panel**: best, mean, std dev, optimal, gap %, execution time
- **Status Bar**: progresso in tempo reale con barra percentuale
- **Log Area**: log degli eventi in stile terminale

## Istanze

10 istanze dal benchmark CVRPLIB, suddivise in 4 set:

| Set | Istanze | Caratteristiche |
|---|---|---|
| **A** | A-n45-k7, A-n60-k9, A-n80-k10 | Clienti distribuiti uniformemente |
| **B** | B-n56-k7, B-n66-k9, B-n78-k10 | Clienti clusterizzati |
| **E** | E-n76-k8, E-n101-k14 | Distribuzione mista |
| **P** | P-n50-k10, P-n101-k4 | Posizionamento specifico |

## Setup e Avvio

### Backend

```bash
cd backend
uv venv
uv pip install fastapi uvicorn numpy matplotlib
.venv/Scripts/python.exe main.py
# Server avviato su http://localhost:8000
```

### Frontend

```bash
cd frontend
bun install
bun run dev
# Frontend su http://localhost:3000 (proxy WebSocket a :8000)
```

### Test rapido

```bash
cd backend
.venv/Scripts/python.exe test_quick.py
```

## Protocollo Sperimentale

- **Run**: 5 run indipendenti per istanza (configurabile)
- **Criterio arresto**: 350,000 valutazioni fitness (configurabile)
- **Metriche**: best, mean, std dev, generazioni al best, convergenza
- **Config multipli**: 7 varianti HGA testabili parallelamente

### Varianti di Configurazione

| Config | Pop | Tourn | Elite | Gran | Crossover | Mutation | LS Rate | Profilo |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Ultra | 5 | 2 | 1 | 2 | 0.80 | 0.10 | 0.10 | Velocissimo |
| Small | 10 | 2 | 2 | 3 | 0.80 | 0.10 | 0.10 | Rapido |
| Medium | 30 | 3 | 3 | 7 | 0.80 | 0.10 | 0.10 | Equilibrato |
| Balanced | 60 | 3 | 4 | 12 | 0.85 | 0.10 | 0.10 | Bilanciato |
| Large | 100 | 4 | 5 | 15 | 0.80 | 0.10 | 0.10 | Migliore qualità |
| Explore | 100 | 2 | 1 | 15 | 0.95 | 0.40 | 0.25 | Esplorazione |
| Tuned | — | — | — | — | — | — | — | Ottimizzato da Optuna |

## Tuning Automatico (Optuna)

Il progetto include un sistema di ottimizzazione automatica degli iperparametri basato su **Optuna** con campionatore **TPE (Tree-structured Parzen Estimator)** multivariato.

- **Warm-start**: il primo trial usa i parametri default come baseline
- **Budget per trial**: 100.000 valutazioni (ridotte per velocità)
- **Istanze di tuning**: 4 rappresentative (una per set)
- **Metrica**: gap percentuale medio rispetto ai BKS
- **Output**: `config/config_tuned.yaml` (best config), `results/tuning/tuning_summary.json` (riepilogo), `results/tuning/tuning.db` (studio persistente)
- **Config tuning**: `config/config_optuna.yaml` controlla trials, budget, storage, warm-start

## Esecuzione su Cluster SLURM

Script pronti per cluster HPC con SLURM + Apptainer:
- `cluster/run.sh` — pipeline completa (esperimenti → grafici → tabella)
- `cluster/tune.sh` — pipeline tuning Optuna
- `cluster/aliases.sh` — shortcut (`run-exp`, `tune`, `myjobs`, `lastlog`, ...)
- `cluster/setup.sh` — installazione dipendenze da `pyproject.toml`
- `sync_cluster.ps1` — sincronizzazione file da Windows

Comandi rapidi:
```bash
source cluster/aliases.sh
run-exp              # tutti i config
run-exp config_large # singolo config
tune                 # tuning Optuna
myjobs               # job attivi
lastlog              # ultimo log
```

## Risultati preliminari (solo 10K eval)

Con solo 10,000 valutazioni (test rapido):

| Istanza | Ottimo | Trovato | Gap |
|---|---|---|---|
| A-n45-k7 | 1,146 | 1,153 | 0.61% |
| P-n50-k10 | 696 | 709 | 1.87% |

Con 350,000 valutazioni (35x più iterazioni) i risultati saranno significativamente migliori.

## Tecnologie

| Layer | Tecnologia | Note |
|---|---|---|
| Linguaggio | Python 3.11+ | Type hints completi |
| Backend framework | FastAPI + uvicorn | Async, WebSocket nativo |
| Frontend | React 18 + TypeScript | Vite, Canvas API |
| Package manager | uv (Python), bun (JS) | Veloci e moderni |
| Algoritmo | HGA | Ibrido GA + Local Search |
| Tuning | Optuna (TPE) | Ottimizzazione automatica iperparametri |
| Visualizzazione | HTML5 Canvas | Rendering custom senza librerie |
| Documentazione | LaTeX | Relazione accademica |
| Cluster | SLURM + Apptainer | Script pronti per HPC |
