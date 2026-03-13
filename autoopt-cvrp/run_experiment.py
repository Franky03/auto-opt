"""
run_experiment.py -- Orquestrador do loop agentic AutoOpt-CVRP.
Usa um modelo local via Ollama para propor melhorias na heuristica CVRP.

Uso: python run_experiment.py [--n-experiments N] [--time-limit T] [--model MODEL]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HEURISTIC_PY = os.path.join(SCRIPT_DIR, "heuristic.py")
PROGRAM_MD = os.path.join(SCRIPT_DIR, "program.md")
PREPARE_PY = os.path.join(SCRIPT_DIR, "prepare.py")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
LOG_FILE = os.path.join(RESULTS_DIR, "experiment_log.jsonl")

OLLAMA_URL = "http://localhost:11434/api/generate"

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def write_file(path: str, content: str):
    with open(path, "w") as f:
        f.write(content)


def ask_model(prompt: str, model: str = "qwen-reasoning") -> str:
    """Envia prompt ao Ollama e retorna a resposta."""
    import requests

    resp = requests.post(
        OLLAMA_URL,
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=600,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def extract_code(response: str) -> str | None:
    """Extrai codigo Python da resposta do modelo."""
    # Tenta blocos de codigo markdown
    for pat in [r"```python\s*\n(.*?)```", r"```\s*\n(.*?)```"]:
        match = re.search(pat, response, re.DOTALL)
        if match:
            return match.group(1).strip()

    # Se a resposta inteira parece ser codigo Python (comeca com docstring ou import)
    stripped = response.strip()
    if stripped.startswith('"""') or stripped.startswith("import ") or stripped.startswith("from "):
        return stripped

    return None


def git_commit(message: str):
    subprocess.run(["git", "add", HEURISTIC_PY, LOG_FILE], cwd=SCRIPT_DIR, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=SCRIPT_DIR, check=True)


def git_short_hash() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=SCRIPT_DIR, text=True
    ).strip()


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------

sys.path.insert(0, SCRIPT_DIR)
from bks import get_bks


def compute_score(result: dict, instance_name: str = None) -> float:
    """
    Metrica principal para comparacao entre experimentos.

    Se infeasible: distancia * (1 + violations/n_clientes) * 2
    Se feasible + BKS conhecido: gap percentual = (distancia/BKS) - 1
    Se feasible + sem BKS: distancia total (para instancias sinteticas)

    Em todos os casos: MENOR EH MELHOR.
    """
    if not result["feasible"]:
        n = result.get("n_customers", 50)
        return result["total_distance"] * (1 + result["violations"] / n) * 2

    bks = get_bks(instance_name) if instance_name else None
    if bks is not None:
        return (result["total_distance"] / bks) - 1  # gap percentual

    return result["total_distance"]


# ---------------------------------------------------------------------------
# Avaliacao
# ---------------------------------------------------------------------------


def _run_solve_with_timeout(heuristic_code: str, instance: dict, time_limit: float, timeout: float) -> dict:
    """
    Executa solve() num processo filho com timeout absoluto.
    Retorna {"solution": [...], "elapsed": float} ou {"error": str}.
    """
    import multiprocessing as mp

    def _worker(code, inst, tl, result_queue):
        try:
            # Cria modulo temporario
            import types
            mod = types.ModuleType("heuristic_tmp")
            # Importa prepare no namespace do modulo
            import prepare
            mod.__dict__["__builtins__"] = __builtins__
            exec("from prepare import *", mod.__dict__)
            exec(code, mod.__dict__)

            t0 = time.time()
            sol = mod.solve(inst, tl)
            elapsed = time.time() - t0
            result_queue.put({"solution": sol, "elapsed": elapsed})
        except Exception as e:
            result_queue.put({"error": f"{type(e).__name__}: {e}"})

    queue = mp.Queue()
    proc = mp.Process(target=_worker, args=(heuristic_code, instance, time_limit, queue))
    proc.start()
    proc.join(timeout=timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=5)
        if proc.is_alive():
            proc.kill()
            proc.join()
        return {"error": "timeout"}

    if queue.empty():
        return {"error": "processo terminou sem resultado"}

    return queue.get()


