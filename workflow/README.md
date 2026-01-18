# workflow

This directory contains several classic agent workflow examples (more “workflows” than fully autonomous agents), mainly inspired by:
https://www.anthropic.com/engineering/building-effective-agents

These examples use LangGraph + LangChain to represent patterns such as routing, parallelization, orchestrator-workers, and evaluator-optimizer as minimal runnable graphs.

## Quickstart

1) Install dependencies:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r workflow/requirement.txt
```

2) Configure model access:

```bash
export KIMI_API_KEY="YOUR_ACTUAL_KEY"
```

3) Run any example:

```bash
python workflow/routing.py
python workflow/parallelization.py
python workflow/orchestrator_workers.py "Write a product introduction for a new coffee machine"
python workflow/evaluator_optimizer.py
```

## Examples

### Routing

File: [routing.py](routing.py)

Key ideas:
- A router node classifies the request into exactly one category (general/refund/tech)
- The workflow dispatches to a specialized agent with its own tools and system prompt
- Useful when request types are clear and downstream handling differs significantly

Diagram: `picture/routing.png`

### Parallelization

File: [parallelization.py](parallelization.py)

Includes two parallelization demos:
- Sectioning (guardrails in parallel): generate an answer and run a safety check concurrently, then aggregate
- Voting: multiple reviewers analyze the same input in parallel, then the aggregator tallies votes

Diagram: `picture/parallelization.png`

### Orchestrator-Workers

File: [orchestrator_workers.py](orchestrator_workers.py)

Key ideas:
- The orchestrator decomposes the original task into 2–3 distinct approaches/styles
- A fan-out sends one subtask per worker (in parallel)
- The synthesizer aggregates all worker outputs into the final response

Diagram: `picture/orchestrator-workers.png`

### Evaluator-Optimizer

File: [evaluator_optimizer.py](evaluator_optimizer.py)

Key ideas:
- The generator produces an initial output and refines it based on feedback (demo uses literary translation)
- The evaluator acts as a strict critic and returns ACCEPT/REJECT plus actionable feedback
- Conditional edges create a loop: reject → revise; accept or max iterations → stop

Diagram: `picture/evaluator-optimizer.png`

## Structure

```text
workflow/
  picture/                   # Diagrams for each pattern
  evaluator_optimizer.py     # Evaluator-Optimizer loop
  orchestrator_workers.py    # Orchestrator-Workers fan-out/fan-in
  parallelization.py         # Parallel guardrails / parallel voting
  routing.py                 # Route to specialized agents
```
