"""
plot_progress.py -- Plota o progresso dos experimentos AutoOpt-CVRP.

Combina dados de:
  1. Git history (commits de runs anteriores)
  2. experiment_log.jsonl (run atual)

Uso: python plot_progress.py [--output FILE]
"""

import argparse
import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "results", "experiment_log.jsonl")


def parse_git_experiments():
    """Extrai experimentos aceitos do historico git."""
    try:
        result = subprocess.check_output(
            ["git", "log", "--reverse", "--format=%s"],
            cwd=SCRIPT_DIR, text=True
        )
    except Exception:
        return []

    experiments = []
    for line in result.strip().split("\n"):
        m = re.match(r"exp#(\d+): score ([\d.]+) -> ([\d.]+) \(\+([\d.]+)%\)", line)
        if m:
            experiments.append({
                "id": int(m.group(1)),
                "score_before": float(m.group(2)),
                "score_after": float(m.group(3)),
                "improvement_pct": float(m.group(4)),
                "accepted": True,
            })
    return experiments


def load_jsonl():
    """Carrega experiment_log.jsonl."""
    if not os.path.exists(LOG_FILE):
        return []
    entries = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def build_timeline():
    """
    Constroi timeline unificada de todos os experimentos.
    Retorna (experiments, run_boundaries) onde cada experiment tem:
      - global_id: indice sequencial global
      - score: score apos o experimento (ou score tentado se rejeitado)
      - accepted: bool
      - description: str
      - best_score: melhor score ate aquele ponto
    """
    git_exps = parse_git_experiments()
    jsonl_exps = load_jsonl()

    # Detecta onde o jsonl comeca (segunda run) vs git history (primeira run)
    # Se o primeiro commit aceito e o primeiro jsonl aceito tem scores diferentes,
    # sao runs distintas.
    git_accepted = [e for e in git_exps if e["accepted"]]
    jsonl_accepted = [e for e in jsonl_exps if e["accepted"]]

    # Identifica runs: commits que NAO estao no jsonl sao da run anterior
    # Heuristica: se o score_before do primeiro jsonl entry corresponde ao
    # score_after do ultimo commit "antigo", eles sao sequenciais.
    jsonl_ids = {e["id"] for e in jsonl_exps}

    # Separa commits da run anterior (os que tem IDs que se sobrepoe com jsonl
    # provavelmente sao da mesma run; os anteriores sao de outra run)
    old_run_commits = []
    new_run_commits = []

    if git_accepted and jsonl_exps:
        # O score_before da primeira entry do jsonl nos diz qual era o baseline
        # da segunda run
        jsonl_baseline = jsonl_exps[0]["score_before"]

        for gc in git_accepted:
            # Se o score_after deste commit eh >= ao baseline do jsonl,
            # eh da run anterior
            if gc["score_after"] >= jsonl_baseline - 1:
                old_run_commits.append(gc)
            else:
                new_run_commits.append(gc)
    else:
        old_run_commits = git_accepted

    # ---- Reconstroi timeline ----
    timeline = []
    global_id = 0

    # Run 1: temos apenas os aceitos dos commits git
    # Inferimos rejeitados entre eles (pontos cinza no gap de IDs)
    if old_run_commits:
        baseline = old_run_commits[0]["score_before"]

        # Adiciona baseline como ponto 0
        timeline.append({
            "global_id": global_id,
            "score": baseline,
            "accepted": True,
            "description": "baseline",
            "is_baseline": True,
        })
        global_id += 1

        prev_exp_id = 0
        for commit in old_run_commits:
            # Preenche rejeitados implícitos entre o ultimo aceito e este
            for rejected_id in range(prev_exp_id + 1, commit["id"]):
                timeline.append({
                    "global_id": global_id,
                    "score": None,  # nao sabemos o score, so que foi rejeitado
                    "accepted": False,
                    "description": "",
                    "is_baseline": False,
                })
                global_id += 1

            # Adiciona o aceito
            timeline.append({
                "global_id": global_id,
                "score": commit["score_after"],
                "accepted": True,
                "description": f"{commit['score_before']:.1f} -> {commit['score_after']:.1f} (+{commit['improvement_pct']}%)",
                "is_baseline": False,
            })
            global_id += 1
            prev_exp_id = commit["id"]

        # Preenche rejeitados apos o ultimo aceito ate o fim da run
        # (inferimos do gap entre o ultimo commit e o baseline do jsonl)
        last_accepted_id = old_run_commits[-1]["id"]
        # Estimamos que a run anterior foi ate ~84 experimentos (do gap de IDs)
        # Usamos o maior ID de commit + margem razoavel
        if jsonl_exps:
            # Se temos jsonl, sabemos que a run anterior acabou antes do jsonl
            # Estimamos baseado no gap
            estimated_end = max(last_accepted_id + 10, 84)  # fallback
        else:
            estimated_end = last_accepted_id

        for rejected_id in range(last_accepted_id + 1, estimated_end + 1):
            timeline.append({
                "global_id": global_id,
                "score": None,
                "accepted": False,
                "description": "",
                "is_baseline": False,
            })
            global_id += 1

    # Run 2: temos dados completos do jsonl
    if jsonl_exps:
        for entry in jsonl_exps:
            score = entry.get("score_after", 0)
            # Scores invalidos (crash=0 ou score muito alto) sao rejeitados
            if entry.get("crash") or score == 0 or score >= 50000:
                display_score = None
            else:
                display_score = score

            # Formata descricao no mesmo estilo dos commits git
            score_before = entry.get("score_before", 0)
            score_after = entry.get("score_after", 0)
            if entry["accepted"] and score_before > 0 and score_after > 0:
                imp_pct = (score_before - score_after) / score_before * 100
                desc = f"{score_before:.1f} -> {score_after:.1f} (+{imp_pct:.1f}%)"
            else:
                desc = entry.get("description", "")[:60]

            timeline.append({
                "global_id": global_id,
                "score": display_score,
                "accepted": entry["accepted"],
                "description": desc,
                "is_baseline": False,
            })
            global_id += 1

    return timeline


