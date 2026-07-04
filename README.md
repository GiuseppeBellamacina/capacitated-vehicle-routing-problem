# Risolutore CVRP (Capacitated Vehicle Routing Problem) con Algoritmo Genetico Ibrido (HGA)

Questo progetto implementa un risolutore interattivo e ad alte prestazioni per il **Capacitated Vehicle Routing Problem (CVRP)** utilizzando un **Algoritmo Genetico Ibrido (HGA)** con decodifica ottimale tramite lo **Split Algorithm di Prins**.

L'applicazione è suddivisa in un backend ad alte prestazioni (accelerato con **Numba** e servito tramite **FastAPI/WebSockets**) e una dashboard frontend interattiva (scritta in **React + TypeScript** con rendering su **HTML5 Canvas**).

---

## 📂 Struttura del Progetto

```text
capacitated-vehicle-routing-problem/
├── backend/                  # Codice sorgente del backend Python
│   ├── cvrp/                 # Moduli dell'algoritmo CVRP
│   │   ├── instance.py       # Parser delle istanze (.vrp in formato CVRPLIB)
│   │   ├── hga.py            # Implementazione dell'Algoritmo Genetico Ibrido
│   │   ├── numba_utils.py    # Operatori e Split ottimizzati JIT con Numba
│   │   └── utils.py          # Utility di calcolo costi e verifica fattibilità
│   ├── main.py               # Server FastAPI + gestione canali WebSocket
│   ├── pyproject.toml        # Dipendenze e metadati del progetto (gestito con uv)
│   ├── run_experiments.py    # Script di esecuzione del protocollo sperimentale completo
│   ├── tune_parameters.py    # Script di tuning automatico iperparametri con Optuna
│   ├── plot_convergence.py   # Script di generazione grafici (convergenza + rotte + radar + confronto)
│   ├── format_latex.py       # Script unificato di formattazione tabelle LaTeX (--table / --comparison)
│   ├── test_quick.py         # Test rapido di esecuzione dell'algoritmo
│   └── test_minimal.py       # Test unitario e di compilazione Numba
├── frontend/                 # Dashboard interattiva React
│   ├── src/
│   │   ├── App.tsx           # Componente principale e gestione WebSocket
│   │   ├── index.css         # Stili e design del tema scuro (glassmorphic)
│   │   └── main.tsx          # Entry point React
│   ├── package.json          # Dipendenze JavaScript (gestito con bun)
│   └── vite.config.ts        # Configurazione Vite con proxy API/WebSocket
├── config/                   # File di configurazione YAML
│   ├── config_small.yaml     # Config: popolazione leggera (pop=10)
│   ├── config_medium.yaml    # Config: popolazione media (pop=30)
│   ├── config_large.yaml     # Config: popolazione grande (pop=100)
│   ├── config_ultra.yaml     # Config: popolazione minima (pop=5)
│   ├── config_explore.yaml   # Config: esplorazione aggressiva (pop=100, mut=0.4)
│   ├── config_balanced.yaml  # Config: bilanciato qualità/velocità (pop=60)
│   ├── config_tuned.yaml     # Config: generato da Optuna (output del tuning)
│   └── config_optuna.yaml    # Config: metaparametri per il tuning automatico
├── cluster/                  # Script e utility per esecuzione su cluster SLURM
│   ├── run.sh                # Pipeline esperimenti (run_experiments → plot → table)
│   ├── tune.sh               # Pipeline tuning Optuna via SLURM
│   ├── setup.sh              # Installazione dipendenze (usa pyproject.toml)
│   ├── aliases.sh            # Alias e shortcut per il cluster
│   ├── sync_cluster.ps1      # Script PowerShell per sincronizzare col cluster
│   └── clean.sh              # Pulizia workspace
├── instances/                # Istanze del benchmark ufficiale CVRPLIB (.vrp)
├── results/                  # Risultati esperimenti (generati)
│   ├── config_small/         # Risultati per la variante Small
│   ├── config_large/         # Risultati per la variante Large
│   ├── ...                   # Una directory per ogni config
│   └── tuning/               # Risultati tuning Optuna (tuning_summary.json, tuning.db)
├── docs/
│   ├── cvrp.md               # Documentazione teorica dell'algoritmo HGA
│   └── report/               # Relazione di progetto in LaTeX
│       ├── report.tex        # Codice sorgente del report accademico
│       └── report.pdf        # PDF compilato del report
├── ANALYSIS.md               # Analisi architetturale del progetto
└── README.md                 # Questo file
```

---

## 🛠️ Tecnologie Utilizzate

