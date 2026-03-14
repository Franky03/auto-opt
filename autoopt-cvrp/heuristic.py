"""
Geracao 3 - Modificacao: Implementacao de Construcao Aleatorizada (Randomized Greedy) e Diversificacao Melhorada.

Motivo da mudanca: O algoritmo anterior utilizava apenas a inserção "Best Insertion" (Melhor Inserção), que tende a criar soluções locais muito rápidas, mas potencialmente subótimas (armadilhas de ótimos locais).

A nova estratégia implementada é a **Construção Aleatorizada com Diversificação (Randomized Greedy)**.
Em vez de escolher a melhor inserção absoluta, o algoritmo agora seleciona aleatoriamente entre as 3 melhores opções de inserção (ou menos, se não houver).

Isso gera soluções iniciais ligeiramente diferentes a cada execução, permitindo que o Local Search explore regiões diferentes do espaço de busca, aumentando a probabilidade de encontrar uma solução global melhor.

Além disso, a função `perturb_solution` foi levemente ajustada para garantir que os clientes removidos sejam reinsertados de forma mais inteligente (tentando rotas vazias ou com espaço), melhorando a robustez da fase de diversificação.
"""

import math
import time
import random

def euclidean_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def solve(instance: dict, time_limit: float = 30.0) -> list:
    """
    Resolve a instancia CVRP e retorna uma lista de rotas.
    """
    t_start = time.time()
    n = instance["n"]
    capacity = instance["capacity"]
    depot = instance["depot"]
    coords = [depot] + instance["coords"]  # no 0 = deposito
    demands = [0] + instance["demands"]    # demanda 0 do deposito
    
    # Seed fixa para reproducibilidade, mas o algoritmo usa randomização interna
    random.seed(42)

    # ============ Pre-computacao de Distancias (Otimizacao) ============
    dist_matrix = [[0.0] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(i + 1, n + 1):
            d = euclidean_distance(coords[i], coords[j])
            dist_matrix[i][j] = d
            dist_matrix[j][i] = d

    def get_dist(i, j):
        return dist_matrix[i][j]

    # ============ FASE 1: Construcao Aleatorizada (Randomized Greedy) ============
    def construct_solution():
        unassigned = set(range(1, n + 1))
        routes = []
        
        if not unassigned:
            return routes
            
        # Seleciona o primeiro cliente aleatoriamente entre os mais proximos do deposito (Top 3)
        closest_candidates = sorted(unassigned, key=lambda i: get_dist(0, i))[:3]
        closest_to_depot = random.choice(closest_candidates)
        unassigned.remove(closest_to_depot)
        routes.append([0, closest_to_depot, 0])
        route_loads = [demands[closest_to_depot]]
        
        while unassigned:
            # Lista para armazenar as melhores inserções encontradas: (custo, rota_idx, pos, cliente)
            best_insertions = []
            
            for client in list(unassigned):
                client_demand = demands[client]
                
                # 1. Tenta inserir em rotas existentes
                for r_idx, route in enumerate(routes):
                    if route_loads[r_idx] + client_demand > capacity:
                        continue
                    
                    for pos in range(1, len(route) - 1):
                        prev_node = route[pos - 1]
                        next_node = route[pos]
                        
                        cost = get_dist(prev_node, client) + get_dist(client, next_node) - get_dist(prev_node, next_node)
                        
                        # Adiciona a lista de candidatas
                        best_insertions.append((cost, r_idx, pos, client))
                
                # 2. Tenta criar rota nova
                cost_new_route = 2 * get_dist(0, client)
                best_insertions.append((cost_new_route, -2, 1, client))
            
            if not best_insertions:
                break

            # Ordena por custo crescente e pega os Top 3 (ou menos)
            best_insertions.sort(key=lambda x: x[0])
            top_candidates = best_insertions[:3]
            
            # Escolhe aleatoriamente um dos Top 3
            selected = random.choice(top_candidates)
            cost, r_idx, pos, client = selected
            
            if r_idx == -2:
                # Criar nova rota
                routes.append([0, client, 0])
                route_loads.append(demands[client])
            else:
                # Inserir na rota existente
                routes[r_idx].insert(pos, client)
                route_loads[r_idx] += demands[client]
            
            unassigned.remove(client)
            
            if time.time() > t_start + time_limit - 1.0:
                break
        
        return routes

    def route_distance(route: list) -> float:
        dist = 0.0
        for i in range(len(route) - 1):
            dist += get_dist(route[i], route[i + 1])
        return dist

    def total_distance(routes: list) -> float:
        return sum(route_distance(r) for r in routes)

    def two_opt(route: list) -> list:
        improved = True
        while improved:
            improved = False
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    a, b = route[i], route[i + 1]
                    c, d = route[j], route[j + 1]
                    
                    dist_atual = get_dist(a, b) + get_dist(c, d)
                    dist_nova = get_dist(a, c) + get_dist(b, d)
                    
                    if dist_nova < dist_atual:
                        route[i + 1:j + 1] = reversed(route[i + 1:j + 1])
                        improved = True
                        break
                if improved:
                    break
        return route

    def apply_two_opt(routes: list) -> list:
        for route in routes:
            two_opt(route)
        return routes

    def relocate_segment(routes: list, demands: list, capacity: float) -> list:
        improved = True
        max_iterations = 30
        iteration = 0
        
        while improved and iteration < max_iterations and time.time() < t_start + time_limit - 0.3:
            improved = False
            iteration += 1
            
            for from_route_idx in range(len(routes)):
                from_route = routes[from_route_idx]
                
                if len(from_route) < 4:
                    continue
                
                for seg_len in range(1, 4):
                    if time.time() > t_start + time_limit - 0.3:
                        break
                    
                    for i in range(1, len(from_route) - seg_len):
                        segment = from_route[i:i + seg_len]
                        segment_demand = sum(demands[c] for c in segment)
                        
                        prev_node = from_route[i - 1]
                        next_node = from_route[i + seg_len]
                        removal_cost = (get_dist(prev_node, segment[0]) +
                                       get_dist(segment[-1], next_node) -
                                       get_dist(prev_node, next_node))
                        
                        for to_route_idx in range(len(routes)):
                            if to_route_idx == from_route_idx:
                                continue
                            
                            to_route = routes[to_route_idx]
                            to_route_load = sum(demands[node] for node in to_route[1:-1])
                            
                            if to_route_load + segment_demand > capacity:
                                continue
                            
                            for j in range(1, len(to_route)):
                                prev_b = to_route[j - 1]
                                next_b = to_route[j]
                                
                                insertion_cost = (get_dist(prev_b, segment[0]) +
                                                   get_dist(segment[-1], next_b) -
                                                   get_dist(prev_b, next_b))
                                
                                gain = removal_cost - insertion_cost
                                
                                if gain > 1e-9:
                                    from_route[i:i + seg_len] = []
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

    def exchange(routes: list, demands: list, capacity: float) -> list:
        improved = True
        max_iterations = 20
        iteration = 0
        
        while improved and iteration < max_iterations and time.time() < t_start + time_limit - 0.3:
            improved = False
            iteration += 1
            
            for a in range(len(routes)):
                for b in range(a + 1, len(routes)):
                    route_a = routes[a]
                    route_b = routes[b]
                    
                    load_a = sum(demands[node] for node in route_a[1:-1])
                    load_b = sum(demands[node] for node in route_b[1:-1])
                    
                    for i in range(1, len(route_a) - 1):
                        if time.time() > t_start + time_limit - 0.3:
                            break
                        
                        for j in range(1, len(route_b) - 1):
                            customer_a = route_a[i]
                            customer_b = route_b[j]
                            
                            new_load_a = load_a - demands[customer_a] + demands[customer_b]
                            new_load_b = load_b - demands[customer_b] + demands[customer_a]
                            
                            if new_load_a > capacity or new_load_b > capacity:
                                continue
                            
                            prev_a = route_a[i - 1]
                            next_a = route_a[i + 1]
                            prev_b = route_b[j - 1]
                            next_b = route_b[j + 1]
                            
                            current_dist = (get_dist(prev_a, customer_a) +
                                           get_dist(customer_a, next_a) +
                                           get_dist(prev_b, customer_b) +
                                           get_dist(customer_b, next_b))
                            
                            new_dist = (get_dist(prev_a, customer_b) +
                                       get_dist(customer_b, next_a) +
                                       get_dist(prev_b, customer_a) +
                                       get_dist(customer_a, next_b))
                            
                            if new_dist < current_dist - 1e-9:
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

    # ============ FASE 5: 2-opt* Inter-rotas (Corrigido e Otimizado) ============
    def two_opt_star(routes: list, demands: list, capacity: float) -> list:
        improved = True
        max_iterations = 20
        iteration = 0
        
        while improved and iteration < max_iterations and time.time() < t_start + time_limit - 0.3:
            improved = False
            iteration += 1
            
            for a in range(len(routes)):
                for b in range(a + 1, len(routes)):
                    route_a = routes[a]
                    route_b = routes[b]
                    
                    if len(route_a) < 3 or len(route_b) < 3:
                        continue
                    
                    # Pre-calcular cargas
                    load_a = sum(demands[node] for node in route_a[1:-1])
                    load_b = sum(demands[node] for node in route_b[1:-1])
                    
                    for i in range(1, len(route_a) - 2):
                        if time.time() > t_start + time_limit - 0.3:
                            break
                        
                        for j in range(1, len(route_b) - 2):
                            a1, a2 = route_a[i], route_a[i + 1]
                            b1, b2 = route_b[j], route_b[j + 1]
                            
                            current_dist = (get_dist(a1, a2) +
                                          get_dist(b1, b2))
                            
                            new_dist = (get_dist(a1, b1) +
                                      get_dist(a2, b2))
                            
                            if new_dist >= current_dist - 1e-9:
                                continue
                            
                            # Calcular demanda dos segmentos a serem trocados (sufixos)
                            segment_a = route_a[i + 1:-1]
                            segment_b = route_b[j + 1:-1]
                            
                            load_segment_a = sum(demands[node] for node in segment_a)
                            load_segment_b = sum(demands[node] for node in segment_b)
                            
                            new_load_a = load_a - load_segment_a + load_segment_b
                            new_load_b = load_b - load_segment_b + load_segment_a
                            
                            if new_load_a > capacity or new_load_b > capacity:
                                continue
                            
                            # Aplicar troca de sufixos
                            new_route_a = route_a[:i + 1] + list(reversed(segment_b)) + [0]
                            new_route_b = route_b[:j + 1] + list(reversed(segment_a)) + [0]
                            
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

    def perturb_solution(routes: list, demands: list, capacity: float) -> list:
        if len(routes) < 2:
            return routes
            
        # Escolhe uma rota aleatoria para perturbar (priorizando rotas maiores)
        route_to_perturb = random.choice([r for r in routes if len(r) > 2])
        
        num_to_remove = min(random.randint(2, 4), len(route_to_perturb) - 2)
        client_indices = list(range(1, len(route_to_perturb) - 1))
        indices_to_remove = random.sample(client_indices, num_to_remove)
        
        removed_clients = []
        for idx in sorted(indices_to_remove, reverse=True):
            client = route_to_perturb[idx]
            removed_clients.append(client)
            route_to_perturb.pop(idx)
        
        # Reinsere clientes removidos
        for client in removed_clients:
            inserted = False
            # Tenta inserir em uma rota aleatoria primeiro
            target_route_idx = random.randint(0, len(routes) - 1)
            target_route = routes[target_route_idx]
            
            current_load = sum(demands[node] for node in target_route[1:-1])
            if current_load + demands[client] <= capacity:
                pos = random.randint(1, len(target_route) - 1)
                target_route.insert(pos, client)
                inserted = True
            else:
                # Se não couber, tenta em todas as outras rotas
                for idx in range(len(routes)):
                    r = routes[idx]
                    load = sum(demands[node] for node in r[1:-1])
                    if load + demands[client] <= capacity:
                        pos = random.randint(1, len(r) - 1)
                        r.insert(pos, client)
                        inserted = True
                        break
                
                # Se ainda não couber (caso raro), devolve para a rota original
                if not inserted:
                    route_to_perturb.insert(random.randint(1, len(route_to_perturb) - 1), client)

        return routes

    # ============ Execucao Principal com ILS ============
    
    routes = construct_solution()
    
    best_routes = [list(r) for r in routes]
    best_dist = total_distance(routes)
    
    while time.time() < t_start + time_limit - 0.5:
        local_search_iterations = 0
        max_local_iter = 8
        
        while local_search_iterations < max_local_iter and time.time() < t_start + time_limit - 0.5:
            routes_before = [list(r) for r in routes]
            dist_before = total_distance(routes)
            
            apply_two_opt(routes)
            relocate_segment(routes, demands, capacity)
            exchange(routes, demands, capacity)
            two_opt_star(routes, demands, capacity)
            
            dist_after = total_distance(routes)
            
            if dist_after >= dist_before - 1e-9:
                break
            local_search_iterations += 1
        
        current_dist = total_distance(routes)
        if current_dist < best_dist - 1e-9:
            best_dist = current_dist
            best_routes = [list(r) for r in routes]
        
        routes = perturb_solution(routes, demands, capacity)
    
    return best_routes