def evaluate_heuristic(time_limit: float) -> dict:
    """
    Avalia heuristic.py atual nas 10 instancias de benchmark.
    Retorna metricas agregadas.
    """
    sys.path.insert(0, SCRIPT_DIR)
    from prepare import get_benchmark_instances, evaluate_solution

    instances = get_benchmark_instances()
    heuristic_code = read_file(HEURISTIC_PY)

    # Validacao sintatica
    try:
        compile(heuristic_code, HEURISTIC_PY, "exec")
    except SyntaxError as e:
        return {
            "mean_score": float("inf"),
            "scores": [],
            "mean_distance": 0,
            "mean_vehicles": 0,
            "feasible_count": 0,
            "crashed": True,
            "crash_msg": f"SyntaxError: {e}",
        }

    scores = []
    distances = []
    vehicles = []
    feasible_count = 0
    crash_count = 0
    crash_msg = ""
    timeout = time_limit + 10

    for i, inst in enumerate(instances):
        result = _run_solve_with_timeout(heuristic_code, inst, time_limit, timeout)

        if "error" in result:
            crash_count += 1
            crash_msg = result["error"]
            # Penaliza crash com score alto
            scores.append(float("inf"))
            distances.append(0)
            vehicles.append(0)
            continue

        sol = result["solution"]
        metrics = evaluate_solution(sol, inst)
        scores.append(metrics["score"])
        distances.append(metrics["total_distance"])
        vehicles.append(metrics["n_vehicles"])
        if metrics["feasible"]:
            feasible_count += 1

    # Se crashou mais de 3 instancias, marca como crash total
    crashed = crash_count > 3

    # Score medio (infinito se houve crashes)
    finite_scores = [s for s in scores if s < float("inf")]
    if finite_scores and not crashed:
        mean_score = sum(scores) / len(scores) if all(s < float("inf") for s in scores) else float("inf")
    else:
        mean_score = float("inf")

    return {
        "mean_score": mean_score,
        "scores": scores,
        "mean_distance": sum(distances) / max(len(distances), 1),
        "mean_vehicles": sum(vehicles) / max(len(vehicles), 1),
        "feasible_count": feasible_count,
        "crashed": crashed,
        "crash_msg": crash_msg,
    }


# ---------------------------------------------------------------------------
# Prompt do agente
# ---------------------------------------------------------------------------


def build_agent_prompt(current_code: str, program_md: str, prepare_py: str,
                       history: list, current_scores: dict) -> str:
    """Monta o prompt completo para o agente."""
    if history:
        history_str = "\n".join([
            f"  Exp {h['id']}: score {h['score_after']:.2f} | "
            f"{'ACEITO' if h['accepted'] else 'REVERTIDO'} | {h['description']}"
            for h in history[-5:]
        ])
    else:
        history_str = "  (nenhum experimento anterior)"

    scores_str = ""
    if current_scores.get("scores"):
        for i, s in enumerate(current_scores["scores"]):
            scores_str += f"  Instancia {i}: {s:.2f}\n"
    else:
        scores_str = "  (sem scores ainda)"

    return f"""Voce eh um pesquisador especialista em Pesquisa Operacional e algoritmos de otimizacao combinatoria.
Sua tarefa eh melhorar a heuristica CVRP abaixo.

## Diretrizes de pesquisa

{program_md}

## Referencia: prepare.py (NAO MODIFIQUE -- apenas para consulta)

```python
{prepare_py}
```

## Historico recente (ultimos 5 experimentos)

{history_str}

## Score atual por instancia (menor eh melhor)

{scores_str}
Score medio atual: {current_scores['mean_score']:.2f}
Instancias feasiveis: {current_scores['feasible_count']}/10

## Codigo atual de heuristic.py

```python
{current_code}
```

## Instrucao

Faca UMA modificacao especifica e bem definida para tentar reduzir o score medio.
Pense passo a passo sobre qual mudanca tem mais chance de melhorar o resultado
dado o historico acima.

Retorne o codigo Python completo e funcional do novo heuristic.py dentro de um bloco ```python.
A primeira linha do arquivo deve ser a docstring descrevendo a geracao atual e o que foi mudado.
"""


def build_fix_prompt(current_code: str, error_msg: str) -> str:
    """Prompt para corrigir um crash."""
    return f"""O codigo heuristic.py crashou com o seguinte erro:

{error_msg}

Codigo atual:
```python
{current_code}
```

Corrija o erro e retorne o codigo Python completo e funcional dentro de um bloco ```python.
Nao mude a logica principal -- apenas corrija o bug.
"""


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------


def load_history() -> list:
    """Carrega historico de experimentos do log."""
    if not os.path.exists(LOG_FILE):
        return []
    history = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                history.append(json.loads(line))
    return history