### Backend (Python 3.11+)
- **FastAPI & Uvicorn**: Server REST API e WebSocket per la comunicazione in tempo reale.
- **Numba (JIT Compiler)**: Compilazione Just-In-Time del codice critico per prestazioni equivalenti al C/C++.
- **NumPy**: Gestione efficiente delle matrici di adiacenza e delle coordinate dei nodi.
- **Optuna**: Framework di ottimizzazione iperparametrica automatica con TPE (Tree-structured Parzen Estimator).

### Frontend (React + TypeScript)
- **Vite**: Strumento di build ultrarapido per il frontend.
- **HTML5 Canvas API**: Rendering custom delle rotte dinamiche e dei nodi senza sovraccaricare il DOM.
- **WebSockets nativi**: Ricezione in streaming dei progressi dell'algoritmo per ogni run.

---

## 🚀 Setup e Installazione

Assicurati di avere installato sul tuo sistema:
- **Python 3.11** o superiore.
- **Node.js** (consigliato versione 18+) e il gestore **Bun** (in alternativa è possibile usare `npm`).

### 1. Configurazione del Backend

Accedi alla cartella del backend ed esegui il setup dell'ambiente virtuale. Si raccomanda l'uso di `uv` per la massima velocità, ma è possibile procedere anche con `pip`:

**Utilizzando `uv` (consigliato):**
```bash
cd backend
uv sync
```

**Utilizzando `pip` tradizionale:**
```bash
cd backend
python -m venv .venv
# Attiva l'ambiente virtuale:
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Unix/macOS:
source .venv/bin/activate

pip install .
```

### 2. Configurazione del Frontend

Accedi alla cartella del frontend e installa le dipendenze:

**Utilizzando `bun` (consigliato):**
```bash
cd frontend
bun install
```

**Utilizzando `npm`:**
```bash
cd frontend
npm install
```

---

## 💻 Istruzioni per l'Esecuzione

### Esecuzione Locale dell'Applicazione Interattiva

Per avviare l'applicazione completa con dashboard interattiva in tempo reale:

1. **Avvia il server backend FastAPI**:
   ```bash
   cd backend
   # Assicurati che l'ambiente virtuale sia attivo
   .venv\Scripts\python.exe main.py
   ```
   Il server sarà attivo all'indirizzo `http://localhost:8000`.

2. **Avvia il server di sviluppo del frontend**:
   ```bash
   cd frontend
   bun run dev # o npm run dev
   ```
   La dashboard sarà accessibile da browser all'indirizzo `http://localhost:3000`.

### Diagnostica e Test Rapidi

Per verificare che l'algoritmo e le ottimizzazioni Numba funzionino correttamente sul tuo hardware:

- **Test rapido** (10K valutazioni su A-n45-k7):
  ```bash
  cd backend
  .venv\Scripts\python.exe test_quick.py
  ```
- **Test minimo** (compilazione Numba):
  ```bash
  cd backend
  .venv\Scripts\python.exe test_minimal.py
  ```

---

## ⚙️ Varianti di Configurazione (Config Presets)

Il progetto offre **7 configurazioni HGA predefinite**, ciascuna ottimizzata per un diverso profilo di esecuzione. Ogni config è un file YAML nella directory `config/`.

| Config | Pop | Tourn | Elite | Granular | Crossover | Mutation | LS Rate | LS Iter | Profilo |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Ultra** | 5 | 2 | 1 | 2 | 0.80 | 0.10 | 0.10 | 2 | Velocissimo, bassa qualità |
| **Small** | 10 | 2 | 2 | 3 | 0.80 | 0.10 | 0.10 | 2 | Rapido, qualità accettabile |
| **Medium** | 30 | 3 | 3 | 7 | 0.80 | 0.10 | 0.10 | 2 | Equilibrio velocità/qualità |
| **Balanced** | 60 | 3 | 4 | 12 | 0.85 | 0.10 | 0.10 | 2 | Bilanciato, buona qualità |
| **Large** | 100 | 4 | 5 | 15 | 0.80 | 0.10 | 0.10 | 2 | Migliore qualità, più lento |
| **Explore** | 100 | 2 | 1 | 15 | 0.95 | 0.40 | 0.25 | 3 | Esplorazione aggressiva |
| **Tuned** | — | — | — | — | — | — | — | — | Ottimizzato da Optuna ⭐ |

### Eseguire un esperimento con un config specifico

```bash
cd backend
.venv\Scripts\python.exe run_experiments.py --config ../config/config_large.yaml
```

---

## 🧪 Tuning Automatico con Optuna

Il progetto include un sistema di **ottimizzazione automatica degli iperparametri** basato su Optuna. Il tuning cerca la combinazione ottimale di parametri HGA eseguendo trial multipli su istanze rappresentative.

