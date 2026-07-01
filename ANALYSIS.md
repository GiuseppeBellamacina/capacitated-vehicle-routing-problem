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
| **Popolazione** | 100 individui (NN + Savings + random) |
| **Selezione** | Tournament selection (k=2) |
| **Crossover** | Order Crossover (OX), tasso 0.9 |
| **Mutazione** | Swap (40%), Insert (30%), Inversion (30%), tasso 0.3 |
| **Ricerca Locale** | 2-opt, Or-opt, Relocate, Exchange (steepest descent) |
| **Elitismo** | 2 migliori preservati |
| **Criterio arresto** | 350,000 valutazioni fitness |

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
├── test_quick.py         # Test rapido
└── cvrp/
    ├── __init__.py
    ├── instance.py       # Parser formato CVRPLIB
    ├── hga.py            # Algoritmo Genetico Ibrido
    └── utils.py          # Utility (distanze, costi, feasibility)
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

- **Run**: 5 run indipendenti per istanza
- **Criterio arresto**: 350,000 valutazioni fitness
- **Metriche**: best, mean, std dev, generazioni al best, convergenza

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
| Visualizzazione | HTML5 Canvas | Rendering custom senza librerie |
| Documentazione | LaTeX | Relazione accademica |
