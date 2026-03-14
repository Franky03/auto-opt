"""
Heuristica CVRP -- Geracao 3
Algoritmo: Clarke-Wright Savings + 2-opt intra-rota + Or-opt inter-rotas
Descricao: Constroi rotas com o algoritmo de Savings de Clarke-Wright,
           aplica 2-opt em cada rota, depois usa Or-opt para realocar
           clientes entre rotas e reduzir a distancia total.
Mudanca: Substitui Nearest Neighbor por Clarke-Wright Savings para melhor
         solucao inicial (considera economia global, nao apenas vizinhanca local).
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

    # ============ FASE 1: Construcao com Clarke-Wright Savings ============
    # Calcula distancias do deposito para cada cliente
    dist_to_depot = [euclidean_distance(coords[0], coords[i]) for i in range(1, n + 1)]
    
    # Calcula savings para cada par de clientes
    # savings[i][j] = d(0,i) + d(0,j) - d(i,j)
    savings = []
    for i in range(1, n + 1):
        row = []
        for j in range(i + 1, n + 1):
            s = dist_to_depot[i - 1] + dist_to_depot[j - 1] - euclidean_distance(coords[i], coords[j])
            row.append((s, i, j))
        savings.extend(row)
    
    # Ordena savings em ordem decrescente
    savings.sort(reverse=True)
    
    # Inicializa cada cliente em sua propria rota
    routes = [[0, i, 0] for i in range(1, n + 1)]
    route_load = [demands[i] for i in range(1, n + 1)]
    in_route = {i: i - 1 for i in range(1, n + 1)}  # cliente -> indice da rota
    
    # Lista de clientes nas extremidades de cada rota (para verificacao rapida)
    route_ends = [[1, -1] for _ in range(n)]  # [primeiro, ultimo] cliente em cada rota
    
    for _, i, j in savings:
        if _time.time() > t_start + time_limit - 1.0:
            break
            
        route_i = in_route.get(i)
        route_j = in_route.get(j)
        
        if route_i is None or route_j is None or route_i == route_j:
            continue
        
        # Verifica se i e j estao nas extremidades de suas rotas
        # i deve ser primeiro ou ultimo em sua rota
        # j deve ser primeiro ou ultimo em sua rota
        ends_i = route_ends[route_i]
        ends_j = route_ends[route_j]
        
        i_at_end = (i == ends_i[0] or i == ends_i[1])
        j_at_end = (j == ends_j[0] or j == ends_j[1])
        
        if not (i_at_end and j_at_end):
            continue
        
        # Verifica capacidade
        if route_load[route_i] + route_load[route_j] > capacity:
            continue
        
        # Determina como concatenar as rotas
        # Rotas sao do tipo [0, ..., 0]
        route_i_obj = routes[route_i]
        route_j_obj = routes[route_j]
        
        # Decide orientacao para minimizar distancia
        # Opcoes: i...0 + 0...j ou i...0 + j...0 (inverte rota j)
        if i == ends_i[0]:  # i eh primeiro na rota i
            if j == ends_j[0]:  # j eh primeiro na rota j
                # Concatena: rota_i + rota_j_invertida
                new_route = route_i_obj + route_j_obj[-2:0:-1] + [0]
            else:  # j eh ultimo na rota j
                # Concatena: rota_i + rota_j
                new_route = route_i_obj + route_j_obj[1:]
        else:  # i eh ultimo na rota i
            if j == ends_j[0]:  # j eh primeiro na rota j
                # Concatena: rota_j_invertida + rota_i
                new_route = route_j_obj[-2:0:-1] + [0] + route_i_obj[1:]
            else:  # j eh ultimo na rota j
                # Concatena: rota_j + rota_i_invertida
                new_route = route_j_obj + route_i_obj[-2:0:-1] + [0]
        
        # Atualiza rotas
        routes[route_i] = new_route
        routes[route_j] = [0, 0]  # rota vazia
        route_load[route_i] += route_load[route_j]
        route_load[route_j] = 0
        
        # Atualiza extremidades
        if len(new_route) > 2:
            route_ends[route_i] = [new_route[1], new_route[-2]]
        
        # Atualiza mapeamento para clientes da rota j
        for node in new_route:
            if 1 <= node <= n:
                in_route[node] = route_i
    
    # Remove rotas vazias
    routes = [r for r in routes if len(r) > 2]

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
    while _time.time() < t_start + time_limit - 0.5:  # reservar 0.5s para seguranca
        routes_before = [list(r) for r in routes]
        total_dist_before = total_distance(routes, coords)
        
        routes = or_opt(routes, coords, demands, capacity)
        
        total_dist_after = total_distance(routes, coords)
        
        if total_dist_after >= total_dist_before - 1e-9:
            # Sem melhoria, restaurar e sair
            routes = routes_before
            break
    
    return routes