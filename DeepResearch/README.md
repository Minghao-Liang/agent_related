# DeepResearch (Go)

A lightweight research agent example that implements an iterative workflow:
"generate search queries → web research → reflection to fill gaps → finalize an answer with citations".

The overall idea and flow are inspired by [google-gemini/gemini-fullstack-langgraph-quickstart](https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart): dynamically generate search queries, summarize evidence from web search results, reflect to identify knowledge gaps and iterate with follow-up searches, then synthesize a final answer with citations. This project re-implements that workflow in Go, using CloudWeGo Eino `compose` for graph orchestration, DuckDuckGo (HTML) for web search, and an OpenAI-compatible API for LLM calls (defaults are set up for Kimi/Moonshot).

## Project Structure

- `cmd/cli_research/`: CLI entry that runs one full research session and writes `output.md`
- `internal/agent/`: agent graph (generate_query / web_research / reflection / finalize_answer) and state
- `internal/search/`: search client interface and DuckDuckGo implementation (`internal/search/ddg`)
- `internal/llm/`: LLM abstraction and JSON-structured output generator
- `internal/prompts/`: prompt provider and template rendering (built-ins in `internal/prompts/builtin`)
- `internal/citation/`: citation building and replacement from `([1])` to markdown links
- `test/`: basic integration test (validates events and main flow)

## Quickstart

### 1) Environment Variables

Recommended (all optional; defaults apply if unset):

- `BASE_URL`: base URL for an OpenAI-compatible API (default: `https://api.moonshot.cn/v1`)
- `KIMI_API_KEY`: API key (default: literal string `KIMI_API_KEY`; real requests will usually fail if unset)
- `QUERY_GENERATOR_MODEL`: model for query generation (default: `kimi-k2-0905-preview`)
- `REFLECTION_MODEL`: model for reflection and follow-up queries (default: `kimi-k2-0905-preview`)
- `ANSWER_MODEL`: model for final answer synthesis (default: `kimi-k2-thinking`)
- `TEMPERATURE_QUERY`: temperature for query generation (default: `0`)
- `TEMPERATURE_REFLECT`: temperature for reflection (default: `1.0`)
- `TEMPERATURE_ANSWER`: temperature for final answer (default: `0`)
- `MAX_RETRIES`: maximum retries (default: `3`)

Example (macOS / zsh):

```bash
export BASE_URL="https://api.moonshot.cn/v1"
export KIMI_API_KEY="YOUR_ACTUAL_KEY"
```

### 2) Run the CLI

```bash
cd DeepResearch
go run ./cmd/cli_research \
  -question "What are the major trends in agentic AI systems in 2025?" \
  -initial-queries 3 \
  -max-loops 3 \
  -reasoning-model "kimi-k2-thinking"
```

The CLI prints step events (generate_query / web_research / reflection / finalize_answer) to stdout and writes the final answer to `output.md`.

## Workflow Overview

1. **Generate Query**: generate an initial batch of search queries (JSON-structured output)
2. **Web Research**: search the web per query and produce evidence-based notes with `([1])`, `([2])`, ... citation placeholders
3. **Reflection**: decide whether the information is sufficient, identify knowledge gaps, and propose follow-up queries (iterative)
4. **Finalize Answer**: synthesize the final answer and replace short refs with markdown links

## Tests

```bash
go test ./...
```

## Reference

- [google-gemini/gemini-fullstack-langgraph-quickstart](https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart) — an end-to-end example of an iterative research agent (query generation, web research, reflection, and citation-backed synthesis) that inspired this project’s workflow.
