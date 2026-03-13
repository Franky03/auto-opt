"""
Heuristica CVRP -- Geracao 1
Algoritmo: Nearest Neighbor Greedy + 2-opt intra-rota
Descricao: Constroi rotas com Nearest Neighbor, depois aplica 2-opt em cada rota
           para melhorar a sequencia de visitas dentro de cada rota.
"""

import time as _time
import math as _math

from prepare import euclidean_distance


def solve(instance: dict, time_limit: float = 30.0) -> list:
    """
    Resolve a instancia CVRP e retorna uma lista de rotas.

    REGRAS QUE O AGENTE DEVE SEMPRE RESPEITAR:
    - Esta funcao deve sempre se chamar solve(instance, time_limit)
    - Deve sempre retornar uma lista de rotas no formato [[0,...,0], ...]
    - Deve respeitar o time_limit em segundos
    - Pode importar apenas: prepare, math, random, time, copy, itertools, collections
    - NAO pode usar bibliotecas externas (OR-Tools, networkx, scipy, etc.)
    """
    t_start = _time.time()
    n = instance["n"]
    capacity = instance["capacity"]
    depot = instance["depot"]
    coords = [depot] + instance["coords"]  # no 0 = deposito
    demands = [0] + instance["demands"]    # demanda 0 do deposito

    # ============ FASE 1: Construcao com Nearest Neighbor ============
    unvisited = set(range(1, n + 1))
    routes = []

    while unvisited:
        route = [0]
        load = 0
        current = 0

        while True:
            # encontra o cliente nao visitado mais proximo que cabe
            best = None
            best_dist = float("inf")
            for c in unvisited:
                if load + demands[c] <= capacity:
                    d = euclidean_distance(coords[current], coords[c])
                    if d < best_dist:
                        best_dist = d
                        best = c

            if best is None:
                break  # nenhum cliente cabe -- fecha a rota

            route.append(best)
            load += demands[best]
            unvisited.remove(best)
            current = best

        route.append(0)  # retorna ao deposito
        routes.append(route)

    # ============ FASE 2: Melhoria 2-opt intra-rota ============
    def two_opt(route: list, coords: list) -> list:
        """Aplica 2-opt em uma rota para melhorar a sequencia."""
        improved = True
        while improved:
            improved = False
            # uma rota [0, c1, c2, ..., ck, 0] tem k+1 arestas
            # tentamos trocar arestas (i, i+1) e (j, j+1) por (i, j) e (i+1, j+1)
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    # arestas atuais: (route[i], route[i+1]) e (route[j], route[j+1])
                    # arestas novas:  (route[i], route[j]) e (route[i+1], route[j+1])
                    a, b = route[i], route[i + 1]
                    c, d = route[j], route[j + 1]
                    
                    dist_atual = euclidean_distance(coords[a], coords[b]) + euclidean_distance(coords[c], coords[d])
                    dist_nova = euclidean_distance(coords[a], coords[c]) + euclidean_distance(coords[b], coords[d])
                    
                    if dist_nova < dist_atual:
                        # inverte a sub-rota de i+1 a j
                        route[i + 1:j + 1] = reversed(route[i + 1:j + 1])
                        improved = True
                        break
                if improved:
                    break
        return route

    # Aplica 2-opt em cada rota
    for route in routes:
        route = two_opt(route, coords)

    return routes