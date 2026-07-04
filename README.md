# CVRP Solver (Capacitated Vehicle Routing Problem) with Hybrid Genetic Algorithm (HGA)

This project implements a high-performance interactive solver for the **Capacitated Vehicle Routing Problem (CVRP)** using a **Hybrid Genetic Algorithm (HGA)** with optimal decoding via **Prins' Split Algorithm**.

The application is split into a high-performance backend (accelerated with **Numba** and served via **FastAPI/WebSockets**) and an interactive frontend dashboard (written in **React + TypeScript** with **HTML5 Canvas** rendering).

---

## 📂 Project Structure

```text
capacitated-vehicle-routing-problem/
├── backend/                  # Python backend source code
│   ├── cvrp/                 # CVRP algorithm modules
│   │   ├── __init__.py       # Package init
│   │   ├── instance.py       # Instance parser (.vrp in CVRPLIB format)
│   │   ├── hga.py            # Hybrid Genetic Algorithm implementation
│   │   ├── numba_utils.py    # JIT-optimized operators and Split with Numba
│   │   └── utils.py          # Cost computation and feasibility utilities
│   ├── main.py               # FastAPI server + WebSocket channel management
│   ├── pyproject.toml        # Project dependencies and metadata (managed with uv)
│   ├── uv.lock               # Locked dependency versions
│   ├── run_experiments.py    # Full experimental protocol execution script
│   ├── tune_parameters.py    # Automatic hyperparameter tuning script with Optuna
│   ├── plot_convergence.py   # Plot generation script (convergence + routes + radar + comparison)
│   ├── format_latex.py       # LaTeX table formatting (single-config + cross-config comparison)
│   ├── test_quick.py         # Quick algorithm execution test
│   └── test_minimal.py       # Unit test and Numba compilation test
├── frontend/                 # Interactive React dashboard
│   ├── src/
│   │   ├── App.tsx           # Main component and WebSocket handling
│   │   ├── index.css         # Dark theme styles (glassmorphic design)
│   │   └── main.tsx          # React entry point
│   ├── package.json          # JavaScript dependencies (managed with bun)
│   └── vite.config.ts        # Vite configuration with API/WebSocket proxy
├── config/                   # YAML configuration files
│   ├── config_small.yaml     # Config: lightweight population (pop=10)
│   ├── config_medium.yaml    # Config: medium population (pop=30)
│   ├── config_large.yaml     # Config: large population (pop=100)
│   ├── config_fast.yaml     # Config: minimal population (pop=5)
│   ├── config_explore.yaml   # Config: aggressive exploration (pop=100, mut=0.4)
│   ├── config_balanced.yaml  # Config: balanced quality/speed (pop=60)
│   ├── config_tuned.yaml     # Config: Optuna-generated (tuning output)
│   └── config_optuna.yaml    # Config: metaparameters for automatic tuning
├── cluster/                  # Scripts and utilities for SLURM cluster execution
│   ├── run.sh                # Experiments pipeline (run_experiments → plot → table)
│   ├── tune.sh               # Optuna tuning pipeline via SLURM
│   ├── setup.sh              # Dependency installation (uses pyproject.toml)
│   ├── aliases.sh            # Cluster aliases and shortcuts
│   ├── sync_cluster.ps1      # PowerShell script to sync with the cluster
│   └── clean.sh              # Workspace cleanup
├── instances/                # Official CVRPLIB benchmark instances (.vrp)
├── results/                  # Experiment results (generated)
│   ├── config_small/         # Results for the Small variant
│   ├── config_large/         # Results for the Large variant
│   ├── ...                   # One directory per config
│   └── tuning/               # Optuna tuning results (tuning_summary.json, tuning.db)
├── docs/
│   ├── cvrp.md               # Theoretical documentation of the HGA algorithm
│   └── report/               # Project report in LaTeX
│       ├── report.tex        # Academic report source code
│       └── report.pdf        # Compiled report PDF
└── README.md                 # This file
```

---

## 🛠️ Technologies Used

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.11+ | Full type hints |
| Backend framework | FastAPI + uvicorn | Async, native WebSocket |
| Frontend | React 18 + TypeScript | Vite, Canvas API |
| Package manager | uv (Python), bun (JS) | Fast and modern |
| JIT Compiler | Numba | C/C++ performance from Python |
| Tuning | Optuna (TPE) | Automatic hyperparameter optimization |
| Visualization | HTML5 Canvas | Custom rendering without external libraries |
| Documentation | LaTeX | Academic report |
| Cluster | SLURM + Apptainer | HPC-ready scripts |

