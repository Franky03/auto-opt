"""
Heuristica CVRP -- Geracao 0
Algoritmo: Nearest Neighbor Greedy
Descricao: Constroi rotas adicionando sempre o cliente nao visitado mais proximo
           que caiba na capacidade atual. Quando nenhum cliente cabe, fecha a rota.
"""

import time as _time

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

    return routes