### Configurazione del Tuning

Il file `config/config_optuna.yaml` controlla i metaparametri del processo di tuning:

```yaml
study_name: hga_tuning      # Nome studio (per riprendere sessioni)
trials: 100                 # Numero di trial da eseguire
budget: 100000              # Valutazioni per trial (ridotto per velocità)
runs_per_trial: 2           # Run indipendenti per istanza per trial
instances: []               # Istanze su cui fare tuning (vuoto = automatico)
storage: sqlite:///results/tuning/tuning.db  # Database persistente
warm_start: true            # Primo trial usa parametri default
output_config: config/config_tuned.yaml      # Dove salvare il miglior config
output_dir: results/tuning  # Directory output riepilogo
```

### Eseguire il tuning in locale

```bash
cd backend
.venv\Scripts\python.exe tune_parameters.py --config ../config/config_optuna.yaml
```

Al termine, `results/tuning/` conterrà:
- `tuning_summary.json` — riepilogo con best params, gap, top-5 trial
- `tuning.db` — database Optuna per riprendere lo studio
- `config/config_tuned.yaml` — miglior config HGA trovato, pronto per gli esperimenti

### Eseguire esperimenti con il config ottimizzato

```bash
cd backend
.venv\Scripts\python.exe run_experiments.py --config ../config/config_tuned.yaml
```

---

## 🖥️ Esecuzione su Cluster SLURM

Il progetto include script pronti per l'esecuzione su cluster HPC con **SLURM** e **Apptainer**.

### Setup sul cluster

```bash
# 1. Sincronizza i file dal locale (PowerShell)
.\sync_cluster.ps1 -Action upload

# 2. Sul cluster, carica gli alias
source cluster/aliases.sh

# 3. Installa le dipendenze
bash cluster/setup.sh
```

### Comandi rapidi (alias)

| Comando | Descrizione |
| :--- | :--- |
| `run-exp` | Lancia tutti gli esperimenti via SLURM |
| `run-exp config_large` | Lancia solo il config specificato |
| `tune` | Lancia il tuning Optuna via SLURM |
| `tune config_optuna_v2` | Lancia tuning con config specifico |
| `myjobs` | Lista job attivi |
| `lastlog` | Segui l'ultimo log |
| `runlog <ID>` | Segui il log di un job specifico |
| `killjob <ID>` | Cancella un job |
| `killalljobs` | Cancella tutti i job |

### Pipeline automatica

`run-exp` esegue in sequenza per ogni config:
1. **Esperimenti** (`run_experiments.py`) — tutte le 10 istanze, 5 run × 350K FE
2. **Grafici** (`plot_convergence.py`) — convergenza, rotte, radar, confronto
3. **Tabella LaTeX** (`format_latex.py`) — tabella formattata per il report

`tune` esegue:
1. **Tuning Optuna** (`tune_parameters.py`) — ricerca iperparametri
2. Salva il miglior config in `config/config_tuned.yaml`
3. Salva il riepilogo in `results/tuning/tuning_summary.json`

---

## 📊 Protocollo Sperimentale e Risultati (Benchmark CVRPLIB)

Il protocollo sperimentale prevede l'esecuzione dell'algoritmo su **10 istanze del benchmark CVRPLIB** (distribuite in 4 set differenti: A, B, E, P), per **5 run indipendenti** ciascuna, con un criterio di arresto rigoroso fissato a **350.000 valutazioni della funzione fitness (FE)**.

### Risultati Finali Ottenuti (R = 5, FE = 350.000)

Grazie alle ottimizzazioni apportate a livello algoritmico, l'HGA ha ottenuto risultati eccellenti, avvicinandosi sensibilmente all'ottimo globale (BKS) con gap percentuali estremamente ridotti:

| Istanza | HGA Best Cost | Mean Cost | Std Dev | Ottimo (BKS) | Gap% | Veicoli |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A-n45-k7** | 1146.91 | 1155.02 | 12.81 | 1146 | **0.08%** | 7 |
| **A-n60-k9** | 1367.34 | 1376.86 | 7.87 | 1354 | **0.99%** | 9 |
| **A-n80-k10** | 1817.37 | 1848.71 | 26.61 | 1763 | 3.08% | 10 |
| **B-n56-k7** | 712.92 | 716.05 | 1.69 | 707 | **0.84%** | 7 |
| **B-n66-k9** | 1327.10 | 1330.89 | 3.30 | 1316 | **0.84%** | 9 |
| **B-n78-k10** | 1238.33 | 1254.00 | 8.16 | 1221 | 1.42% | 10 |
| **E-n76-k8** | 750.44 | 760.29 | 6.74 | 735 | 2.10% | 8 |
| **E-n101-k14** | 1097.02 | 1105.04 | 8.10 | 1071 | 2.43% | 14 |
| **P-n50-k10** | 700.66 | 705.54 | 3.40 | 696 | **0.67%** | 10 |
| **P-n101-k4** | 693.54 | 694.70 | 1.07 | 681 | 1.84% | 4 |

