# agent_related

This repository contains a collection of example projects and experiments I built while learning about AI agents.

## Directory Overview

### DeepResearch/
A lightweight “research agent” implemented with Go + eino. The core loop is:
generate search queries → web research & evidence notes → reflection to find gaps and iterate → finalize an answer with citations.

### workflow/
Minimal runnable examples of classic agent workflow patterns, implemented with LangGraph + LangChain, including:
- routing: route requests to specialized handlers/sub-agents
- parallelization: parallel guardrails / parallel voting patterns
- orchestrator_workers: an orchestrator decomposes tasks, workers run in parallel, then results are synthesized
- evaluator_optimizer: an evaluate-and-improve loop (generate → evaluate → revise → accept/stop)

### tool/
A collection of examples related to tool systems, tool servers, and tool-calling strategies.

#### tool/langgraph-mcp/
An example that integrates MCP (Model Context Protocol) “perception tools” and “execution tools” servers with a LangChain agent. It includes:
- an MCP server providing web/document/media parsing, search, public/private data access, and filesystem operations
- an MCP server for code execution, file edit/write, a virtual terminal, and external integrations (e.g., Calendar, GitHub PR)
- an interactive agent entry that uses an LLM to drive conversation and tool calls

#### tool/tools_active_discovery/
An experimental implementation of Active Tool Discovery inspired by MCP‑Zero: start with a minimal initial toolset, then discover/activate tools on demand via natural-language retrieval to reduce token cost and noise and improve robustness.

## Notes
- Each subdirectory usually includes its own README with more details about the specific project.
