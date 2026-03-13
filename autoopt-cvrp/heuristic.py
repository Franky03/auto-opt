"""
Heuristica CVRP -- Geracao 2
Algoritmo: Nearest Neighbor Greedy + 2-opt intra-rota + Or-opt inter-rotas
Descricao: Constroi rotas com Nearest Neighbor, aplica 2-opt em cada rota,
           depois usa Or-opt para realocar clientes entre rotas e reduzir
           a distancia total.
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
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    a, b = route[i], route[i + 1]
                    c, d = route[j], route[j + 1]
                    
                    dist_atual = euclidean_distance(coords[a], coords[b]) + euclidean_distance(coords[c], coords[d])
                    dist_nova = euclidean_distance(coords[a], coords[c]) + euclidean_distance(coords[b], coords[d])
                    
                    if dist_nova < dist_atual:
                        route[i + 1:j + 1] = reversed(route[i + 1:j + 1])
                        improved = True
                        break
                if improved:
                    break
        return route

    for route in routes:
        two_opt(route, coords)

    # ============ FASE 3: Or-opt inter-rotas ============
    def route_distance(route: list, coords: list) -> float:
        """Calcula a distancia total de uma rota."""
        dist = 0.0
        for i in range(len(route) - 1):
            dist += euclidean_distance(coords[route[i]], coords[route[i + 1]])
        return dist

    def total_distance(routes: list, coords: list) -> float:
        """Calcula a distancia total de todas as rotas."""
        return sum(route_distance(r, coords) for r in routes)

    def or_opt(routes: list, coords: list, demands: list, capacity: float) -> list:
        """
        Or-opt: tenta mover clientes individuais entre rotas para reduzir a distancia.
        """
        improved = True
        max_iterations = 100
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            # Para cada rota de origem
            for from_route_idx in range(len(routes)):
                from_route = routes[from_route_idx]
                
                # Para cada cliente na rota (excluindo deposito)
                for i in range(1, len(from_route) - 1):
                    customer = from_route[i]
                    customer_demand = demands[customer]
                    
                    # Calcular custo de remover o cliente da rota de origem
                    prev_node = from_route[i - 1]
                    next_node = from_route[i + 1]
                    removal_cost = (euclidean_distance(coords[prev_node], coords[customer]) +
                                   euclidean_distance(coords[customer], coords[next_node]) -
                                   euclidean_distance(coords[prev_node], coords[next_node]))
                    
                    # Tentar inserir em outras rotas
                    for to_route_idx in range(len(routes)):
                        if to_route_idx == from_route_idx:
                            continue
                        
                        to_route = routes[to_route_idx]
                        to_route_load = sum(demands[node] for node in to_route[1:-1])
                        
                        # Verificar se o cliente cabe na rota de destino
                        if to_route_load + customer_demand > capacity:
                            continue
                        
                        # Tentar inserir em todas as posicoes da rota de destino
                        for j in range(1, len(to_route)):  # posicoes 1..len-1
                            prev_b = to_route[j - 1]
                            next_b = to_route[j]
                            
                            # Custo de insercao
                            insertion_cost = (euclidean_distance(coords[prev_b], coords[customer]) +
                                             euclidean_distance(coords[customer], coords[next_b]) -
                                             euclidean_distance(coords[prev_b], coords[next_b]))
                            
                            # Ganho = custo_remocao - custo_insercao
                            gain = removal_cost - insertion_cost
                            
                            if gain > 1e-9:  # Melhorar a solucao
                                # Remover da rota de origem
                                from_route.pop(i)
                                
                                # Inserir na rota de destino
                                to_route.insert(j, customer)
                                
                                improved = True
                                break
                        
                        if improved:
                            break
                    
                    if improved:
                        break
                
                if improved:
                    break
        
        return routes

    # Aplicar Or-opt com controle de tempo
    while _time.time() < t_start + time_limit - 0.5:  # reservar 0.5s para segurança
        routes_before = [list(r) for r in routes]
        total_dist_before = total_distance(routes, coords)
        
        routes = or_opt(routes, coords, demands, capacity)
        
        total_dist_after = total_distance(routes, coords)
        
        if total_dist_after >= total_dist_before - 1e-9:
            # Sem melhoria, restaurar e sair
            routes = routes_before
            break
    
    return routes