### Esecuzione del Benchmark
Per rieseguire l'intero protocollo sperimentale:
```bash
cd backend
.venv\Scripts\python.exe run_experiments.py --config ../config/config_large.yaml
```
I risultati vengono salvati in `results/<config_name>/results.json`.

### Generazione dei Grafici ad Alta Risoluzione

Lo script `plot_convergence.py` genera automaticamente un set di **9+ grafici di livello accademico** (salvati nella directory `docs/report/imgs/` a 300 DPI):

1. **Grafici di Convergenza** (`imgs/convergence/`): Visualizzazione delle 5 run individuali, della deviazione standard ($\pm 1\sigma$), del comportamento medio e della run migliore per ciascuna istanza rappresentativa.
2. **Grafici delle Rotte Migliori** (`imgs/routes/`): Tracciato geometrico 2D delle rotte reali effettuate dai veicoli, con differenziazione cromatica colorblind-friendly, marker proporzionali alle domande dei clienti e indicazione numerica dell'ordine delle tappe.
3. **Grafici di Riepilogo** (`imgs/summary/`):
   - `summary_best_vs_bks.png`: Istogramma di confronto diretto tra il costo migliore HGA e il valore ottimale BKS.
   - `summary_gap.png`: Grafico delle deviazioni percentuali (gap) rispetto all'ottimo per tutte le istanze.
   - `summary_boxplot.png`: Distribuzione dei costi normalizzata in percentuale rispetto alla BKS per analizzare la stabilità statistica dell'algoritmo.
   - `summary_runtime.png`: Grafico a dispersione del tempo computazionale richiesto in funzione del numero di nodi.
   - `summary_radar.png`: Diagramma radar multi-variabile che confronta le prestazioni normalizzate (Route length, Stability, Gap, Time/node, Convergence) per ciascun set (A, B, E, P) e per ciascuna variante di configurazione.
   - `summary_config_comparison.png`: Confronto tra tutte le varianti di configurazione su metriche aggregate.
   - `summary_generations.png`: Numero medio di generazioni evolutive necessarie per convergere alla soluzione ottimale.
   - `summary_route_length.png`: Lunghezza media delle rotte in termini di clienti serviti per veicolo.

Per generare/aggiornare l'intero set di grafici:
```bash
cd backend
.venv\Scripts\python.exe plot_convergence.py --results ../results/config_large/results.json --imgs ../docs/report/imgs/config_large
```

---

## 🧬 Ottimizzazioni dell'Algoritmo (HGA)

Per raggiungere velocità di esecuzione elevatissime (**fino a oltre 6.900 valutazioni al secondo per core**), l'architettura HGA è stata potenziata con i seguenti interventi:

1. **Pre-calcolo dei Carichi in $O(1)$**: Sostituito il ricalcolo continuo dei carichi delle rotte ($O(N)$) nelle scansioni della ricerca locale inter-route (`_relocate` e `_exchange`) con vettori pre-calcolati aggiornati in tempo costante.
2. **Index-Only Move Tracking**: Eliminata l'operazione di deep-copy nel loop interno della ricerca locale. I vicinati valutano i delta teorici in $O(1)$, e la mossa fisica viene applicata in-place una sola volta alla fine del ciclo solo in caso di miglioramento.
3. **Double-Tier Education (Light/Full)**:
   - *Educazione leggera*: Il 2-opt JIT-compilato con Numba viene applicato a **tutti** i figli generati ad ogni iterazione, garantendo la rimozione immediata degli incroci stradali.
   - *Local Search completa*: Gli operatori inter-route completi sono eseguiti solo al tasso stocastico configurato ($p_{ls} = 0.1$).
4. **Duplicate Detection (Survivor Selection)**: I cloni con costo identico (arrotondato al terzo decimale) vengono rilevati e rimpiazzati con individui casuali pre-educati ad ogni generazione per massimizzare la diversità ed evitare la convergenza precoce.
5. **Micro-ottimizzazioni dei Generatori**: Sostituito `random.sample(range(n), 2)` e ordinamenti Python con offset matematici diretti per l'estrazione rapida di punti di taglio del crossover OX e indici di mutazione. Bypass diretto a torneo per $k=2$.
