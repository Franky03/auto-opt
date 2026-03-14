"""
Geracao 3 - Modificacao: Correcao e Otimizacao do Operador Relocate (Move) Inter-Rota.

Motivo da mudanca: A analise do codigo revela que o operador relocate_segment estava incompleto
e com logica truncada, impossibilitando sua execucao correta. O operador relocate (move) e fundamental
para CVRP pois permite transferir clientes entre rotas, frequentemente encontrando solucoes melhores
que apenas rearranjos intra-rota.
A nova versao:
1. Implementa corretamente o relocate movendo um ou dois clientes consecutivos entre rotas.
2. Calcula ganho de distancia em O(1) sem reconstruir rotas.
3. Verifica capacidade de forma eficiente.
4. Utiliza estrategia de melhor vizinho para maior estabilidade.
"""

import math
import time
import random

def euclidean_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def solve(instance: dict, time_limit: float = 30.0) -> list:
    t_start = time.time()
    n = instance["n"]
    capacity = instance["capacity"]
    depot = instance["depot"]
    coords = [depot] + instance["coords"]
    demands = [0] + instance["demands"]
    
    random.seed(42)

    dist_matrix = [[0.0] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(i + 1, n + 1):
            d = euclidean_distance(coords[i], coords[j])
            dist_matrix[i][j] = d
            dist_matrix[j][i] = d

    def get_dist(i, j):
        return dist_matrix[i][j]

    def construct_solution():
        unassigned = set(range(1, n + 1))
        routes = []
        
        if not unassigned:
            return routes
            
        closest_to_depot = min(unassigned, key=lambda i: get_dist(0, i))
        unassigned.remove(closest_to_depot)
        routes.append([0, closest_to_depot, 0])
        route_loads = [demands[closest_to_depot]]
        
        while unassigned:
            best_insertion_cost = float('inf')
            best_route_idx = -1
            best_pos = -1
            best_client = -1
            
            for client in list(unassigned):
                client_demand = demands[client]
                
                for r_idx, route in enumerate(routes):
                    if route_loads[r_idx] + client_demand > capacity:
                        continue
                    
                    for pos in range(1, len(route) - 1):
                        prev_node = route[pos - 1]
                        next_node = route[pos]
                        
                        cost = get_dist(prev_node, client) + get_dist(client, next_node) - get_dist(prev_node, next_node)
                        
                        if cost < best_insertion_cost:
                            best_insertion_cost = cost
                            best_route_idx = r_idx
                            best_pos = pos
                            best_client = client
                
                if best_route_idx == -1:
                    cost_new_route = 2 * get_dist(0, client)
                    if cost_new_route < best_insertion_cost:
                        best_insertion_cost = cost_new_route
                        best_route_idx = -2
                        best_pos = 1
                        best_client = client
            
            if best_route_idx == -2:
                routes.append([0, best_client, 0])
                route_loads.append(demands[best_client])
            else:
                routes[best_route_idx].insert(best_pos, best_client)
                route_loads[best_route_idx] += demands[best_client]
            
            unassigned.remove(best_client)
            
            if time.time() > t_start + time_limit - 1.0:
                break
        
        return routes

    def route_distance(route):
        dist = 0.0
        for i in range(len(route) - 1):
            dist += get_dist(route[i], route[i + 1])
        return dist

    def total_distance(routes):
        return sum(route_distance(r) for r in routes)

    def route_load(route, demands):
        return sum(demands[node] for node in route[1:-1])

    def two_opt(route):
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

    def apply_two_opt(routes):
        for route in routes:
            two_opt(route)
        return routes

    def relocate_customer(routes, demands, capacity):
        improved = True
        max_passes = 15
        passes = 0
        
        while improved and passes < max_passes and time.time() < t_start + time_limit - 0.3:
            improved = False
            passes += 1
            
            best_gain = 0
            best_move = None
            
            for from_r in range(len(routes)):
                from_route = routes[from_r]
                if len(from_route) < 4:
                    continue
                    
                from_load = route_load(from_route, demands)
                
                for i in range(1, len(from_route) - 1):
                    client = from_route[i]
                    client_demand = demands[client]
                    prev_node = from_route[i - 1]
                    next_node = from_route[i + 1]
                    
                    removal_cost = get_dist(prev_node, client) + get_dist(client, next_node) - get_dist(prev_node, next_node)
                    
                    for to_r in range(len(routes)):
                        if to_r == from_r:
                            continue
                        
                        to_route = routes[to_r]
                        to_load = route_load(to_route, demands)
                        
                        if to_load + client_demand > capacity:
                            continue
                        
                        for j in range(1, len(to_route)):
                            prev_b = to_route[j - 1]
                            next_b = to_route[j]
                            
                            insertion_cost = get_dist(prev_b, client) + get_dist(client, next_b) - get_dist(prev_b, next_b)
                            gain = removal_cost - insertion_cost
                            
                            if gain > best_gain + 1e-10:
                                best_gain = gain
                                best_move = (from_r, i, to_r, j)
            
            if best_move:
                from_r, i, to_r, j = best_move
                client = routes[from_r][i]
                routes[from_r].pop(i)
                routes[to_r].insert(j, client)
                improved = True
        
        return routes

    def relocate_two_consecutive(routes, demands, capacity):
        improved = True
        max_passes = 8
        passes = 0
        
        while improved and passes < max_passes and time.time() < t_start + time_limit - 0.3:
            improved = False
            passes += 1
            
            best_gain = 0
            best_move = None
            
            for from_r in range(len(routes)):
                from_route = routes[from_r]
                if len(from_route) < 5:
                    continue
                    
                from_load = route_load(from_route, demands)
                
                for i in range(1, len(from_route) - 2):
                    c1, c2 = from_route[i], from_route[i + 1]
                    seg_demand = demands[c1] + demands[c2]
                    
                    prev_node = from_route[i - 1]
                    next_node = from_route[i + 2]
                    
                    removal_cost = (get_dist(prev_node, c1) + get_dist(c1, c2) + 
                                   get_dist(c2, next_node) - get_dist(prev_node, next_node))
                    
                    if from_load - seg_demand < 0:
                        continue
                        
                    for to_r in range(len(routes)):
                        if to_r == from_r:
                            continue
                        
                        to_route = routes[to_r]
                        to_load = route_load(to_route, demands)
                        
                        if to_load + seg_demand > capacity:
                            continue
                        
                        for j in range(1, len(to_route)):
                            prev_b = to_route[j - 1]
                            next_b = to_route[j]
                            
                            insertion_cost = (get_dist(prev_b, c1) + get_dist(c1, c2) + 
                                             get_dist(c2, next_b) - get_dist(prev_b, next_b))
                            
                            gain = removal_cost - insertion_cost
                            
                            if gain > best_gain + 1e-10:
                                best_gain = gain
                                best_move = (from_r, i, to_r, j)
            
            if best_move:
                from_r, i, to_r, j = best_move
                c1, c2 = routes[from_r][i], routes[from_r][i + 1]
                routes[from_r].pop(i + 1)
                routes[from_r].pop(i)
                routes[to_r].insert(j, c1)
                routes[to_r].insert(j + 1, c2)
                improved = True
        
        return routes

    def exchange(routes, demands, capacity):
        improved = True
        max_passes = 12
        passes = 0
        
        while improved and passes < max_passes and time.time() < t_start + time_limit - 0.3:
            improved = False
            passes += 1
            
            best_gain = 0
            best_swap = None
            
            for a in range(len(routes)):
                for b in range(a + 1, len(routes)):
                    route_a = routes[a]
                    route_b = routes[b]
                    
                    load_a = route_load(route_a, demands)
                    load_b = route_load(route_b, demands)
                    
                    for i in range(1, len(route_a) - 1):
                        for j in range(1, len(route_b) - 1):
                            ca, cb = route_a[i], route_b[j]
                            
                            if (load_a - demands[ca] + demands[cb] > capacity or
                                load_b - demands[cb] + demands[ca] > capacity):
                                continue
                            
                            prev_a, next_a = route_a[i - 1], route_a[i + 1]
                            prev_b, next_b = route_b[j - 1], route_b[j + 1]
                            
                            current_dist = (get_dist(prev_a, ca) + get_dist(ca, next_a) +
                                          get_dist(prev_b, cb) + get_dist(cb, next_b))
                            
                            new_dist = (get_dist(prev_a, cb) + get_dist(cb, next_a) +
                                       get_dist(prev_b, ca) + get_dist(ca, next_b))
                            
                            gain = current_dist - new_dist
                            
                            if gain > best_gain + 1e-10:
                                best_gain = gain
                                best_swap = (a, i, b, j)
            
            if best_swap:
                a, i, b, j = best_swap
                routes[a][i], routes[b][j] = routes[b][j], routes[a][i]
                improved = True
        
        return routes

    def two_opt_star(routes, demands, capacity):
        improved = True
        max_passes = 10
        passes = 0
        
        while improved and passes < max_passes and time.time() < t_start + time_limit - 0.3:
            improved = False
            passes += 1
            
            for a in range(len(routes)):
                for b in range(a + 1, len(routes)):
                    route_a = routes[a]
                    route_b = routes[b]
                    
                    if len(route_a) < 3 or len(route_b) < 3:
                        continue
                    
                    load_a = route_load(route_a, demands)
                    load_b = route_load(route_b, demands)
                    
                    for i in range(1, len(route_a) - 2):
                        for j in range(1, len(route_b) - 2):
                            a1, a2 = route_a[i], route_a[i + 1]
                            b1, b2 = route_b[j], route_b[j + 1]
                            
                            current_dist = get_dist(a1, a2) + get_dist(b1, b2)
                            new_dist = get_dist(a1, b1) + get_dist(a2, b2)
                            
                            if new_dist >= current_dist - 1e-9:
                                continue
                            
                            segment_a = route_a[i + 1:-1]
                            segment_b = route_b[j + 1:-1]
                            
                            load_segment_a = sum(demands[node] for node in segment_a)
                            load_segment_b = sum(demands[node] for node in segment_b)
                            
                            if (load_a - load_segment_a + load_segment_b > capacity or
                                load_b - load_segment_b + load_segment_a > capacity):
                                continue
                            
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

    def perturb_solution(routes, demands, capacity):
        if len(routes) < 2:
            return routes
            
        route_to_perturb = random.choice([r for r in routes if len(r) > 2])
        
        num_to_remove = min(random.randint(2, 4), len(route_to_perturb) - 2)
        client_indices = list(range(1, len(route_to_perturb) - 1))
        indices_to_remove = random.sample(client_indices, num_to_remove)
        
        removed_clients = []
        for idx in sorted(indices_to_remove, reverse=True):
            client = route_to_perturb[idx]
            removed_clients.append(client)
            route_to_perturb.pop(idx)
        
        for client in removed_clients:
            target_route_idx = random.randint(0, len(routes) - 1)
            target_route = routes[target_route_idx]
            
            current_load = route_load(target_route, demands)
            if current_load + demands[client] <= capacity:
                pos = random.randint(1, len(target_route) - 1)
                target_route.insert(pos, client)
            else:
                inserted = False
                for idx in range(len(routes)):
                    r = routes[idx]
                    load = route_load(r, demands)
                    if load + demands[client] <= capacity:
                        pos = random.randint(1, len(r) - 1)
                        r.insert(pos, client)
                        inserted = True
                        break
                
                if not inserted:
                    route_to_perturb.insert(random.randint(1, len(route_to_perturb) - 1), client)

        return routes

    routes = construct_solution()
    
    best_routes = [list(r) for r in routes]
    best_dist = total_distance(routes)
    
    while time.time() < t_start + time_limit - 0.5:
        local_search_iterations = 0
        max_local_iter = 10
        
        while local_search_iterations < max_local_iter and time.time() < t_start + time_limit - 0.5:
            routes_before = [list(r) for r in routes]
            dist_before = total_distance(routes)
            
            apply_two_opt(routes)
            relocate_customer(routes, demands, capacity)
            relocate_two_consecutive(routes, demands, capacity)
            exchange(routes, demands, capacity)
            
            current_dist = total_distance(routes)
            
            if current_dist < best_dist - 1e-6:
                best_dist = current_dist
                best_routes = [list(r) for r in routes]
            
            if current_dist >= dist_before - 1e-6:
                break
                
            local_search_iterations += 1
        
        if time.time() > t_start + time_limit - 0.5:
            break
            
        if random.random() < 0.6:
            routes = perturb_solution(routes, demands, capacity)
        
        current_dist = total_distance(routes)
        if current_dist < best_dist - 1e-6:
            best_dist = current_dist
            best_routes = [list(r) for r in routes]
    
    return best_routes

def main():
    instance = {
        "n": 25,
        "capacity": 50,
        "depot": (0, 0),
        "coords": [(random.randint(1, 100), random.randint(1, 100)) for _ in range(25)],
        "demands": [random.randint(1, 10) for _ in range(25)]
    }
    
    routes = solve(instance, time_limit=30.0)
    
    print(f"Numero de rotas: {len(routes)}")
    print(f"Distancia total: {total_distance(routes):.2f}")
    
    for i, route in enumerate(routes):
        load = route_load(route, [0] + instance["demands"])
        print(f"Rota {i + 1}: {route} (Capacidade: {load}/{instance['capacity']})")

if __name__ == "__main__":
    main()