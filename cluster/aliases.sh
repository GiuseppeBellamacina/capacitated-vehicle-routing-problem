#!/bin/bash
# ============================================================================
# Alias utili per il cluster DMI — CVRP Solver (HGA)
#
# Uso:
#   source cluster/aliases.sh
#
# Per caricarli automaticamente, aggiungi al tuo ~/.bashrc:
#   source ~/capacitated-vehicle-routing-problem/cluster/aliases.sh
# ============================================================================

PROJ_DIR="$HOME/capacitated-vehicle-routing-problem"

# ── Job management ───────────────────────────────────────────────────────────

# Controlla i miei job attivi
alias myjobs='squeue --me --format="%.10i %.20j %.8T %.10M %.6D %.20R %o"'

# Info dettagliata su un job (uso: jobinfo <JOB_ID>)
jobinfo() {
    if [ -z "$1" ]; then
        echo "Uso: jobinfo <JOB_ID>"
        return 1
    fi
    scontrol show job "$1"
}

# Cancella un job (uso: killjob <JOB_ID>)
alias killjob='scancel'

# Cancella tutti i miei job
alias killalljobs='scancel --me'

# ── Log monitoring ───────────────────────────────────────────────────────────

# Segui il log di un job (uso: runlog <JOB_ID>)
runlog() {
    if [ -z "$1" ]; then
        echo "Uso: runlog <JOB_ID>"
        return 1
    fi
    local logfile="$PROJ_DIR/logs/slurm-train-${1}.log"
    if [ ! -f "$logfile" ]; then
        echo "Log non trovato: $logfile"
        return 1
    fi
    tail -f "$logfile"
}

# Mostra l'ultimo log — uso: lastlog [N_RIGHE]
# Senza argomento: tail -f (segui). Con argomento: mostra ultime N righe.
lastlog() {
    local logfile
    logfile=$(ls -t "$PROJ_DIR"/logs/slurm*.log 2>/dev/null | head -1)
    if [ -z "$logfile" ]; then
        echo "Nessun log trovato in $PROJ_DIR/logs/"
        return 1
    fi
    echo "==> $logfile <=="
    if [ -n "$1" ]; then
        tail -n "$1" "$logfile"
    else
        tail -f "$logfile"
    fi
}

# ── Filesystem ───────────────────────────────────────────────────────────────

# Tree ricorsivo di una cartella (uso: tree <DIR> [DEPTH])
tree() {
    local dir="${1:-.}"
    local depth="${2:-3}"
    find "$dir" -maxdepth "$depth" | sed -e "s|[^/]*/|  |g" -e "s|  |├─|"
}

# ── GPU & risorse ────────────────────────────────────────────────────────────

# Uso disco del progetto
alias quota='quota -s'

# ── Quick commands ───────────────────────────────────────────────────────────

# Vai alla directory del progetto
alias proj='cd "$PROJ_DIR"'

# Vai alla directory backend
alias backend='cd "$PROJ_DIR/backend"'

# ── Pip / Environment ────────────────────────────────────────────────────────

