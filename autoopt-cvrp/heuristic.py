"""
Heuristica CVRP -- Geracao 5
Algoritmo: Clarke-Wright Savings + 2-opt intra-rota + Or-opt + 2-opt* inter-rotas
Descricao: Adiciona 2-opt* (cross-exchange) para trocar segmentos entre rotas,
           uma operacao poderosa que frequentemente reduz significativamente a distancia.
Mudanca: Implementa 2-opt* como fase de melhoria inter-rotas adicional apos o Or-opt.
"""

import time as _time
import math as _math

from prepare import euclidean_distance


def solve(instance: dict, time_limit: float = 30.0) -> list:
    """
    Resolve a instancia CVRP e retorna uma lista de rotas.
    """
    t_start = _time.time()
    n = instance["n"]
    capacity = instance["capacity"]
    depot = instance["depot"]
    coords = [depot] + instance["coords"]  # no 0 = deposito
    demands = [0] + instance["demands"]    # demanda 0 do deposito

    # ============ FASE 1: Construcao com Clarke-Wright Savings ============
    dist_to_depot = [euclidean_distance(coords[0], coords[i]) for i in range(1, n + 1)]
    
    savings = []
    for i in range(1, n + 1):
        for j in range(i + 1, n + 1):
            s = dist_to_depot[i - 1] + dist_to_depot[j - 1] - euclidean_distance(coords[i], coords[j])
            savings.append((s, i, j))
    
    savings.sort(reverse=True)
    
    routes = [[0, i, 0] for i in range(1, n + 1)]
    route_load = [demands[i] for i in range(1, n + 1)]
    in_route = {i: i - 1 for i in range(1, n + 1)}
    route_ends = [[1, -1] for _ in range(n)]
    
    for _, i, j in savings:
        if _time.time() > t_start + time_limit - 1.0:
            break
            
        route_i = in_route.get(i)
        route_j = in_route.get(j)
        
        if route_i is None or route_j is None or route_i == route_j:
            continue
        
        ends_i = route_ends[route_i]
        ends_j = route_ends[route_j]
        
        i_at_end = (i == ends_i[0] or i == ends_i[1])
        j_at_end = (j == ends_j[0] or j == ends_j[1])
        
        if not (i_at_end and j_at_end):
            continue
        
        if route_load[route_i] + route_load[route_j] > capacity:
            continue
        
        route_i_obj = routes[route_i]
        route_j_obj = routes[route_j]
        
        if i == ends_i[0]:
            if j == ends_j[0]:
                new_route = route_i_obj + route_j_obj[-2:0:-1] + [0]
            else:
                new_route = route_i_obj + route_j_obj[1:]
        else:
            if j == ends_j[0]:
                new_route = route_j_obj[-2:0:-1] + [0] + route_i_obj[1:]
            else:
                new_route = route_j_obj + route_i_obj[-2:0:-1] + [0]
        
        routes[route_i] = new_route
        routes[route_j] = [0, 0]
        route_load[route_i] += route_load[route_j]
        route_load[route_j] = 0
        
        if len(new_route) > 2:
            route_ends[route_i] = [new_route[1], new_route[-2]]
        
        for node in new_route:
            if 1 <= node <= n:
                in_route[node] = route_i
    
    routes = [r for r in routes if len(r) > 2]

    # ============ FASE 2: Melhoria 2-opt intra-rota ============
    def two_opt(route: list, coords: list) -> list:
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
        dist = 0.0
        for i in range(len(route) - 1):
            dist += euclidean_distance(coords[route[i]], coords[route[i + 1]])
        return dist

    def total_distance(routes: list, coords: list) -> float:
        return sum(route_distance(r, coords) for r in routes)

    def or_opt(routes: list, coords: list, demands: list, capacity: float) -> list:
        improved = True
        max_iterations = 100
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            for from_route_idx in range(len(routes)):
                from_route = routes[from_route_idx]
                
                for i in range(1, len(from_route) - 1):
                    customer = from_route[i]
                    customer_demand = demands[customer]
                    
                    prev_node = from_route[i - 1]
                    next_node = from_route[i + 1]
                    removal_cost = (euclidean_distance(coords[prev_node], coords[customer]) +
                                   euclidean_distance(coords[customer], coords[next_node]) -
                                   euclidean_distance(coords[prev_node], coords[next_node]))
                    
                    for to_route_idx in range(len(routes)):
                        if to_route_idx == from_route_idx:
                            continue
                        
                        to_route = routes[to_route_idx]
                        to_route_load = sum(demands[node] for node in to_route[1:-1])
                        
                        if to_route_load + customer_demand > capacity:
                            continue
                        
                        for j in range(1, len(to_route)):
                            prev_b = to_route[j - 1]
                            next_b = to_route[j]
                            
                            insertion_cost = (euclidean_distance(coords[prev_b], coords[customer]) +
                                             euclidean_distance(coords[customer], coords[next_b]) -
                                             euclidean_distance(coords[prev_b], coords[next_b]))
                            
                            gain = removal_cost - insertion_cost
                            
                            if gain > 1e-9:
                                from_route.pop(i)
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

    while _time.time() < t_start + time_limit - 0.5:
        routes_before = [list(r) for r in routes]
        total_dist_before = total_distance(routes, coords)
        
        routes = or_opt(routes, coords, demands, capacity)
        
        total_dist_after = total_distance(routes, coords)
        
        if total_dist_after >= total_dist_before - 1e-9:
            routes = routes_before
            break
    
    # ============ FASE 4: 2-opt* inter-rotas (cross-exchange) ============
    def two_opt_star(routes: list, coords: list, demands: list, capacity: float) -> list:
        """
        2-opt* (cross-exchange): troca segmentos entre duas rotas.
        Dadas rotas A e B com arestas (i, i+1) e (j, j+1):
        - Remove arestas (i, i+1) e (j, j+1)
        - Adiciona arestas (i, j) e (i+1, j+1)
        - Inverte segmento entre i+1 e fim da rota A
        - Inverte segmento entre j+1 e fim da rota B
        """
        improved = True
        max_iterations = 50
        iteration = 0
        
        while improved and iteration < max_iterations and _time.time() < t_start + time_limit - 0.3:
            improved = False
            iteration += 1
            
            for a in range(len(routes)):
                for b in range(a + 1, len(routes)):
                    route_a = routes[a]
                    route_b = routes[b]
                    
                    if len(route_a) < 3 or len(route_b) < 3:
                        continue
                    
                    # Calcular cargas das rotas
                    load_a = sum(demands[node] for node in route_a[1:-1])
                    load_b = sum(demands[node] for node in route_b[1:-1])
                    
                    # Tentar todas as arestas em route_a
                    for i in range(1, len(route_a) - 2):
                        if _time.time() > t_start + time_limit - 0.3:
                            break
                            
                        # Tentar todas as arestas em route_b
                        for j in range(1, len(route_b) - 2):
                            # Nodos das arestas
                            a1, a2 = route_a[i], route_a[i + 1]
                            b1, b2 = route_b[j], route_b[j + 1]
                            
                            # Distancia atual das arestas
                            current_dist = (euclidean_distance(coords[a1], coords[a2]) +
                                          euclidean_distance(coords[b1], coords[b2]))
                            
                            # Distancia nova apos 2-opt*
                            new_dist = (euclidean_distance(coords[a1], coords[b1]) +
                                      euclidean_distance(coords[a2], coords[b2]))
                            
                            if new_dist >= current_dist - 1e-9:
                                continue
                            
                            # Calcular carga do segmento que sera movido
                            # Segmento de route_a: de a2 ate o fim (excluindo deposito)
                            segment_a = route_a[i + 1:-1]
                            segment_b = route_b[j + 1:-1]
                            
                            load_segment_a = sum(demands[node] for node in segment_a)
                            load_segment_b = sum(demands[node] for node in segment_b)
                            
                            # Nova carga das rotas apos troca
                            new_load_a = load_a - load_segment_a + load_segment_b
                            new_load_b = load_b - load_segment_b + load_segment_a
                            
                            if new_load_a > capacity or new_load_b > capacity:
                                continue
                            
                            # Aplicar 2-opt*
                            # Nova rota A: route_a[:i+1] + segment_b + [0]
                            # Nova rota B: route_b[:j+1] + segment_a + [0]
                            new_route_a = route_a[:i + 1] + segment_b + [0]
                            new_route_b = route_b[:j + 1] + segment_a + [0]
                            
                            routes[a] = new_route_a
                            routes[b] = new_route_b
                            improved = True
                            break
                        
                        if improved:
                            break
                    
                    if improved:
                        break
                
                if improved:
                    break
        
        return routes

    # Aplicar 2-opt*
    while _time.time() < t_start + time_limit - 0.2:
        routes_before = [list(r) for r in routes]
        total_dist_before = total_distance(routes, coords)
        
        routes = two_opt_star(routes, coords, demands, capacity)
        
        total_dist_after = total_distance(routes, coords)
        
        if total_dist_after >= total_dist_before - 1e-9:
            routes = routes_before
            break

    return routes