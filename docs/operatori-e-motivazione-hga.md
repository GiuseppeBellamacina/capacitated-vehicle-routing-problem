# Operatori Caratteristici e Motivazione della Scelta dell'HGA

Questo documento risponde a due quesiti fondamentali posti dal progetto:

1. **Quali sono gli operatori caratteristici dell'algoritmo HGA implementato?**
2. **Perché è stato scelto l'HGA rispetto alle alternative proposte?**

---

## 1. Operatori Caratteristici dell'HGA Implementato

L'algoritmo è un **Algoritmo Genetico Ibrido (HGA)**, detto anche **Algoritmo Memetico**, che combina i meccanismi di esplorazione globale di un algoritmo genetico con operatori di ricerca locale per il raffinamento intensivo. Ogni scelta progettuale è motivata di seguito.

### 1.1 Rappresentazione del Cromosoma: Permutazione Senza Delimitatori + Split di Prins

**Scelta**: Il cromosoma è una semplice permutazione dei clienti (es. `[3, 7, 1, 5, 2, 4, 6]`), **senza delimitatori di rotta**.

**Motivazione**: Le rappresentazioni con delimitatori (es. `[0, 3, 7, 1, 0, 5, 2, 0, 4, 6]`) producono figli non validi durante il crossover, richiedendo costose riparazioni. La permutazione semplice, invece:

- Garantisce che qualsiasi permutazione sia un cromosoma sintatticamente valido.
- Delega il partizionamento in rotte all'**Algoritmo di Split di Prins (2004)**, che risolve il sottoproblema di routing in modo **ottimale** tramite programmazione dinamica in tempo $O(n^2)$.
- Separa elegantemente il problema di *sequenziamento* dei clienti (compito del GA) dal problema di *partizionamento in rotte* (compito dello Split).

L'equazione di ricorrenza DP è:

$$V(j) = \min_{i < j \text{ s.t. } \text{load}(i+1 \dots j) \le Q} \{ V(i) + w(i, j) \}$$

dove $V(j)$ è il costo ottimo per servire i primi $j$ clienti e $w(i,j)$ è il costo della rotta che serve i clienti da $i+1$ a $j$.

### 1.2 Generazione della Popolazione Iniziale: Euristiche + Random

**Operatori utilizzati**:

| Fonte | Quantità | Descrizione |
|:---|:---:|:---|
| **Nearest Neighbor** | 1 | Costruzione greedy: partendo dal deposito, si visita sempre il cliente più vicino non ancora servito |
| **Clarke & Wright Savings** | 1 | Calcola i risparmi $s_{ij} = c_{i0} + c_{0j} - c_{ij}$ e unisce le rotte in ordine decrescente di risparmio |
| **Permutazioni casuali** | $\mu - 2$ | Mescolamento casuale (shuffle) dei clienti |

**Motivazione**: Le due soluzioni euristiche forniscono "punti di partenza" di buona qualità, accelerando la convergenza iniziale. Le permutazioni casuali garantiscono **diversità genetica**, evitando la convergenza prematura della popolazione su un ottimo locale. La proporzione (~97.5% random nella configurazione Tuned con $\mu=81$) è deliberatamente sbilanciata verso l'esplorazione.

### 1.3 Selezione: Torneo con k=4

**Operatore**: **Tournament Selection**. Si estraggono $k=4$ individui a caso dalla popolazione e si seleziona quello con fitness (costo) minore.

**Motivazione**: Rispetto alla roulette wheel (che soffre di dominanza precoce dei migliori) e alla selezione per rango (più lenta), il torneo:

- Offre un equilibrio regolabile tramite $k$ tra **pressione selettiva** ($k$ alto favorisce i migliori) e **diversità** ($k$ basso dà più chance agli individui mediocri).
- Non richiede il calcolo di probabilità proporzionali alla fitness.
- Il valore $k=4$ (determinato da Optuna) offre una pressione selettiva moderata-alta, adatta a un paesaggio di fitness complesso come il CVRP.

### 1.4 Crossover: Order Crossover (OX)

**Operatore**: **Order Crossover** con due punti di taglio casuali, probabilità $p_c = 0.675$ (Tuned).