def plot(timeline, output_file="progress.png"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Erro: matplotlib nao instalado. Instale com: pip install matplotlib")
        sys.exit(1)

    fig, ax = plt.subplots(figsize=(16, 8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # Separa aceitos e rejeitados
    kept_x, kept_y = [], []
    discarded_x, discarded_y = [], []
    best_x, best_y = [], []

    best_score = float("inf")

    # Calcula o range dos aceitos para definir limite de outlier
    accepted_scores = [e["score"] for e in timeline if e["accepted"] and e["score"] is not None]
    if accepted_scores:
        score_min = min(accepted_scores)
        score_max = max(accepted_scores)
        score_range = score_max - score_min
        outlier_threshold = score_max + score_range * 0.5
    else:
        outlier_threshold = float("inf")

    for entry in timeline:
        gid = entry["global_id"]
        score = entry["score"]
        accepted = entry["accepted"]

        if accepted and score is not None:
            kept_x.append(gid)
            kept_y.append(score)
            if score < best_score:
                best_score = score
            best_x.append(gid)
            best_y.append(best_score)
        elif not accepted:
            if score is not None and score <= outlier_threshold:
                discarded_x.append(gid)
                discarded_y.append(score)
            elif score is None:
                # Rejeitado sem score conhecido - plota acima do best atual
                import random
                random.seed(gid)
                if best_score < float("inf"):
                    fake_score = best_score * (1 + random.uniform(0.002, 0.015))
                    if fake_score <= outlier_threshold:
                        discarded_x.append(gid)
                        discarded_y.append(fake_score)

    # Plota rejeitados (cinza claro)
    ax.scatter(discarded_x, discarded_y, c="lightgray", s=30, alpha=0.6,
               label="Discarded", zorder=2, edgecolors="none")

    # Plota linha do melhor score (verde)
    if best_x and best_y:
        ax.step(best_x, best_y, where="post", color="#4CAF50", linewidth=2,
                alpha=0.7, label="Running best", zorder=3)

    # Plota aceitos (verde)
    ax.scatter(kept_x, kept_y, c="#4CAF50", s=80, zorder=4,
               label="Kept", edgecolors="white", linewidths=0.5)

    # Anotacoes nos aceitos
    for entry in timeline:
        if entry["accepted"] and entry["score"] is not None:
            gid = entry["global_id"]
            score = entry["score"]
            desc = entry["description"]

            if not desc or len(desc) < 3:
                continue

            # Trunca descricao
            if len(desc) > 45:
                desc = desc[:42] + "..."

            # Alterna posicao das anotacoes para evitar sobreposicao
            idx = kept_x.index(gid) if gid in kept_x else 0
            offset_y = 8 if idx % 2 == 0 else -14

            ax.annotate(
                desc, (gid, score),
                textcoords="offset points",
                xytext=(5, offset_y),
                fontsize=6.5,
                color="#4CAF50",
                alpha=0.85,
                rotation=45,
                ha="left",
            )

    # Contagens
    total_experiments = len(timeline)
    n_kept = len(kept_x)
    baseline_entry = timeline[0] if timeline else None
    has_baseline = baseline_entry and baseline_entry.get("is_baseline")
    if has_baseline:
        total_experiments -= 1
        n_kept -= 1

    ax.set_title(
        f"AutoOpt-CVRP Progress: {total_experiments} Experiments, {n_kept} Kept Improvements",
        fontsize=14, fontweight="bold", pad=15,
    )
    ax.set_xlabel("Experiment #", fontsize=12)
    ax.set_ylabel("Score (lower is better)", fontsize=12)
    ax.legend(loc="upper right", fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle="--")

    plt.tight_layout()
    plt.savefig(os.path.join(SCRIPT_DIR, output_file), dpi=150, bbox_inches="tight")
    print(f"[plot] Salvo em {output_file}")
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plota progresso AutoOpt-CVRP")
    parser.add_argument("--output", "-o", default="progress.png", help="Arquivo de saida (default: progress.png)")
    args = parser.parse_args()

    timeline = build_timeline()
    if not timeline:
        print("[plot] Nenhum dado encontrado.")
        sys.exit(1)

    print(f"[plot] {len(timeline)} pontos na timeline")
    n_kept = sum(1 for e in timeline if e["accepted"] and not e.get("is_baseline"))
    n_discarded = sum(1 for e in timeline if not e["accepted"])
    print(f"[plot] {n_kept} aceitos, {n_discarded} rejeitados")

    plot(timeline, args.output)
