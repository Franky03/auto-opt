"""
Geracao: Iterated Local Search (ILS) com Relocate Melhorado
Descricao: Implementa Iterated Local Search (ILS) com um operador Relocate aprimorado
           que move segmentos de 1-3 clientes (Or-opt completo) em vez de apenas clientes
           individuais. Tambem adiciona um operador Exchange (swap entre rotas) para
           explorar melhor o espaco de solucoes.
Mudanca: Substitui o Or-opt simples por um Relocate de segmento (1-3 clientes) e adiciona
         um operador Exchange (swap de 1-1 clientes entre rotas). Ajusta o loop de
         melhoria local para alternar entre operadores de forma mais equilibrada.
"""

import time as _time
import math as _math
import random as _random

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
    
    # Seed fixa para reproducibilidade na construcao, mas aleatoriedade na perturbacao
    _random.seed(42)

    # ============ FASE 1: Construcao com Clarke-Wright Savings ============
    def construct_solution():
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
        
        return [r for r in routes if len(r) > 2]

    # ============ Funcoes de Distancia ============
    def route_distance(route: list, coords: list) -> float:
        dist = 0.0
        for i in range(len(route) - 1):
            dist += euclidean_distance(coords[route[i]], coords[route[i + 1]])
        return dist

    def total_distance(routes: list, coords: list) -> float:
        return sum(route_distance(r, coords) for r in routes)

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

    def apply_two_opt(routes: list, coords: list) -> list:
        for route in routes:
            two_opt(route, coords)
        return routes

    # ============ FASE 3: Relocate de Segmento (Or-opt Completo) ============
    def relocate_segment(routes: list, coords: list, demands: list, capacity: float) -> list:
        """
        Move segmentos de 1-3 clientes de uma rota para outra (Or-opt completo).
        """
        improved = True
        max_iterations = 30
        iteration = 0
        
        while improved and iteration < max_iterations and _time.time() < t_start + time_limit - 0.3:
            improved = False
            iteration += 1
            
            for from_route_idx in range(len(routes)):
                from_route = routes[from_route_idx]
                
                if len(from_route) < 4:  # Precisa ter pelo menos 3 clientes para mover segmento
                    continue
                
                # Tenta segmentos de tamanho 1, 2, 3
                for seg_len in range(1, 4):
                    if _time.time() > t_start + time_limit - 0.3:
                        break
                    
                    for i in range(1, len(from_route) - seg_len):
                        segment = from_route[i:i + seg_len]
                        segment_demand = sum(demands[c] for c in segment)
                        
                        # Custo de remocao
                        prev_node = from_route[i - 1]
                        next_node = from_route[i + seg_len]
                        removal_cost = (euclidean_distance(coords[prev_node], coords[segment[0]]) +
                                       euclidean_distance(coords[segment[-1]], coords[next_node]) -
                                       euclidean_distance(coords[prev_node], coords[next_node]))
                        
                        for to_route_idx in range(len(routes)):
                            if to_route_idx == from_route_idx:
                                continue
                            
                            to_route = routes[to_route_idx]
                            to_route_load = sum(demands[node] for node in to_route[1:-1])
                            
                            if to_route_load + segment_demand > capacity:
                                continue
                            
                            # Tenta inserir o segmento em todas as posicoes
                            for j in range(1, len(to_route)):
                                prev_b = to_route[j - 1]
                                next_b = to_route[j]
                                
                                insertion_cost = (euclidean_distance(coords[prev_b], coords[segment[0]]) +
                                                   euclidean_distance(coords[segment[-1]], coords[next_b]) -
                                                   euclidean_distance(coords[prev_b], coords[next_b]))
                                
                                gain = removal_cost - insertion_cost
                                
                                if gain > 1e-9:
                                    # Remove o segmento da rota de origem
                                    from_route[i:i + seg_len] = []
                                    # Insere na rota de destino
                                    to_route[j:j] = segment
                                    improved = True
                                    break
                            
                            if improved:
                                break
                        
                        if improved:
                            break
                    
                    if improved:
                        break
                
                if improved:
                    break
        
        return routes

    # ============ FASE 4: Exchange (Swap entre Rotas) ============
    def exchange(routes: list, coords: list, demands: list, capacity: float) -> list:
        """
        Troca um cliente de uma rota com um cliente de outra rota.
        """
        improved = True
        max_iterations = 20
        iteration = 0
        
        while improved and iteration < max_iterations and _time.time() < t_start + time_limit - 0.3:
            improved = False
            iteration += 1
            
            for a in range(len(routes)):
                for b in range(a + 1, len(routes)):
                    route_a = routes[a]
                    route_b = routes[b]
                    
                    load_a = sum(demands[node] for node in route_a[1:-1])
                    load_b = sum(demands[node] for node in route_b[1:-1])
                    
                    for i in range(1, len(route_a) - 1):
                        if _time.time() > t_start + time_limit - 0.3:
                            break
                        
                        for j in range(1, len(route_b) - 1):
                            customer_a = route_a[i]
                            customer_b = route_b[j]
                            
                            # Verifica capacidade apos troca
                            new_load_a = load_a - demands[customer_a] + demands[customer_b]
                            new_load_b = load_b - demands[customer_b] + demands[customer_a]
                            
                            if new_load_a > capacity or new_load_b > capacity:
                                continue
                            
                            # Calcula ganho
                            prev_a = route_a[i - 1]
                            next_a = route_a[i + 1]
                            prev_b = route_b[j - 1]
                            next_b = route_b[j + 1]
                            
                            current_dist = (euclidean_distance(coords[prev_a], coords[customer_a]) +
                                           euclidean_distance(coords[customer_a], coords[next_a]) +
                                           euclidean_distance(coords[prev_b], coords[customer_b]) +
                                           euclidean_distance(coords[customer_b], coords[next_b]))
                            
                            new_dist = (euclidean_distance(coords[prev_a], coords[customer_b]) +
                                       euclidean_distance(coords[customer_b], coords[next_a]) +
                                       euclidean_distance(coords[prev_b], coords[customer_a]) +
                                       euclidean_distance(coords[customer_a], coords[next_b]))
                            
                            if new_dist < current_dist - 1e-9:
                                # Realiza a troca
                                route_a[i] = customer_b
                                route_b[j] = customer_a
                                improved = True
                                break
                        
                        if improved:
                            break
                    
                    if improved:
                        break
                
                if improved:
                    break
        
        return routes

    # ============ FASE 5: 2-opt* inter-rotas (cross-exchange) ============
    def two_opt_star(routes: list, coords: list, demands: list, capacity: float) -> list:
        improved = True
        max_iterations = 20
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
                    
                    load_a = sum(demands[node] for node in route_a[1:-1])
                    load_b = sum(demands[node] for node in route_b[1:-1])
                    
                    for i in range(1, len(route_a) - 2):
                        if _time.time() > t_start + time_limit - 0.3:
                            break
                        
                        for j in range(1, len(route_b) - 2):
                            a1, a2 = route_a[i], route_a[i + 1]
                            b1, b2 = route_b[j], route_b[j + 1]
                            
                            current_dist = (euclidean_distance(coords[a1], coords[a2]) +
                                          euclidean_distance(coords[b1], coords[b2]))
                            
                            new_dist = (euclidean_distance(coords[a1], coords[b1]) +
                                      euclidean_distance(coords[a2], coords[b2]))
                            
                            if new_dist >= current_dist - 1e-9:
                                continue
                            
                            segment_a = route_a[i + 1:-1]
                            segment_b = route_b[j + 1:-1]
                            
                            load_segment_a = sum(demands[node] for node in segment_a)
                            load_segment_b = sum(demands[node] for node in segment_b)
                            
                            new_load_a = load_a - load_segment_a + load_segment_b
                            new_load_b = load_b - load_segment_b + load_segment_a
                            
                            if new_load_a > capacity or new_load_b > capacity:
                                continue
                            
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

    # ============ FASE 6: Perturbacao (ILS) ============
    def perturb_solution(routes: list, coords: list, demands: list, capacity: float) -> list:
        """
        Remove clientes de uma rota aleatoria e os reinsere otimamente.
        """
        if len(routes) < 2:
            return routes
            
        # Seleciona uma rota aleatoria para perturbar
        route_to_perturb = _random.choice([r for r in routes if len(r) > 2])
        
        # Remove 2-4 clientes desta rota
        num_to_remove = min(_random.randint(2, 4), len(route_to_perturb) - 2)
        client_indices = list(range(1, len(route_to_perturb) - 1))
        indices_to_remove = _random.sample(client_indices, num_to_remove)
        
        removed_clients = []
        # Remove em ordem inversa para nao alterar indices
        for idx in sorted(indices_to_remove, reverse=True):
            client = route_to_perturb[idx]
            removed_clients.append(client)
            route_to_perturb.pop(idx)
        
        # Reinsere os clientes em posicoes aleatorias (ou em outras rotas)
        for client in removed_clients:
            # Tenta inserir em uma rota aleatoria
            target_route_idx = _random.randint(0, len(routes) - 1)
            target_route = routes[target_route_idx]
            
            current_load = sum(demands[node] for node in target_route[1:-1])
            if current_load + demands[client] <= capacity:
                pos = _random.randint(1, len(target_route) - 1)
                target_route.insert(pos, client)
            else:
                # Tenta encontrar uma rota onde caiba
                inserted = False
                for idx in range(len(routes)):
                    r = routes[idx]
                    load = sum(demands[node] for node in r[1:-1])
                    if load + demands[client] <= capacity:
                        pos = _random.randint(1, len(r) - 1)
                        r.insert(pos, client)
                        inserted = True
                        break
                
                if not inserted:
                    # Coloca de volta na rota original
                    route_to_perturb.insert(_random.randint(1, len(route_to_perturb) - 1), client)

        return routes

    # ============ Execucao Principal com ILS ============
    
    # 1. Construcao Inicial
    routes = construct_solution()
    
    best_routes = [list(r) for r in routes]
    best_dist = total_distance(routes, coords)
    
    # Loop do ILS
    while _time.time() < t_start + time_limit - 0.5:
        # 2. Melhoria Local - alternando entre operadores
        local_search_iterations = 0
        max_local_iter = 8
        
        while local_search_iterations < max_local_iter and _time.time() < t_start + time_limit - 0.5:
            routes_before = [list(r) for r in routes]
            dist_before = total_distance(routes, coords)
            
            # 2-opt intra
            apply_two_opt(routes, coords)
            # Relocate de segmento (Or-opt completo)
            relocate_segment(routes, coords, demands, capacity)
            # Exchange (swap entre rotas)
            exchange(routes, coords, demands, capacity)
            # 2-opt*
            two_opt_star(routes, coords, demands, capacity)
            
            dist_after = total_distance(routes, coords)
            
            if dist_after >= dist_before - 1e-9:
                break
            local_search_iterations += 1
        
        # Atualiza melhor solucao
        current_dist = total_distance(routes, coords)
        if current_dist < best_dist - 1e-9:
            best_dist = current_dist
            best_routes = [list(r) for r in routes]
        
        # 3. Perturbacao
        routes = perturb_solution(routes, coords, demands, capacity)
    
    return best_routes