**Funzionamento**:
1. Si scelgono due punti di taglio $cx1$, $cx2$ sui genitori.
2. Il figlio eredita il segmento $[cx1, cx2]$ dal **primo genitore**.
3. Le posizioni restanti sono riempite scorrendo il **secondo genitore** in ordine circolare, saltando i nodi già presenti.

**Motivazione**: OX è l'operatore ideale per permutazioni perché:

- **Preserva l'ordine relativo** di entrambi i genitori (a differenza di PMX che preserva le posizioni assolute, meno rilevante nel routing).
- **Non produce duplicati**: ogni cliente appare esattamente una volta — non servono riparazioni.
- **Trasmette blocchi contigui**, che spesso corrispondono a sequenze di clienti geograficamente vicine (buone rotte parziali).
- È l'operatore standard nella letteratura VRP basata su Split (Prins, 2004; Vidal et al., 2012).

Tasso $p_c = 0.675$ (inferiore al default 0.8) — Optuna ha determinato che un crossover leggermente meno frequente, combinato con più ricerca locale, produce risultati migliori.

### 1.5 Mutazione: Tre Operatori Stocastici

**Operatori** (scelti casualmente a ogni attivazione, $p_m = 0.236$, Tuned):

| Operatore | Probabilità | Effetto |
|:---|:---:|:---|
| **Swap** | 40% | Scambia due clienti in posizioni casuali |
| **Insert** | 30% | Rimuove un cliente e lo reinserisce in un'altra posizione |
| **Inversion** | 30% | Inverte un segmento contiguo della permutazione |

**Motivazione**:

- **Swap**: Produce perturbazioni locali, utile per il fine-tuning di buone soluzioni. È complementare al 2-opt della ricerca locale (che opera sulle rotte, non sulla permutazione).
- **Insert**: Modifica l'ordine relativo in modo più drastico dello swap, aiutando a "saltare" fuori da ottimi locali.
- **Inversion**: Cambia la direzione di visita di un gruppo di clienti. Poiché il CVRP usa distanze simmetriche, l'inversione non altera la fitness della permutazione ma cambia radicalmente l'output dello Split, creando nuove opportunità di partizionamento.

La scelta stocastica dell'operatore evita bias sistematici e mantiene la diversità delle perturbazioni. Il tasso $p_m = 0.236$, quasi doppio rispetto al default 0.1, riflette la necessità di esplorazione aggressiva identificata da Optuna.

### 1.6 Ricerca Locale: Quattro Operatori con Strategia Steepest Descent

Tutti gli operatori usano strategia **steepest descent** (best improvement): viene valutato l'intero vicinato e applicata la mossa col miglioramento maggiore.

#### 1.6.1 Intra-Route (stessa rotta)

| Operatore | Complessità | Ruolo |
|:---|:---:|:---|
| **2-opt** | $O(n_r^2)$ | Elimina incroci di percorso invertendo un segmento. Calcolo delta: $\Delta = (c_{i,j} + c_{i+1,j+1}) - (c_{i,i+1} + c_{j,j+1})$ |
| **Or-opt** | $O(n_r^3)$ (mitigato da Numba) | Riloca un segmento contiguo di 1–3 clienti in un'altra posizione della stessa rotta |

**Entrambi sono compilati JIT con Numba** (`@njit(cache=True, nogil=True)`), raggiungendo velocità vicine al C nativo.

#### 1.6.2 Inter-Route (tra rotte diverse)

| Operatore | Ruolo |
|:---|:---|
| **Relocate** | Sposta un cliente da una rotta A a una rotta B (se la capacità di B lo consente) |
| **Exchange** | Scambia un cliente della rotta A con uno della rotta B (verificando capacità) |

**Ottimizzazioni critiche**:
- **Delta cost evaluation $O(1)$**: si calcola solo la differenza di costo delle due rotte modificate: $\Delta = (\text{costo}_{A, dopo} + \text{costo}_{B, dopo}) - (\text{costo}_{A, prima} + \text{costo}_{B, prima})$
- **Pre-calcolo dei carichi**: i load delle rotte sono mantenuti in vettori e aggiornati in $O(1)$ ad ogni mossa, evitando ricalcoli $O(n)$.
- **Tracciamento solo per indici**: il vicinato viene esplorato calcolando solo indici e delta; la mossa fisica (costosa) viene applicata in-place solo alla fine.
- **Ordine randomizzato**: Relocate ed Exchange vengono eseguiti in ordine casuale a ogni chiamata per evitare bias.
- **Limite iterazioni** (`max_iter=2`): evita di sprecare budget computazionale su miglioramenti infinitesimali.

