# Agent Related

This repository contains experimental projects and runnable examples built while learning about AI agents.

## 📁 Directory Overview

- **`DeepResearch/`**: A lightweight Go-based research agent that follows a complete loop: generate query → web research → reflection → finalize answer with citations.
- **`miniCoder/`**: A lightweight, interactive AI coding assistant CLI in Python. It acts as an autonomous pair-programmer in the terminal, featuring multi-model support (Claude, DeepSeek, etc.), built-in tools (bash, file operations, search), and session management via slash commands.
- **`workflow/`**: Minimal runnable examples of classic agent workflow patterns (using LangGraph + LangChain):
  - *Routing*: Dispatch requests to specialized sub-agents.
  - *Parallelization*: Execute parallel guardrails or voting patterns.
  - *Orchestrator-Workers*: Decompose tasks for parallel workers, then synthesize.
  - *Evaluator-Optimizer*: An evaluate-and-improve loop (generate → evaluate → revise).
- **`tool/`**: Examples of tool systems and calling strategies:
  - `langgraph-mcp/`: Integrates MCP (Model Context Protocol) perception/execution servers with a LangChain agent.
  - `tools_active_discovery/`: Experimental active tool discovery (inspired by MCP-Zero) that retrieves and activates tools on demand to save tokens.

## 📝 Notes

Each subdirectory contains its own `README.md` with detailed documentation and usage instructions.
