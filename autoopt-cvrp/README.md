# AutoOpt-CVRP

Loop agentic autonomo que cria e melhora heuristicas para o Capacitated Vehicle Routing Problem (CVRP), usando um modelo de IA local via Ollama.

Inspirado no [autoresearch](https://github.com/karpathy/autoresearch) de Karpathy.

## Como funciona

1. O agente (Qwen local via Ollama) recebe o codigo atual da heuristica
2. Propoe uma modificacao para melhorar o score
3. O orquestrador aplica a mudanca e avalia nas 10 instancias de benchmark
4. Se o score medio melhorou: mantem e faz git commit
5. Se piorou ou crashou: reverte
6. Repete

## Quick start

```bash
# 1. Certifique-se de ter o Ollama rodando com o modelo
ollama list  # deve mostrar qwen-reasoning

# 2. Instale dependencias
pip install requests

# 3. Teste a heuristica inicial
python -c "
from prepare import generate_instance, evaluate_solution
from heuristic import solve
inst = generate_instance(50, 0)
sol = solve(inst)
print(evaluate_solution(sol, inst))
"

# 4. Rode o loop autonomo
python run_experiment.py --n-experiments 100 --time-limit 30
```

## Estrutura

```
prepare.py          -- gerador de instancias e avaliador (fixo)
heuristic.py        -- heuristica atual (modificada pelo agente)
program.md          -- diretrizes de pesquisa para o agente
run_experiment.py   -- orquestrador do loop agentic (fixo)
results/            -- logs de experimentos (experiment_log.jsonl)
```

## Opcoes

```
python run_experiment.py [--n-experiments N] [--time-limit T] [--model MODEL]

  --n-experiments   Numero de experimentos (default: 100)
  --time-limit      Segundos por instancia (default: 30)
  --model           Modelo Ollama (default: qwen-reasoning)
```

## Logs

Cada experimento gera uma linha em `results/experiment_log.jsonl`:

```json
{"id": 1, "accepted": true, "score_before": 1847.3, "score_after": 1791.2, "improvement_pct": 3.04, "description": "Adicionou 2-opt intra-rota"}
```