### 1.7 Educazione a Due Livelli (Light/Full)

| Livello | Operatori | Frequenza | Costo |
|:---|:---|:---|:---|
| **Light** | Solo 2-opt (JIT Numba) | **100% dei figli** | Molto basso |
| **Full** | 2-opt + Or-opt + Relocate + Exchange | $p_{ls} = 25.9\%$ (Tuned) | Alto (5 FE) |

**Motivazione**: L'educazione leggera garantisce che ogni figlio abbia almeno le rotte "disincrociate" (2-opt), eliminando difetti banali a costo quasi nullo. La ricerca locale completa, molto più costosa, viene applicata solo a una frazione dei figli, massimizzando il rapporto qualità/tempo CPU.

### 1.8 Ricerca Locale Granulare (GLS)

**Operatore**: Per Relocate ed Exchange, un cliente viene considerato per lo spostamento solo se è tra i $\gamma = 25$ vicini più prossimi (per distanza euclidea) dei nodi adiacenti nella rotta di destinazione.

**Motivazione**: Senza GLS, la ricerca locale inter-route ha complessità $O(m^2 \cdot n_r^2)$ dove $m$ è il numero di rotte. Con GLS, il vicinato si riduce drasticamente perché:
- È improbabile che spostare un cliente in una rotta geograficamente lontana produca un miglioramento.
- Il filtro di granularità è applicato in $O(1)$ grazie a un hash set pre-calcolato.
- Il valore $\gamma = 25$, quasi doppio rispetto al default 15, è stato determinato da Optuna — un vicinato più ampio paga in termini di qualità.

### 1.9 Rilevamento Duplicati (Survivor Selection)

**Operatore**: A ogni generazione, individui con costo identico (arrotondato alla terza cifra decimale) vengono identificati come cloni e **sostituiti con individui casuali freschi** (pre-educati con 2-opt).

**Motivazione**: Senza questo meccanismo, la popolazione collasserebbe rapidamente su poche soluzioni quasi identiche (deriva genetica), sprecando il budget computazionale e impedendo ulteriore miglioramento. La sostituzione con random freschi mantiene la diversità senza introdurre parametri aggiuntivi.

### 1.10 Elitismo (e=4)

**Operatore**: I migliori 4 individui di ogni generazione vengono copiati **inalterati** nella generazione successiva.

**Motivazione**: Garantisce la proprietà di **non-decrescenza** della fitness ottima: la migliore soluzione trovata non può mai essere persa. Con $e=4$, si preserva un piccolo nucleo d'élite senza soffocare la diversità.

### 1.11 Ottimizzazioni Computazionali (Originalità Implementative)

| Tecnica | Impatto |
|:---|:---|
| **Numba JIT** su split, crossover, 2-opt, Or-opt | ~50-100× più veloce del Python puro |
| **Delta cost evaluation** | $O(1)$ per mossa invece di $O(n)$ |
| **Pre-calcolo carichi** | $O(1)$ capacity check invece di $O(n)$ |
| **Indice, non deep-copy** | Nessuna allocazione nel ciclo interno |
| **Micro-ottimizzazioni dei generatori** | Offset matematici diretti invece di `random.sample()` |
| **Mutazioni in-place con backtracking** | Copia solo se la mossa è accettata |
| **Percorso rapido per k=2** | Branch dedicato per torneo binario |

Queste ottimizzazioni permettono all'algoritmo di raggiungere **oltre 6.900 valutazioni al secondo per core**, rendendo fattibili 350.000 FE in ~50 secondi anche su istanze da 101 clienti.

---

## 2. Perché l'HGA e Non un Altro Algoritmo?

La scelta tra i cinque algoritmi proposti — **Tabu Search (TS)**, **Algoritmo Immunologico (AI)**, **Ant Colony Optimization (ACO)**, **Algoritmo Genetico Ibrido (HGA)**, **Algoritmo Immunologico con Penalty Function (AI+PF)** — è stata guidata da considerazioni teoriche, pratiche e di letteratura.

### 2.1 HGA vs Tabu Search (TS)

