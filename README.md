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
│   ├── test_quick.py         # Test rapido di esecuzione dell'algoritmo
│   └── test_minimal.py       # Test unitario e di compilazione Numba
├── frontend/                 # Dashboard interattiva React
│   ├── src/
│   │   ├── App.tsx           # Componente principale e gestione WebSocket
│   │   ├── index.css         # Stili e design del tema scuro (glassmorphic)
│   │   └── main.tsx          # Entry point React
│   ├── package.json          # Dipendenze JavaScript (gestito con bun)
│   └── vite.config.ts        # Configurazione Vite con proxy API/WebSocket
├── instances/                # Istanze del benchmark ufficiale CVRPLIB (.vrp)
├── docs/
│   └── report/               # Relazione di progetto in LaTeX
│       ├── report.tex        # Codice sorgente del report accademico
│       └── report.pdf        # PDF compilato del report
└── README.md                 # Questo file
```

---

## 🛠️ Tecnologie Utilizzate

### Backend (Python 3.11+)
- **FastAPI & Uvicorn**: Server REST API e WebSocket per la comunicazione in tempo reale.
- **Numba (JIT Compiler)**: Compilazione Just-In-Time del codice critico per prestazioni equivalenti al C/C++.
- **NumPy**: Gestione efficiente delle matrici di adiacenza e delle coordinate dei nodi.

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

pip install -r requirements.txt # o installa manualmente fastapi uvicorn numpy numba matplotlib
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

- **Test minimale di compilazione Numba**:
  ```bash
  cd backend
  .venv\Scripts\python.exe test_minimal.py
  ```
- **Test rapido dell'algoritmo (2000 valutazioni)**:
  ```bash
  cd backend
  .venv\Scripts\python.exe test_quick.py
  ```

---

## 📊 Protocollo Sperimentale (Benchmark CVRPLIB)

Il protocollo sperimentale prevede l'esecuzione dell'algoritmo su **10 istanze del benchmark CVRPLIB** (distribuite in 4 set differenti), per **5 run indipendenti** ciascuna, con un criterio di arresto rigoroso fissato a **350.000 valutazioni della funzione fitness (FE)**.

Le istanze utilizzate sono:
1. **Set A**: `A-n45-k7`, `A-n60-k9`, `A-n80-k10`
2. **Set B**: `B-n56-k7`, `B-n66-k9`, `B-n78-k10`
3. **Set E**: `E-n76-k8`, `E-n101-k14`
4. **Set P**: `P-n50-k10`, `P-n101-k4`

### Esecuzione Automatica del Benchmark

È presente uno script dedicato per l'esecuzione automatica del protocollo sperimentale completo su tutte le 10 istanze. I risultati intermedi vengono salvati progressivamente in formato JSON (`backend/results.json`) per garantire la persistenza dei dati anche in caso di interruzioni.

Per avviare il benchmark:
```bash
cd backend
.venv\Scripts\python.exe run_experiments.py
```

Al termine dell'esecuzione, lo script genererà un sommario a terminale con le statistiche richieste per la relazione finale: **Best Cost**, **Mean Cost**, **Standard Deviation**, **Average Generations to Best** ed **Execution Time** per ciascuna istanza, confrontati con il valore ottimo noto del benchmark.

---

## 🧬 Dettagli dell'Algoritmo (HGA)

L'**Algoritmo Genetico Ibrido** combina la capacità di esplorazione globale dei GA con l'accuratezza di raffinamento locale degli algoritmi di ricerca locale:

1. **Rappresentazione (Encoding)**: Una soluzione è codificata come una permutazione di clienti (senza depot intermedio).
2. **Decodifica (Split di Prins)**: Un algoritmo di programmazione dinamica in $O(n^2)$ partiziona in modo ottimale la permutazione in rotte veicolari che rispettano la capacità di carico $\sigma$.
3. **Operatori di Selezione e Crossover**: Order Crossover (OX) con probabilità $0.9$ e Selezione a Torneo ($k=2$).
4. **Operatori di Mutazione**: Swap (40%), Insert (30%) e Inversion (30%) applicati con un tasso complessivo del $0.3$.
5. **Ricerca Locale (Local Search)**: Applicata con tasso del $0.1$, esegue in pipeline:
   - **2-opt** (intra-route): inverte segmenti di rotta per eliminare incroci (accelerato JIT).
   - **Or-opt** (intra-route): sposta segmenti di 1, 2 o 3 nodi contigui.
   - **Relocate** (inter-route): sposta un nodo tra rotte diverse.
   - **Exchange** (inter-route): scambia due nodi tra rotte diverse.