# Pulisci tutti i pacchetti --user
pip-clean() {
    echo "🗑️  Rimozione pacchetti pip --user..."
    rm -rf ~/.local/lib/python3.*/site-packages/*
    rm -rf ~/.local/bin/*
    echo "✅ ~/.local ripulito"
}

# (Re)installa dipendenze da setup.sh
pip-setup() {
    echo "📦 Installazione dipendenze..."
    cd "$PROJ_DIR" && bash cluster/setup.sh
}

# Pulisci e reinstalla da zero
pip-reset() {
    pip-clean
    pip-setup
}

# ── CVRP specific ────────────────────────────────────────────────────────────

# Lancia esperimenti (sbatch cluster/run.sh — esegue tutte le config in sequenza)
run-exp() {
    cd "$PROJ_DIR" && sbatch cluster/run.sh
}

# Genera grafici dai risultati
plots() {
    cd "$PROJ_DIR/backend" && python3 plot_convergence.py
}

# Formatta tabella LaTeX
latex-table() {
    cd "$PROJ_DIR/backend" && python3 format_latex.py table
}

# Scarica risultati dal cluster
pull-results() {
    cd "$PROJ_DIR" && scp -r "bllgpp02h24c351g@gcluster.dmi.unict.it:~/capacitated-vehicle-routing-problem/results/" results/
    echo "✅ Risultati scaricati in results/"
}

# ── Pulizia ──────────────────────────────────────────────────────────────────

# Pulizia workspace (uso: clean [--force])
clean() {
    cd "$PROJ_DIR" && bash cluster/clean.sh "$@"
}

# ── Meta ─────────────────────────────────────────────────────────────────────

_CVRP_ALIASES="myjobs jobinfo killjob killalljobs runlog lastlog tree quota proj backend pip-clean pip-setup pip-reset run-exp plots latex-table pull-results clean"

# Mostra i comandi disponibili
cvrp-help() {
    echo "Comandi CVRP disponibili:"
    echo ""
    echo "── Job management ──"
    echo "   myjobs            — lista job attivi"
    echo "   jobinfo <ID>      — dettagli job"
    echo "   killjob <ID>      — cancella job"
    echo "   killalljobs       — cancella tutti i miei job"
    echo ""
    echo "── Log monitoring ──"
    echo "   runlog <ID>       — segui log esperimenti"
    echo "   lastlog [N]       — segui l'ultimo log (N=ultime N righe)"
    echo ""
    echo "── CVRP ──"
    echo "   run-exp           — lancia esperimenti via SLURM"
    echo "   plots             — genera tutti i grafici"
    echo "   latex-table       — formatta tabella LaTeX"
    echo "   pull-results      — scarica risultati dal cluster"
    echo ""
    echo "── Utilità ──"
    echo "   proj              — cd al progetto"
    echo "   backend           — cd alla directory backend"
    echo "   tree <DIR> [N]    — albero cartelle (profondità N)"
    echo "   quota             — uso disco progetto"
    echo "   clean             — pulizia workspace (usa --force per cancellare)"
    echo ""
    echo "── Pip / Environment ──"
    echo "   pip-clean         — rimuovi tutti i pacchetti pip --user"
    echo "   pip-setup         — (re)installa dipendenze (cluster/setup.sh)"
    echo "   pip-reset         — pip-clean + pip-setup"
    echo ""
    echo "── Meta ──"
    echo "   cvrp-help         — mostra questo messaggio"
}

# Rimuovi tutti gli alias e funzioni custom (solo sessione corrente)
unload-aliases() {
    for cmd in $_CVRP_ALIASES; do
        unalias "$cmd" 2>/dev/null
        unset -f "$cmd" 2>/dev/null
    done
    unset _CVRP_ALIASES PROJ_DIR
    echo "✅ Alias CVRP rimossi (sessione corrente)."
}

_ALIASES_SOURCE_LINE="source ~/capacitated-vehicle-routing-problem/cluster/aliases.sh"

# Aggiungi alias al .bashrc (caricati ad ogni login)
install-aliases() {
    if grep -qF "$_ALIASES_SOURCE_LINE" ~/.bashrc 2>/dev/null; then
        echo "⚠️  Alias già presenti in ~/.bashrc"
    else
        echo "$_ALIASES_SOURCE_LINE" >> ~/.bashrc
        echo "✅ Alias aggiunti a ~/.bashrc (attivi dal prossimo login)"
    fi
}

# Rimuovi alias dal .bashrc
uninstall-aliases() {
    if grep -qF "$_ALIASES_SOURCE_LINE" ~/.bashrc 2>/dev/null; then
        sed -i "\|$_ALIASES_SOURCE_LINE|d" ~/.bashrc
        echo "✅ Alias rimossi da ~/.bashrc"
    else
        echo "⚠️  Alias non presenti in ~/.bashrc"
    fi
    unload-aliases
}

echo "✅ Alias CVRP caricati. Digita 'cvrp-help' per la lista comandi."