**Tabu Search** è un algoritmo a singola soluzione: mantiene una sola soluzione corrente e la migliora iterativamente esplorandone il vicinato, usando una *tabu list* per evitare cicli.

| Aspetto | TS | HGA |
|:---|:---|:---|
| Esplorazione | Singola traiettoria | Popolazione → esplorazione parallela |
| Rischio | Intrappolamento in ottimi locali | Mitigato dalla diversità della popolazione |
| Memoria | Esplicita (tabu list) | Implicita (pool genetico) |
| Tuning | Tabu tenure critico e problem-dependent | Molti parametri, ma più robusti |

**Perché non TS**: La TS richiede la progettazione di una *struttura di vicinato* e una *tabu list* specifiche per il CVRP. Definire la tabu tenure ottimale è notoriamente difficile: troppo breve e l'algoritmo cicla, troppo lunga e restringe eccessivamente la ricerca. Inoltre, la TS essendo single-solution non beneficia della diversificazione implicita di una popolazione, rendendola più suscettibile al paesaggio di fitness multimodale del CVRP.

### 2.2 HGA vs Algoritmo Immunologico (AI)

L'**AI** si ispira al principio di **selezione clonale**: gli anticorpi (soluzioni) con alta affinità (bassa fitness) vengono clonati e ipermutati proporzionalmente alla loro affinità.

| Aspetto | AI | HGA |
|:---|:---|:---|
| Ricombinazione | Assente (solo clonazione + mutazione) | Crossover OX → trasmissione di blocchi |
| Convergenza | Potenzialmente lenta senza ricombinazione | Il crossover accelera la propagazione di buoni pattern |
| Letteratura CVRP | Scarsa | Molto ricca (Prins 2004, Vidal 2012, Nagata 2010) |

**Perché non AI**: L'assenza di un operatore di ricombinazione è una limitazione significativa per il CVRP. Il crossover OX permette di **combinare blocchi di clienti geograficamente coesi** da due buone soluzioni, cosa che la sola mutazione non può fare efficientemente. Inoltre, l'HGA gode di una letteratura CVRP molto più solida, con operatori ben studiati e comprovati.

### 2.3 HGA vs Ant Colony Optimization (ACO)

L'**ACO** costruisce soluzioni in modo costruttivo: formiche artificiali percorrono il grafo depositando feromoni, e le formiche successive preferiscono archi con più feromone.

