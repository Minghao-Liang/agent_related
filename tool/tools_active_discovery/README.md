# Tools Active Discovery (MCP‑Zero Inspired)

This directory implements an active tool discovery workflow that keeps the initial toolset minimal and retrieves/activates tools on demand during reasoning. The approach is inspired by MCP‑Zero: instead of injecting all tool schemas into the prompt up front, the agent uses natural language queries to discover only the tools it needs, reducing token cost, noise, and improving robustness.

Reference paper: MCP‑Zero — Active Tool Discovery for Autonomous LLM Agents
https://arxiv.org/abs/2506.01056

## Directory Structure
```
tool/tools_active_discovery/
  ├─ experiment/
  │  ├─ run_experiment.py         # Experiment script (control vs. experimental flow, metrics)
  │  └─ tool_registry.py          # Tool registration & search (keyword weighting + embeddings)
  └─ perception-tools/            # MCP tool server (domain tools)
     ├─ server.py                 # MCP server entry, registers tools
     ├─ pubchem_tools.py          # Chemistry database (PubChem)
     ├─ wiki_enhanced.py          # Wikipedia enhanced tools
     ├─ yahoo_finance_tools.py    # Financial market (Yahoo Finance)
     ├─ google_search_enhanced.py # Search enhancement
     ├─ ...                       # Other tools (filesystem, media, arxiv, wayback, etc.)
```

## Method Overview
- Minimal initial toolset: only `code_interpreter` and `discover_tools` are injected, avoiding a large prompt full of tool schemas.
- Active discovery: when current tools are insufficient, the model calls `discover_tools` and describes its need (e.g., “latest NVDA stock price”), and the registry returns the most relevant tools with a compact schema.
- Dynamic activation: discovered tools are added to the current context and can be invoked directly in the next step (e.g., `yfinance_quote`).
- Retrieval mechanics:
  - Keyword weighting (domain boosts): `tool_registry.py` increases relevance for financial terms like `stock`, `finance`, `price`, `market`, `ticker`, `quote` to surface financial tools for financial tasks.
  - Semantic embeddings (optional): if `SILICONFLOW_API_KEY` is set, high-quality embedding retrieval (Qwen Embedding) is used to improve recall and ranking stability.

## Metrics
- `tools_initial`: number of tools available at task start (small for experimental; large for control).
- `tools_final`: number of tools available at task end (experimental grows as tools are discovered; control stays constant).
- `discovered_tools_count`: count of tools added via `discover_tools`.
- `context_tool_count_over_time`: per‑step evolution of available tool count.
- `tool_calls`, `used_tools_sequence`: number and sequence of tool invocations.
- `input_tokens`, `output_tokens`, `total_tokens`: token usage (typically much lower than “inject all tools”).

## Quick Start
1. Prepare Python environment and dependencies (e.g., `langchain_openai`, `langchain_core`, `langchain_mcp_adapters`).
2. Optional: set environment variables to enable embedding retrieval (works without them using keyword weights).
   - `SILICONFLOW_API_KEY`: SiliconFlow API key
   - `SILICONFLOW_API_BASE` (optional, default `https://api.siliconflow.cn/v1`)
   - `SILICONFLOW_EMBEDDING_MODEL` (optional, default `Qwen/Qwen3-Embedding-4B`)
3. Run the experiment:
   - `python tool/tools_active_discovery/experiment/run_experiment.py`
4. Inspect logs:
   - Check `Discovery preview (top-5)` to confirm domain‑relevant tools (e.g., `yfinance_quote`, `stock_price`) are surfaced.
   - Observe tool discovery and activation messages (`>>> ACTIVATING NEW TOOL: ...`) and the final answer quality.

## Task Examples
- Financial task:
  - “Inquire about NVIDIA Corporation (NVDA) latest stock price and analyze related news.”
  - Flow: step 1 `discover_tools` → activate `yfinance_quote`, `yfinance_historical` → return market data → optionally discover reading tools for news analysis.
- Cross‑domain task:
  - “Fetch Caffeine SMILES and molecular weight (PubChem), get a Wikipedia summary, and retrieve Pfizer (PFE) latest stock price; then summarize.”
  - Flow: chemistry and finance tools are discovered and activated independently as needed.

## Comparison with Inject‑All
- Token efficiency: only necessary tool definitions are added, making prompts shorter and cheaper.
- Noise resistance: avoids overwhelming the model with many tools at once, reducing confusion and hallucinations.
- Auditability: discovery and activation are clearly logged for debugging and review.

## Troubleshooting
- Tool server path: `MultiServerMCPClient` uses an absolute path to `perception-tools/server.py`. If it fails, verify the path matches your project layout.
- Embeddings not enabled: without `SILICONFLOW_API_KEY`, retrieval falls back to keyword weights; richer task descriptions and domain boosts can still yield good results.
- Financial tools not discovered:
  - Ensure the task includes domain terms like `stock`, `finance`, `price`, `ticker`, `quote`.
  - Confirm `tool_registry.py` includes financial keyword weighting and a correct `api_base`.