def append_log(entry: dict):
    """Adiciona entrada ao log."""
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_loop(n_experiments: int, time_limit: float, model: str):
    """Loop principal de experimentacao."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    program_md = read_file(PROGRAM_MD)
    prepare_py = read_file(PREPARE_PY)
    history = load_history()

    # Determina proximo ID
    next_id = max((h["id"] for h in history), default=0) + 1

    # Avalia versao atual como baseline
    print("[autoopt] Avaliando heuristica atual...")
    baseline = evaluate_heuristic(time_limit)

    if baseline["crashed"]:
        print(f"[autoopt] ERRO: heuristica atual crasha! {baseline['crash_msg']}")
        print("[autoopt] Corrija heuristic.py antes de iniciar o loop.")
        sys.exit(1)

    best_score = baseline["mean_score"]
    print(f"[autoopt] Score baseline: {best_score:.2f}")
    print(f"[autoopt] Feasiveis: {baseline['feasible_count']}/10")
    print(f"[autoopt] Scores: {[f'{s:.1f}' for s in baseline['scores']]}")

    for exp_num in range(n_experiments):
        exp_id = next_id + exp_num

        print(f"\n{'='*60}")
        print(f"[autoopt] Experimento #{exp_id}")
        print(f"{'='*60}")

        current_code = read_file(HEURISTIC_PY)
        backup_code = current_code

        # Pede proposta ao modelo
        print(f"[autoopt] Pedindo proposta ao {model}...")
        prompt = build_agent_prompt(current_code, program_md, prepare_py, history, baseline)

        max_attempts = 3
        accepted = False
        description = "unknown"
        score_after = float("inf")

        for attempt in range(1, max_attempts + 1):
            try:
                response = ask_model(prompt, model=model)
            except Exception as e:
                print(f"[autoopt] Erro na comunicacao com Ollama: {e}")
                if attempt < max_attempts:
                    print(f"[autoopt] Tentativa {attempt}/{max_attempts}, aguardando 30s...")
                    time.sleep(30)
                    continue
                else:
                    print("[autoopt] Falha na comunicacao. Pulando experimento.")
                    break

            new_code = extract_code(response)
            if not new_code:
                print(f"[autoopt] Nao consegui extrair codigo da resposta (tentativa {attempt})")
                if attempt < max_attempts:
                    continue
                break

            # Extrai descricao da docstring
            doc_match = re.search(r'"""(.*?)"""', new_code, re.DOTALL)
            if doc_match:
                doc_lines = doc_match.group(1).strip().split("\n")
                description = doc_lines[0].strip() if doc_lines else "sem descricao"
            else:
                # Tenta primeira linha de comentario
                first_lines = [l.strip() for l in new_code.split("\n") if l.strip().startswith("#")]
                description = first_lines[0].lstrip("# ") if first_lines else "sem descricao"

            description = description[:120]
            print(f"[autoopt] Proposta: {description}")

            # Valida sintaxe
            try:
                compile(new_code, "heuristic.py", "exec")
            except SyntaxError as e:
                print(f"[autoopt] SyntaxError: {e}")
                if attempt < max_attempts:
                    prompt = build_fix_prompt(new_code, str(e))
                    continue
                break

            # Verifica que solve() existe
            if "def solve(" not in new_code:
                print("[autoopt] Codigo nao contem def solve(). Rejeitado.")
                if attempt < max_attempts:
                    continue
                break

            # Aplica e avalia
            write_file(HEURISTIC_PY, new_code)
            print("[autoopt] Avaliando nova versao...")
            result = evaluate_heuristic(time_limit)

            if result["crashed"]:
                print(f"[autoopt] CRASH: {result['crash_msg']}")
                write_file(HEURISTIC_PY, backup_code)
                if attempt < max_attempts:
                    prompt = build_fix_prompt(new_code, result["crash_msg"])
                    continue
                break

            score_after = result["mean_score"]
            print(f"[autoopt] Score: {score_after:.2f} (antes: {best_score:.2f})")
            print(f"[autoopt] Feasiveis: {result['feasible_count']}/10")

            if score_after < best_score:
                improvement = (best_score - score_after) / best_score * 100
                print(f"[autoopt] MELHORIA! -{improvement:.1f}%")

                # Aceita
                accepted = True
                entry = {
                    "id": exp_id,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "accepted": True,
                    "score_before": round(best_score, 4),
                    "score_after": round(score_after, 4),
                    "improvement_pct": round(improvement, 2),
                    "feasible_count": result["feasible_count"],
                    "description": description,
                    "crash": False,
                }
                append_log(entry)
                history.append(entry)

                # Git commit
                commit_msg = f"exp#{exp_id}: score {best_score:.1f} -> {score_after:.1f} ({improvement:+.1f}%)"
                try:
                    git_commit(commit_msg)
                    print(f"[autoopt] Commit: {commit_msg}")
                except Exception as e:
                    print(f"[autoopt] Aviso: git commit falhou: {e}")

                best_score = score_after
                baseline = result
                break
            else:
                print(f"[autoopt] Sem melhoria. Revertendo.")
                write_file(HEURISTIC_PY, backup_code)
                break

        if not accepted:
            entry = {
                "id": exp_id,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "accepted": False,
                "score_before": round(best_score, 4),
                "score_after": round(score_after, 4) if score_after < float("inf") else 0,
                "improvement_pct": 0,
                "feasible_count": baseline["feasible_count"],
                "description": description,
                "crash": score_after == float("inf"),
            }
            append_log(entry)
            history.append(entry)

    print(f"\n[autoopt] Finalizado. Melhor score: {best_score:.2f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoOpt-CVRP: loop agentic de otimizacao")
    parser.add_argument("--n-experiments", type=int, default=100, help="Numero de experimentos (default: 100)")
    parser.add_argument("--time-limit", type=float, default=30.0, help="Tempo limite por instancia em segundos (default: 30)")
    parser.add_argument("--model", default="qwen-reasoning", help="Modelo Ollama (default: qwen-reasoning)")
    args = parser.parse_args()

    print(f"[autoopt] Modelo: {args.model}")
    print(f"[autoopt] Experimentos: {args.n_experiments}")
    print(f"[autoopt] Time limit: {args.time_limit}s por instancia")
    print()

    run_loop(args.n_experiments, args.time_limit, args.model)