| Aspetto | ACO | HGA |
|:---|:---|:---|
| Costruzione | Costruttiva (arco per arco) | Basata su Split (ottimale dato l'ordine) |
| Ricerca locale | Difficile da integrare in modo fluido | Integrata nativamente (ibridazione) |
| Velocità | Potenzialmente lenta (molte formiche, evaporazione) | Molto veloce con Numba JIT |
| Parametri | Feromone: $\alpha$, $\beta$, $\rho$ — accoppiati e delicati | Separabili e tunabili indipendentemente |

**Perché non ACO**: Sebbene l'ACO sia naturalmente adatta ai problemi di routing, l'integrazione con ricerca locale è meno fluida che nell'HGA. Nell'ACO, la ricerca locale è tipicamente un post-processing, mentre nell'HGA è parte integrante del ciclo evolutivo. Inoltre, i parametri dell'ACO ($\alpha$ per il feromone, $\beta$ per l'euristica, $\rho$ per l'evaporazione) sono fortemente accoppiati e difficili da tunare. L'HGA, con la sua architettura modulare, permette di ottimizzare ogni operatore in modo relativamente indipendente.

### 2.4 HGA vs Algoritmo Immunologico con Penalty Function (AI+PF)

L'**AI+PF** lavora con soluzioni **infeasibili**, penalizzando le violazioni di capacità nella funzione fitness.

| Aspetto | AI+PF | HGA |
|:---|:---|:---|
| Soluzioni | Infeasibili permesse, penalizzate | Solo feasible (garantite dallo Split) |
| Penalty | Pesi difficili da calibrare | Non necessaria |
| Complessità | Gestione del trade-off qualità/violazione | Lo Split gestisce la feasibility automaticamente |

**Perché non AI+PF**: La gestione dei pesi di penalità è notoriamente problematica. Un peso troppo basso e l'algoritmo restituisce soluzioni infeasible; troppo alto e lo spazio di ricerca viene eccessivamente ristretto, perdendo i benefici di esplorare l'infeasibilità. L'HGA, grazie all'algoritmo di Split di Prins, **garantisce la feasibility per costruzione** — ogni cromosoma viene partizionato in rotte che rispettano la capacità $Q$. Questo elimina completamente la necessità di gestire penalità e costituisce un vantaggio architetturale decisivo.

### 2.5 Vantaggi Decisivi dell'HGA — Sintesi

1. **Decomposizione elegante**: La permutazione + Split separa il sequenziamento dal routing. Il GA esplora lo spazio delle permutazioni; lo Split risolve ottimamente il routing. Questa decomposizione è il fondamento teorico più solido tra tutte le alternative.

2. **Ibridazione nativa**: A differenza di TS, AI e ACO (dove la ricerca locale è un'aggiunta posticcia), nell'HGA la ricerca locale è **parte integrante del ciclo evolutivo**, applicata ai figli prima che entrino nella popolazione. È questa la definizione stessa di algoritmo memetico.

3. **Ampia letteratura di支持**: L'HGA con Split di Prins è lo stato dell'arte per il CVRP da quasi 20 anni (Prins 2004, Vidal et al. 2012, 2013). Implementare un algoritmo con una base teorica così solida permette di concentrare l'originalità sulle **ottimizzazioni computazionali** (Numba JIT, delta evaluation, GLS) piuttosto che su scelte algoritmiche fondamentali rischiose.

4. **Tunability**: Lo spazio dei parametri HGA è ampio ma ben compreso, e si presta al tuning automatico con Optuna (TPE). Questo ha permesso di ottenere la configurazione Tuned, con parametri ottimizzati che sarebbero stati difficili da determinare manualmente (es. $p_c = 0.675$, $p_{ls} = 0.259$, $\gamma = 25$).

5. **Performance**: Grazie alle ottimizzazioni implementative (Numba JIT, delta evaluation, GLS), l'HGA raggiunge $\approx 6.900$ valutazioni/secondo, completando 350.000 FE in ~50 secondi. Questa velocità permette di eseguire 5 run × 10 istanze in tempi ragionevoli anche su hardware consumer.

### 2.6 Tabella Riassuntiva del Confronto

| Criterio | TS | AI | ACO | AI+PF | **HGA** |
|:---|:---:|:---:|:---:|:---:|:---:|
| Esplorazione globale | ✗ Singola traiettoria | ✓ Popolazione | ✓ Popolazione (formiche) | ✓ Popolazione | ✓✓ Popolazione + diversità esplicita |
| Ricombinazione | ✗ | ✗ | ✗ (solo feromone) | ✗ | ✓ Order Crossover |
| Ricerca locale | ✓ (add-on) | ✗ | ✓ (post-processing) | ✗ | ✓✓ (integrata, 4 operatori) |
| Gestione feasibility | Manuale | Manuale | Manuale | Penalty (complessa) | ✓✓ Automatica (Split) |
| Letteratura CVRP | Media | Bassa | Media | Bassa | ✓✓ Molto ricca |
| Tunability | Difficile (tabu tenure) | Media | Difficile (feromoni accoppiati) | Difficile (penalty weights) | ✓ Buona (parametri separabili) |
| Velocità (con JIT) | Alta | Media | Media-Bassa | Media | ✓✓ Molto alta (~6900 FE/s) |

---

## Riferimenti Bibliografici

- Prins, C. (2004). *A simple and effective evolutionary algorithm for the vehicle routing problem.* Computers & Operations Research, 31(12), 1985–2002.
- Vidal, T., Crainic, T. G., Gendreau, M., Lahrichi, N., & Rei, W. (2012). *A hybrid genetic algorithm for multidepot and periodic vehicle routing problems.* Operations Research, 60(3), 611–624.
- Vidal, T., Crainic, T. G., Gendreau, M., & Prins, C. (2013). *A hybrid genetic algorithm with adaptive diversity management for a large class of vehicle routing problems with time-windows.* Computers & Operations Research, 40(1), 475–489.
- Nagata, Y., & Bräysy, O. (2009). *A powerful route minimization heuristic for the vehicle routing problem with time windows.* Operations Research Letters, 37(5), 333–338.
- Toth, P., & Vigo, D. (2014). *Vehicle Routing: Problems, Methods, and Applications.* SIAM.
