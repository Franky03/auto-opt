"""
evaluate_final.py -- Avalia a heuristica final em todos os benchmarks.
Gera tabela completa para o paper cientifico.
Uso: python evaluate_final.py [--time-limit T]
"""

import argparse
import csv
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from bks import get_bks
from prepare import evaluate_solution, load_instance_set


def evaluate_instance(solve_fn, instance, time_limit):
    """Avalia uma unica instancia. Retorna dict com metricas."""
    name = instance.get("name", "unknown")
    try:
        t0 = time.time()
        solution = solve_fn(instance, time_limit)
        elapsed = time.time() - t0
        result = evaluate_solution(solution, instance)
        bks = get_bks(name)
        gap = ((result["total_distance"] / bks) - 1) * 100 if bks else None
        return {
            "name": name,
            "distance": result["total_distance"],
            "bks": bks,
            "gap_pct": gap,
            "n_vehicles": result["n_vehicles"],
            "elapsed": elapsed,
            "feasible": result["feasible"],
            "score": result["score"],
            "error": None,
        }
    except Exception as e:
        return {
            "name": name,
            "distance": 0,
            "bks": get_bks(name),
            "gap_pct": None,
            "n_vehicles": 0,
            "elapsed": 0,
            "feasible": False,
            "score": float("inf"),
            "error": str(e),
        }


def print_table(results, set_name):
    """Imprime tabela formatada no terminal."""
    print(f"\n{'='*85}")
    print(f" {set_name}")
    print(f"{'='*85}")
    print(f"{'Instancia':<16} | {'Distancia':>10} | {'BKS':>8} | {'Gap%':>7} | {'Veic':>4} | {'Tempo':>7} | {'OK':>3}")
    print(f"{'-'*85}")

    gaps = []
    feasible_count = 0
    total_elapsed = 0

    for r in results:
        if r["error"]:
            print(f"{r['name']:<16} | {'ERRO':>10} | {'-':>8} | {'-':>7} | {'-':>4} | {'-':>7} | {'X':>3}")
            continue

        dist_str = f"{r['distance']:.1f}"
        bks_str = f"{r['bks']:.0f}" if r['bks'] else "-"
        gap_str = f"{r['gap_pct']:.2f}%" if r['gap_pct'] is not None else "-"
        time_str = f"{r['elapsed']:.1f}s"
        ok_str = "V" if r['feasible'] else "X"

        print(f"{r['name']:<16} | {dist_str:>10} | {bks_str:>8} | {gap_str:>7} | {r['n_vehicles']:>4} | {time_str:>7} | {ok_str:>3}")

        if r['gap_pct'] is not None:
            gaps.append(r['gap_pct'])
        if r['feasible']:
            feasible_count += 1
        total_elapsed += r['elapsed']

    print(f"{'-'*85}")
    mean_gap = sum(gaps) / len(gaps) if gaps else 0
    avg_time = total_elapsed / len(results) if results else 0
    print(f"{'MEDIA':<16} | {'-':>10} | {'-':>8} | {mean_gap:>6.2f}% | {'-':>4} | {avg_time:>6.1f}s | {feasible_count}/{len(results)}")

    return gaps, feasible_count


def main():
    parser = argparse.ArgumentParser(description="Avaliacao final da heuristica CVRP")
    parser.add_argument("--time-limit", type=float, default=30.0, help="Tempo limite por instancia (default: 30)")
    args = parser.parse_args()

    # Importa heuristica
    from heuristic import solve

    results_dir = os.path.join(SCRIPT_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)
    csv_path = os.path.join(results_dir, "final_evaluation.csv")

    all_results = []

    # Conjuntos de benchmark (exceto held-out)
    BENCHMARK_SETS = [
        ("train",       "Sinteticas (Treino)",          "treino"),
        ("benchmark_a", "Augerat Set A",                "benchmark principal"),
        ("benchmark_p", "Augerat Set P",                "benchmark secundario"),
        ("eilon_e",     "Eilon E",                      "benchmark historico"),
    ]

    HELDOUT_SET = ("heldout_b", "Augerat B (held-out)")

    # Avalia benchmarks principais
    for set_key, set_label, _role in BENCHMARK_SETS:
        try:
            instances = load_instance_set(set_key)
        except FileNotFoundError:
            print(f"\n[!] {set_label}: nao disponivel (rode download_instances.py)")
            continue

        print(f"\nAvaliando {set_label} ({len(instances)} instancias)...")
        results = []
        for inst in instances:
            r = evaluate_instance(solve, inst, args.time_limit)
            results.append(r)
            all_results.append({**r, "set": set_key})

        print_table(results, set_label)

    # Avalia held-out separadamente
    heldout_key, heldout_label = HELDOUT_SET
    try:
        instances = load_instance_set(heldout_key)
        print(f"\n{'='*85}")
        print(f" === HELD-OUT (Augerat B) — agente nunca viu estas instancias ===")
        print(f"\nAvaliando {heldout_label} ({len(instances)} instancias)...")
        results = []
        for inst in instances:
            r = evaluate_instance(solve, inst, args.time_limit)
            results.append(r)
            all_results.append({**r, "set": heldout_key})

        print_table(results, heldout_label)
    except FileNotFoundError:
        print(f"\n[!] {heldout_label}: nao disponivel (rode download_instances.py)")

    # Salva CSV
    if all_results:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "set", "name", "distance", "bks", "gap_pct",
                "n_vehicles", "elapsed", "feasible", "score", "error"
            ])
            writer.writeheader()
            writer.writerows(all_results)
        print(f"\nResultados salvos em {csv_path}")


if __name__ == "__main__":
    main()
