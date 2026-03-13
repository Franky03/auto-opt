# Diretrizes de Pesquisa -- AutoOpt CVRP

## Objetivo

Minimizar a distancia total percorrida em instancias CVRP com 50 clientes.
A metrica principal eh `score` (retornada por `evaluate_solution`).
**Menor eh melhor.**

## Ponto de partida

A geracao atual implementa Nearest Neighbor Greedy -- uma heuristica construtiva
simples sem nenhuma fase de melhoria. Ha muito espaco para melhorar.

## Direcoes de pesquisa sugeridas (em ordem de impacto esperado)

1. Adicionar uma fase de melhoria local apos a construcao (2-opt intra-rota eh um bom comeco)
2. Implementar Or-opt (realocar clientes individuais entre rotas)
3. Melhorar a fase construtiva (savings algorithm de Clarke-Wright, por exemplo)
4. Implementar busca local inter-rotas (2-opt*, cross-exchange)
5. Adicionar perturbacao para escapar de otimos locais (ILS, LNS)
6. Usar o time_limit inteligentemente: dedicar a maior parte do tempo a melhoria local iterativa

## Restricoes absolutas

- A funcao principal DEVE se chamar `solve(instance, time_limit)`
- O time_limit DEVE ser respeitado (use `time.time()` para controlar)
- Apenas bibliotecas padrao do Python sao permitidas
- A solucao retornada DEVE estar no formato `[[0,...,0], ...]`

## O que NAO fazer

- Nao altere `prepare.py`
- Nao implemente solucionadores exatos (Branch and Bound, etc.) -- o foco eh heuristicas
- Nao use numpy, scipy, OR-Tools ou qualquer biblioteca externa
- Nao mude a assinatura da funcao `solve(instance, time_limit)`

## Criterio de aceitacao

Uma nova versao eh mantida se o score medio nas 10 instancias de benchmark
for estritamente menor que o score medio da versao anterior.

## Dicas de implementacao

- Sempre controle o tempo com `time.time()` e pare antes de estourar o limite
- Prefira mudancas incrementais: uma melhoria de cada vez
- Se uma mudanca radical crashar, tente uma versao mais simples primeiro
- O Nearest Neighbor eh ruim -- qualquer melhoria local ja vai dar ganho significativo