---

## 🧬 Why HGA?

The Hybrid Genetic Algorithm was chosen among the available options (Ant Colony Optimization, Immune Algorithm) because:

1. **Better global exploration**: the GA explores the solution space through crossover and mutation, reducing the risk of premature convergence to local minima.
2. **Local refinement**: hybrid local search (2-opt, Or-opt, Relocate, Exchange) improves the solutions produced by the evolutionary process.
3. **Prins' Split Algorithm**: optimal decoding from permutation to routes, respecting capacity constraints without encoding them explicitly in the chromosome.
4. **Competitive results**: HGA is recognized in the literature as one of the most effective approaches for CVRP, producing state-of-the-art results on benchmark instances.

> 📖 See [docs/cvrp.md §2](docs/cvrp.md#2-lalgoritmo-genetico-ibrido-hga-o-memetico) for a deeper theoretical treatment of the Hybrid Genetic Algorithm.

### Key HGA Components

| Component | Detail |
|---|---|
| **Encoding** | Customer permutation (excluding depot) |
| **Decoding** | Split Algorithm O(n²) — optimal DP |
| **Population** | 81 individuals (NN + Savings + random) — configurable parameter |
| **Selection** | Tournament selection (k=4) |
| **Crossover** | Order Crossover (OX), $p_c = 0.675$ |
| **Mutation** | Swap (40%), Insert (30%), Inversion (30%), $p_m = 0.236$ |
| **Local Search** | 2-opt, Or-opt, Relocate, Exchange with GLS ($\gamma=25$), steepest descent |
| **Elitism** | $e = 4$ best individuals preserved per generation |
| **Stopping criterion** | 350,000 fitness evaluations |
| **Config variants** | 7 presets: Fast, Small, Medium, Balanced, Large, Explore, Tuned |

### Local Search Operators

All four operators (2-opt, Or-opt, Relocate, Exchange) are implemented with **steepest descent** (best improvement) strategy and integrated with Granular Local Search (GLS).

> 📖 See [docs/cvrp.md §6](docs/cvrp.md#6-ricerca-locale-local-search) for detailed operator descriptions and optimization strategies.

---

## 🚀 Setup and Installation

Make sure you have installed on your system:
- **Python 3.11** or later.
- **Node.js** (version 18+ recommended) and the **Bun** package manager (alternatively, `npm` can be used).

### 1. Backend Setup

Navigate to the backend directory and set up the virtual environment. Using `uv` is recommended for maximum speed, but you can also proceed with `pip`:

**Using `uv` (recommended):**
```bash
cd backend
uv sync
```

**Using traditional `pip`:**
```bash
cd backend
python -m venv .venv
# Activate the virtual environment:
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Unix/macOS:
source .venv/bin/activate

pip install .
```

### 2. Frontend Setup

Navigate to the frontend directory and install dependencies:

**Using `bun` (recommended):**
```bash
cd frontend
bun install
```

**Using `npm`:**
```bash
cd frontend
npm install
```

---

## 💻 Execution Instructions

### Running the Interactive Application Locally

To start the full application with real-time interactive dashboard:

1. **Start the FastAPI backend server**:
   ```bash
   cd backend
   # Make sure the virtual environment is active
   .venv\Scripts\python.exe main.py
   ```
   The server will be available at `http://localhost:8000`.

2. **Start the frontend development server**:
   ```bash
   cd frontend
   bun run dev # or npm run dev
   ```
   The dashboard will be accessible in your browser at `http://localhost:3000`.

### REST API

The backend exposes the following endpoints:

- `GET /api/instances` — list of available `.vrp` instances
- `GET /api/instance/{name}` — details of an instance (coordinates, demands, capacity)
- `GET /api/health` — server health check

### Real-Time WebSocket Communication

- **Protocol**: JSON over WebSocket (`ws://localhost:8000/ws`)
- **Threading**: algorithm runs in a separate thread (`asyncio.to_thread`)
- **Callback**: `loop.call_soon_threadsafe` → `asyncio.Queue` → drain task → WebSocket
- **Messages**: `run_start`, `progress`, `run_complete`, `experiment_complete`
- **Downsampling**: convergence reduced to ~200 points/run for efficient transfer

### Frontend Dashboard

The frontend offers five real-time visualization panels:

- **Route Canvas**: interactive 2D map with colored routes, highlighted depot, demand-proportional nodes
- **Convergence Chart**: multi-run convergence chart with legend
- **Stats Panel**: best, mean, std dev, optimal, gap %, execution time
- **Status Bar**: real-time progress with percentage bar
- **Log Area**: terminal-style event log

### Quick Diagnostics and Tests

To verify that the algorithm and Numba optimizations work correctly on your hardware:

- **Quick test** (10K evaluations on A-n45-k7):
  ```bash
  cd backend
  .venv\Scripts\python.exe test_quick.py
  ```
- **Minimal test** (Numba compilation):
  ```bash
  cd backend
  .venv\Scripts\python.exe test_minimal.py
  ```

---

## ⚙️ Configuration Variants (Config Presets)

The project offers **7 predefined HGA configurations**, each optimized for a different execution profile. Each config is a YAML file in the `config/` directory.

| Config | Pop | Tourn | Elite | Granular | Crossover | Mutation | LS Rate | LS Iter | Profile |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Fast** | 5 | 2 | 1 | 2 | 0.80 | 0.10 | 0.10 | 2 | Fastest, low quality |
| **Small** | 10 | 2 | 2 | 3 | 0.80 | 0.10 | 0.10 | 2 | Fast, acceptable quality |
| **Medium** | 30 | 3 | 3 | 7 | 0.80 | 0.10 | 0.10 | 2 | Speed/quality balance |
| **Balanced** | 60 | 3 | 4 | 12 | 0.85 | 0.10 | 0.10 | 2 | Balanced, good quality |
| **Large** | 100 | 4 | 5 | 15 | 0.80 | 0.10 | 0.10 | 2 | Best quality, slower |
| **Explore** | 100 | 2 | 1 | 15 | 0.95 | 0.40 | 0.25 | 3 | Aggressive exploration |
| **Tuned** | 81 | 4 | 4 | 25 | 0.675 | 0.236 | 0.259 | 2 | Optuna-optimized ⭐ |

### Running an Experiment with a Specific Config

```bash
cd backend
.venv\Scripts\python.exe run_experiments.py --config ../config/config_large.yaml
```

---

## 🧪 Automatic Tuning with Optuna

The project includes an **automatic hyperparameter optimization** system based on Optuna. The tuning process searches for the optimal combination of HGA parameters by running multiple trials on representative instances.

### Tuning Configuration

The `config/config_optuna.yaml` file controls the metaparameters of the tuning process:

```yaml
study_name: hga_tuning      # Study name (for resuming sessions)
trials: 100                 # Number of trials to run
budget: 100000              # Evaluations per trial (reduced for speed)
runs_per_trial: 2           # Independent runs per instance per trial
instances: []               # Instances to tune on (empty = automatic)
storage: sqlite:///results/tuning/tuning.db  # Persistent database
warm_start: true            # First trial uses default parameters
output_config: config/config_tuned.yaml      # Where to save the best config
output_dir: results/tuning  # Summary output directory
```

### Running Tuning Locally

```bash
cd backend
.venv\Scripts\python.exe tune_parameters.py --config ../config/config_optuna.yaml
```

When finished, `results/tuning/` will contain:
- `tuning_summary.json` — summary with best params, gap, top-5 trials
- `tuning.db` — Optuna database for resuming the study
- `config/config_tuned.yaml` — best HGA config found, ready for experiments

### Running Experiments with the Optimized Config

```bash
cd backend
.venv\Scripts\python.exe run_experiments.py --config ../config/config_tuned.yaml
```

---

## 🖥️ Execution on SLURM Cluster

The project includes ready-to-use scripts for execution on HPC clusters with **SLURM** and **Apptainer**.

### Cluster Setup

```bash
# 1. Sync files from local machine (PowerShell)
.\sync_cluster.ps1 -Action upload

# 2. On the cluster, load the aliases
source cluster/aliases.sh

# 3. Install dependencies
bash cluster/setup.sh
```

### Quick Commands (Aliases)

| Command | Description |
| :--- | :--- |
| `run-exp` | Launch all experiments via SLURM |
| `run-exp config_large` | Launch only the specified config |
| `tune` | Launch Optuna tuning via SLURM |
| `tune config_optuna_v2` | Launch tuning with a specific config |
| `myjobs` | List active jobs |
| `lastlog` | Follow the latest log |
| `runlog <ID>` | Follow a specific job's log |
| `killjob <ID>` | Cancel a job |
| `killalljobs` | Cancel all jobs |

### Automated Pipeline

`run-exp` runs sequentially for each config:
1. **Experiments** (`run_experiments.py`) — all 10 instances, 5 runs × 350K FE
2. **Plots** (`plot_convergence.py`) — convergence, routes, radar, comparison
3. **LaTeX Table** (`format_latex.py`) — per-config table
4. **Comparison Table** (`format_latex.py`) — cross-config comparison

`tune` runs:
1. **Optuna Tuning** (`tune_parameters.py`) — hyperparameter search
2. Saves the best config to `config/config_tuned.yaml`
3. Saves the summary to `results/tuning/tuning_summary.json`

---

## 📊 Experimental Protocol and Results (CVRPLIB Benchmark)

The experimental protocol runs the algorithm on **10 CVRPLIB benchmark instances** (distributed across 4 different sets: A, B, E, P), with **5 independent runs** each, and a strict stopping criterion of **350,000 fitness function evaluations (FE)**.

### Final Results Achieved (R = 5, FE = 350,000)

Thanks to automatic tuning with Optuna and algorithmic optimizations, the `config_tuned` configuration ($\mu=81$, $p_c=0.675$, $p_m=0.236$, $p_{ls}=0.259$, $\gamma=25$) achieved excellent results across all 10 instances, with an average gap of 0.84%:

| Instance | HGA Best Cost | Mean Cost | Std Dev | Optimal (BKS) | Gap% | Vehicles |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A-n45-k7** | 1146.77 | 1146.77 | 0.00 | 1146 | **0.07%** | 7 |
| **A-n60-k9** | 1355.80 | 1355.80 | 0.00 | 1354 | **0.13%** | 9 |
| **A-n80-k10** | 1784.41 | 1785.00 | 0.74 | 1763 | 1.21% | 10 |
| **B-n56-k7** | 712.92 | 712.92 | 0.00 | 707 | **0.84%** | 7 |
| **B-n66-k9** | 1326.20 | 1326.56 | 0.44 | 1316 | **0.78%** | 9 |
| **B-n78-k10** | 1227.90 | 1228.45 | 0.98 | 1221 | **0.56%** | 10 |
| **E-n76-k8** | 740.66 | 741.29 | 1.27 | 735 | **0.77%** | 8 |
| **E-n101-k14** | 1090.72 | 1092.38 | 0.83 | 1071 | 1.84% | 14 |
| **P-n50-k10** | 700.66 | 701.37 | 1.42 | 696 | **0.67%** | 10 |
| **P-n101-k4** | 691.29 | 691.83 | 0.66 | 681 | 1.51% | 4 |

### Cross-Config Comparison

The following table compares all 7 configuration variants across the 10 benchmark instances.
For each instance, the value with the **lowest gap%** (best) is highlighted in **bold**.

| Instance | Optimal | Tuned | Balanced | Explore | Large | Medium | Small | Fast |
| --- |--- |--- |--- |--- |--- |--- |--- |--- |
| A-n45-k7 | 1146 | **1,146.77 (+0.07%)** | **1,146.77 (+0.07%)** | **1,146.77 (+0.07%)** | **1,146.77 (+0.07%)** | 1,146.91 (+0.08%) | 1,146.91 (+0.08%) | 1,164.09 (+1.58%) |
| A-n60-k9 | 1354 | **1,355.80 (+0.13%)** | 1,360.59 (+0.49%) | 1,367.35 (+0.99%) | **1,355.80 (+0.13%)** | 1,360.59 (+0.49%) | 1,367.34 (+0.99%) | 1,367.97 (+1.03%) |
| A-n80-k10 | 1763 | **1,784.41 (+1.21%)** | 1,802.63 (+2.25%) | 1,848.12 (+4.83%) | 1,796.37 (+1.89%) | 1,830.48 (+3.83%) | 1,817.37 (+3.08%) | 1,809.79 (+2.65%) |
| B-n56-k7 | 707 | **712.92 (+0.84%)** | **712.92 (+0.84%)** | 714.69 (+1.09%) | **712.92 (+0.84%)** | **712.92 (+0.84%)** | **712.92 (+0.84%)** | 716.42 (+1.33%) |
| B-n66-k9 | 1316 | 1,326.20 (+0.78%) | 1,325.57 (+0.73%) | 1,338.88 (+1.74%) | 1,326.20 (+0.78%) | **1,324.84 (+0.67%)** | 1,327.10 (+0.84%) | 1,329.01 (+0.99%) |
| B-n78-k10 | 1221 | **1,227.90 (+0.56%)** | 1,229.69 (+0.71%) | 1,262.89 (+3.43%) | **1,227.90 (+0.56%)** | **1,227.90 (+0.56%)** | 1,238.33 (+1.42%) | 1,229.69 (+0.71%) |
| E-n101-k14 | 1071 | **1,090.72 (+1.84%)** | 1,093.96 (+2.14%) | 1,109.37 (+3.58%) | 1,093.96 (+2.14%) | 1,102.78 (+2.97%) | 1,097.02 (+2.43%) | 1,105.88 (+3.26%) |
| E-n76-k8 | 735 | **740.66 (+0.77%)** | 744.18 (+1.25%) | 757.56 (+3.07%) | **740.66 (+0.77%)** | 746.28 (+1.53%) | 750.44 (+2.10%) | **740.66 (+0.77%)** |
| P-n101-k4 | 681 | **691.29 (+1.51%)** | **691.29 (+1.51%)** | 692.64 (+1.71%) | **691.29 (+1.51%)** | 692.64 (+1.71%) | 693.54 (+1.84%) | 692.64 (+1.71%) |
| P-n50-k10 | 696 | **700.66 (+0.67%)** | **700.66 (+0.67%)** | **700.66 (+0.67%)** | 704.61 (+1.24%) | 704.61 (+1.24%) | **700.66 (+0.67%)** | 704.91 (+1.28%) |

The **Tuned** configuration is among the best (solely or tied) on 9 out of 10 instances, being strictly better than all others on A-n80-k10 and E-n101-k14. With an average gap of **0.84%**, it is the best overall configuration.

### Running the Benchmark
To re-run the entire experimental protocol:
```bash
cd backend
.venv\Scripts\python.exe run_experiments.py --config ../config/config_large.yaml
```
Results are saved to `results/<config_name>/results.json`.

### Generating High-Resolution Plots

The `plot_convergence.py` script automatically generates a set of **9+ publication-quality plots** (saved in the `docs/report/imgs/` directory at 300 DPI):

1. **Convergence Plots** (`imgs/convergence/`): Visualization of 5 individual runs, standard deviation ($\pm 1\sigma$), average behavior, and best run for each representative instance.
2. **Best Route Plots** (`imgs/routes/`): 2D geometric trace of the actual vehicle routes, with colorblind-friendly color differentiation, markers proportional to customer demands, and numerical indication of stop order.
3. **Summary Plots** (`imgs/summary/`):
   - `summary_best_vs_bks.png`: Direct comparison bar chart between HGA best cost and BKS optimal value.
   - `summary_gap.png`: Percentage deviation (gap) chart relative to the optimum for all instances.
   - `summary_boxplot.png`: Normalized cost distribution as a percentage of BKS to analyze the algorithm's statistical stability.
   - `summary_runtime.png`: Scatter plot of computational time required as a function of node count.
   - `summary_radar.png`: Multi-variable radar chart comparing normalized performance (Route length, Stability, Gap, Time/node, Convergence) for each set (A, B, E, P) and each configuration variant.
   - `summary_config_comparison.png`: Comparison across all configuration variants on aggregate metrics.
   - `summary_generations.png`: Average number of evolutionary generations needed to converge to the optimal solution.
   - `summary_route_length.png`: Average route length in terms of customers served per vehicle.

To generate/update the full set of plots:
```bash
cd backend
.venv\Scripts\python.exe plot_convergence.py --results ../results/config_large/results.json --imgs ../docs/report/imgs/config_large
```

---

## 🧬 Algorithm Optimizations (HGA)

To achieve extremely high execution speeds (**up to over 6,900 evaluations per second per core**), the HGA architecture has been enhanced with 9 key optimizations including $O(1)$ load precomputation, index-only move tracking, double-tier education (light/full), duplicate detection, and generator micro-optimizations.

> 📖 See [docs/cvrp.md §7](docs/cvrp.md#7-dettagli-di-ottimizzazione-del-codice-performance) for a detailed explanation of each optimization technique.
