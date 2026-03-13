"""
prepare.py -- Gerador de instancias CVRP e utilitarios de avaliacao.
FIXO: este arquivo NAO deve ser modificado pelo agente.
"""

import glob
import math
import os
import random
import re

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

BENCHMARK_N = 50          # clientes por instancia sintetica
BENCHMARK_SEEDS = range(10)  # seeds 0..9
TIME_LIMIT_DEFAULT = 30   # segundos por instancia

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------


def euclidean_distance(p1: tuple, p2: tuple) -> float:
    """Distancia euclidiana entre dois pontos."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def route_distance(route: list, coords_all: list) -> float:
    """Distancia total de uma unica rota (lista de indices, comeca e termina em 0)."""
    dist = 0.0
    for i in range(len(route) - 1):
        dist += euclidean_distance(coords_all[route[i]], coords_all[route[i + 1]])
    return dist


# ---------------------------------------------------------------------------
# Geracao de instancias sinteticas
# ---------------------------------------------------------------------------


def generate_instance(n: int, seed: int) -> dict:
    """
    Gera instancia CVRP aleatoria com n clientes.
    Coordenadas em [0, 100] x [0, 100], demandas em [1, 10].
    Capacidade = max(30, ceil(sum(demands) / (n / 5))).
    """
    rng = random.Random(seed)
    depot = (rng.uniform(0, 100), rng.uniform(0, 100))
    coords = [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(n)]
    demands = [rng.randint(1, 10) for _ in range(n)]
    total_demand = sum(demands)
    capacity = max(30, math.ceil(total_demand / (n / 5)))
    return {
        "name": f"synthetic_n{n}_s{seed}",
        "n": n,
        "capacity": capacity,
        "depot": depot,
        "coords": coords,
        "demands": demands,
        "optimal": None,
    }


# ---------------------------------------------------------------------------
# Leitor de instancias CVRPLIB
# ---------------------------------------------------------------------------


def load_cvrplib(filepath: str) -> dict:
    """
    Carrega instancia no formato CVRPLIB/TSPLIB (.vrp).

    Suporta as secoes:
    - NAME, COMMENT, TYPE, DIMENSION, CAPACITY
    - NODE_COORD_SECTION
    - DEMAND_SECTION
    - DEPOT_SECTION

    Retorna dict no formato padrao do sistema.
    Levanta ValueError se o arquivo estiver malformado.
    """
    with open(filepath, "r") as f:
        text = f.read()

    # Nome da instancia
    name_match = re.search(r"NAME\s*:\s*(.+)", text)
    name = name_match.group(1).strip() if name_match else os.path.splitext(os.path.basename(filepath))[0]

    # Dimension
    dim_match = re.search(r"DIMENSION\s*:\s*(\d+)", text)
    if not dim_match:
        raise ValueError(f"DIMENSION nao encontrado em {filepath}")
    dimension = int(dim_match.group(1))

    # Capacity
    cap_match = re.search(r"CAPACITY\s*:\s*(\d+)", text)
    if not cap_match:
        raise ValueError(f"CAPACITY nao encontrado em {filepath}")
    capacity = int(cap_match.group(1))

    # Node coords
    coords_section = re.search(
        r"NODE_COORD_SECTION\s*\n(.*?)(?:DEMAND_SECTION|DEPOT_SECTION|EOF)", text, re.DOTALL
    )
    if not coords_section:
        raise ValueError(f"NODE_COORD_SECTION nao encontrado em {filepath}")
    all_coords = {}
    for line in coords_section.group(1).strip().split("\n"):
        parts = line.split()
        if len(parts) >= 3:
            node_id = int(parts[0])
            all_coords[node_id] = (float(parts[1]), float(parts[2]))

    if len(all_coords) != dimension:
        raise ValueError(f"Esperado {dimension} nos, encontrado {len(all_coords)} em {filepath}")

    # Demands
    demand_section = re.search(
        r"DEMAND_SECTION\s*\n(.*?)(?:DEPOT_SECTION|EOF)", text, re.DOTALL
    )
    if not demand_section:
        raise ValueError(f"DEMAND_SECTION nao encontrado em {filepath}")
    all_demands = {}
    for line in demand_section.group(1).strip().split("\n"):
        parts = line.split()
        if len(parts) >= 2:
            node_id = int(parts[0])
            all_demands[node_id] = int(parts[1])

    # Depot
    depot_section = re.search(r"DEPOT_SECTION\s*\n(.*?)(?:EOF|\-1)", text, re.DOTALL)
    if depot_section:
        depot_line = depot_section.group(1).strip().split("\n")[0].strip()
        depot_id = int(depot_line)
    else:
        depot_id = 1  # default: primeiro no

    # Monta resultado separando deposito dos clientes
    depot = all_coords[depot_id]
    client_ids = sorted(nid for nid in all_coords if nid != depot_id)
    coords = [all_coords[nid] for nid in client_ids]
    demands = [all_demands[nid] for nid in client_ids]

    return {
        "name": name,
        "n": len(coords),
        "capacity": capacity,
        "depot": depot,
        "coords": coords,
        "demands": demands,
        "optimal": None,
    }


# ---------------------------------------------------------------------------
# Avaliacao
# ---------------------------------------------------------------------------


def evaluate_solution(solution: list, instance: dict) -> dict:
    """
    Avalia uma solucao CVRP.
    Retorna metricas: total_distance, n_vehicles, feasible, violations, score.

    Penalidade de infeasibility: score = total_distance * (1 + violations/n) * 2
    """
    depot = instance["depot"]
    coords = instance["coords"]
    demands = instance["demands"]
    capacity = instance["capacity"]
    n = instance["n"]

    # coords com deposito no indice 0
    coords_all = [depot] + coords
    demands_all = [0] + demands

    total_distance = 0.0
    n_vehicles = len(solution)
    violations = 0
    visited = set()

    for route in solution:
        # Verifica formato da rota
        if not route or route[0] != 0 or route[-1] != 0:
            violations += 1
            continue

        route_load = 0
        for i in range(len(route) - 1):
            a, b = route[i], route[i + 1]
            if a < 0 or a > n or b < 0 or b > n:
                violations += 1
                continue
            total_distance += euclidean_distance(coords_all[a], coords_all[b])

        for node in route[1:-1]:
            if node < 1 or node > n:
                violations += 1
                continue
            route_load += demands_all[node]
            visited.add(node)

        if route_load > capacity:
            violations += 1

    # Verifica se todos os clientes foram visitados
    missing = set(range(1, n + 1)) - visited
    violations += len(missing)

    feasible = violations == 0

    if feasible:
        score = total_distance
    else:
        score = total_distance * (1 + violations / n) * 2
        # Penaliza fortemente clientes nao visitados
        if missing:
            score += len(missing) * 1000

    return {
        "total_distance": round(total_distance, 4),
        "n_vehicles": n_vehicles,
        "feasible": feasible,
        "violations": violations,
        "score": round(score, 4),
    }


# ============================================================
# DIVISAO OFICIAL DE INSTANCIAS
# ============================================================

# TREINO -- usadas pelo agente durante o loop overnight
# Instancias sinteticas rapidas (n=50) para evolucao da heuristica
TRAIN_INSTANCES = [generate_instance(BENCHMARK_N, seed) for seed in BENCHMARK_SEEDS]

# Alias para compatibilidade
BENCHMARK_INSTANCES = TRAIN_INSTANCES

# BENCHMARK PRINCIPAL -- avaliacao apos treino, reportado no paper
# Augerat Set A completo (27 instancias)
BENCHMARK_A_PATH = os.path.join(SCRIPT_DIR, "instances", "augerat_a")

# HELD-OUT -- o agente NUNCA ve estas durante o desenvolvimento
# Augerat Set B completo (23 instancias)
HELDOUT_B_PATH = os.path.join(SCRIPT_DIR, "instances", "augerat_b")

# BENCHMARK DE ESCALA -- mostra que a heuristica escala
BENCHMARK_GOLDEN_PATH = os.path.join(SCRIPT_DIR, "instances", "golden")
BENCHMARK_GOLDEN_SUBSET = [f"Golden_{i}.vrp" for i in range(1, 11)]

# BENCHMARK CLASSICO -- conecta com literatura fundacional
BENCHMARK_CMT_PATH = os.path.join(SCRIPT_DIR, "instances", "christofides")


def get_benchmark_instances() -> list:
    """Retorna as 10 instancias sinteticas fixas de benchmark (treino)."""
    return TRAIN_INSTANCES


def load_instance_set(instance_set: str) -> list[dict]:
    """
    Carrega um conjunto de instancias por nome.
    instance_set: "train" | "benchmark_a" | "heldout_b" | "cmt" | "golden"
    Retorna lista de dicts no formato padrao.
    """
    if instance_set == "train":
        return list(TRAIN_INSTANCES)

    path_map = {
        "benchmark_a": BENCHMARK_A_PATH,
        "heldout_b": HELDOUT_B_PATH,
        "cmt": BENCHMARK_CMT_PATH,
        "golden": BENCHMARK_GOLDEN_PATH,
    }

    path = path_map.get(instance_set)
    if not path or not os.path.isdir(path):
        raise FileNotFoundError(f"Pasta de instancias nao encontrada: {path}")

    vrp_files = sorted(glob.glob(os.path.join(path, "*.vrp")))
    if not vrp_files:
        raise FileNotFoundError(f"Nenhum arquivo .vrp em {path}")

    if instance_set == "golden":
        # Apenas subset definido
        subset_names = set(BENCHMARK_GOLDEN_SUBSET)
        vrp_files = [f for f in vrp_files if os.path.basename(f) in subset_names]

    instances = []
    for fpath in vrp_files:
        try:
            inst = load_cvrplib(fpath)
            instances.append(inst)
        except (ValueError, Exception) as e:
            print(f"  Aviso: erro ao carregar {fpath}: {e}")

    return instances


# ---------------------------------------------------------------------------
# Main -- testa a geracao
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Gerando instancias sinteticas de benchmark...")
    for i, inst in enumerate(TRAIN_INSTANCES):
        total_demand = sum(inst["demands"])
        print(f"  Instancia {i} (seed {i}): {inst['n']} clientes, "
              f"capacidade={inst['capacity']}, demanda_total={total_demand}")
    print(f"\n{len(TRAIN_INSTANCES)} instancias geradas com sucesso.")

    # Testa conjuntos reais se disponiveis
    for name in ["benchmark_a", "heldout_b", "cmt", "golden"]:
        try:
            insts = load_instance_set(name)
            print(f"\n{name}: {len(insts)} instancias carregadas")
        except FileNotFoundError:
            print(f"\n{name}: nao disponivel (rode download_instances.py)")
