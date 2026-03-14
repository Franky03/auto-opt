# AutoOpt

[autoresearch](https://github.com/karpathy/autoresearch) but for optimization.

An autonomous agentic loop that iteratively improves heuristics for combinatorial optimization problems. You give it a problem, an initial (bad) heuristic, and a local LLM. It runs experiments in a loop: the AI proposes a code change, the orchestrator evaluates it on benchmark instances, and if the score improves, it commits. If it crashes or regresses, it reverts. Repeat.

The AI doesn't just suggest ideas — it writes the code, gets scored, and learns from what worked and what didn't.

## How it works

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   ┌──────────┐    propose     ┌──────────────┐      │
│   │  Local    │ ─────────────>│  heuristic.py │      │
│   │  LLM     │    code        │  (modified)   │      │
│   │ (Ollama) │<───────────────│               │      │
│   └──────────┘   history +    └──────┬────────┘      │
│        ▲         feedback            │               │
│        │                        evaluate             │
│        │                        on benchmarks        │
│        │                             │               │
│        │                             ▼               │
│        │                     ┌──────────────┐        │
│        └─────────────────────│  score better?│        │
│           rejected:          │              │        │
│           revert + log       └──────┬───────┘        │
│                                     │                │
│                              accepted:               │
│                              git commit + log        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

Three core files:

- **`program.md`** — research directives: what the AI should explore, what it shouldn't touch, constraints on the solution format. This is your "system prompt" for the optimization agent.
- **`heuristic.py`** — the living code. Starts as a dumb Nearest Neighbor, gets rewritten experiment by experiment into something much better.
- **`run_experiment.py`** — the orchestrator. Sends the current code + history to the LLM, extracts the proposed code, evaluates it, decides accept/reject, commits.

## First results: CVRP

The first target is the **Capacitated Vehicle Routing Problem (CVRP)** — a classic NP-hard problem in operations research. Given a set of customers with demands and a fleet of capacity-limited vehicles, find the shortest set of routes starting and ending at a depot that serves all customers.

Starting from a naive Nearest Neighbor heuristic (score ~1723), the agent autonomously evolved it through 24 experiments:

```
exp#2:  score 1722.9 -> 1685.6  (+2.2%)   # first improvement
exp#4:  score 1685.6 -> 1576.8  (+6.5%)   # added 2-opt local search
exp#5:  score 1576.8 -> 1531.6  (+2.9%)   # Clarke-Wright construction
exp#13: score 1531.6 -> 1529.8  (+0.1%)   # tuning
exp#14: score 1529.8 -> 1347.0  (+11.9%)  # inter-route operators
exp#24: score 1347.0 -> 1312.0  (+2.6%)   # ILS with Or-opt + Exchange
```

**Total improvement: ~24% reduction in distance**, fully autonomously. The heuristic went from a one-liner greedy to a full Iterated Local Search with Clarke-Wright construction, 2-opt, Or-opt segment relocation, exchange operators, and 2-opt* cross-exchange. All written by a 27B parameter model running locally.

## Quick start

```bash
# 1. Have Ollama running with your model
ollama list  # should show your model

# 2. Install dependencies
pip install requests

# 3. Run the autonomous loop
cd autoopt-cvrp
python run_experiment.py --n-experiments 100 --time-limit 30
```

The loop prints progress in real time. Each accepted improvement gets a git commit. You can stop and resume at any time — it picks up from the current `heuristic.py` and log.

## Structure

```
autoopt-cvrp/
├── program.md          # research directives for the agent
├── heuristic.py        # current heuristic (modified by the agent)
├── prepare.py          # instance generator + evaluator (fixed)
├── run_experiment.py   # orchestrator (fixed)
├── bks.py              # best known solutions for benchmarks
├── instances/          # CVRP benchmark instances (Augerat, Eilon)
└── results/            # experiment_log.jsonl
```

## Design choices

**Why a local model?** This runs a Qwen 27B via Ollama. It's free, private, and fast enough. You could swap in any model — the orchestrator just needs an endpoint that takes a prompt and returns text with a code block.

**Why git commits?** Every accepted improvement is a commit. This gives you a full history of what worked and what didn't, lets you bisect regressions, and makes the whole process auditable.

**Why one change at a time?** The agent proposes one modification per experiment. This makes it easy to attribute improvements (or regressions) to specific changes, and the history of accepted/rejected attempts becomes a useful signal for the agent itself.

**Why CVRP?** It's a well-studied problem with known benchmarks, it's NP-hard (so heuristics matter), and the solution space is rich enough that there are many different algorithmic ideas to explore — from construction heuristics to local search operators to metaheuristics.

## What's next

- More problem types (TSP, bin packing, job shop scheduling)
- Multi-objective optimization
- Better agent memory and strategy selection
- Evaluation against state-of-the-art solvers
