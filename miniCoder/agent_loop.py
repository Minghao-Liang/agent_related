#!/usr/bin/env python3
from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from tools.registry import execute_tool, get_tool_schemas, initialize_tools


DEFAULT_MODEL = os.getenv("MODEL_ID") or os.getenv(
    "MODEL_NAME",
    "claude-sonnet-4-20250514",
)
DEFAULT_MAX_TOKENS = 8_000
ENV_PATH = Path(__file__).with_name(".env")
WORKDIR = Path(os.getenv("MINICODER_WORKDIR", Path.cwd())).resolve()


def resolve_max_turns() -> int:
    raw = os.getenv("MINICODER_MAX_TURNS", "16")
    try:
        value = int(raw)
    except ValueError:
        return 16
    return value if value > 0 else 16


DEFAULT_MAX_TURNS = resolve_max_turns()

def build_system_prompt(workdir: Path) -> str:
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    
    # Get a lightweight directory tree (up to 2 levels deep, max 50 items)
    tree_items = []
    try:
        for root, dirs, files in os.walk(workdir):
            # Exclude common hidden/virtualenv dirs to avoid clutter
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", "venv", "env")]
            level = str(root).replace(str(workdir), "").count(os.sep)
            if level > 1 or len(tree_items) > 50:
                continue
            indent = "  " * level
            tree_items.append(f"{indent}{os.path.basename(root)}/")
            for f in files:
                if not f.startswith("."):
                    tree_items.append(f"{indent}  {f}")
                    if len(tree_items) > 50:
                        break
    except Exception:
        pass
    
    tree_str = "\n".join(tree_items[:50])
    if len(tree_items) > 50:
        tree_str += "\n  ... (truncated)"

    return (
        f"You are miniCoder, a helpful AI coding assistant.\n\n"
        f"### Environment\n"
        f"- OS: {os_info}\n"
        f"- Working Directory: {workdir}\n\n"
        f"### Directory Structure (Preview)\n"
        f"{tree_str}\n\n"
        f"### Instructions\n"
        f"Use your tools to inspect files, run commands, and write code. "
        f"Always act proactively to solve the user's request. "
        f"Finish the task completely before stopping."
    )

SYSTEM_PROMPT = build_system_prompt(WORKDIR)
initialize_tools(WORKDIR)
TOOLS = get_tool_schemas()


ToolExecutor = Callable[[str, dict[str, Any]], str]


@dataclass
class LoopResult:
    final_text: str
    turns: int
    messages: list[dict[str, Any]]
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class SessionStats:
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class SlashCommandResult:
    handled: bool
    should_exit: bool = False
    output: str = ""


def extract_text(content: list[Any]) -> str:
    pieces: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text" and hasattr(block, "text"):
            pieces.append(block.text)
    return "".join(pieces).strip()


def _extract_usage(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    return input_tokens, output_tokens


def handle_slash_command(
    user_input: str,
    history: list[dict[str, Any]],
    stats: SessionStats,
) -> SlashCommandResult:
    text = user_input.strip()
    if not text.startswith("/"):
        return SlashCommandResult(handled=False)
    parts = text.split(maxsplit=1)
    name = parts[0].lower()
    if name == "/help":
        return SlashCommandResult(
            handled=True,
            output=(
                "Available commands:\n"
                "/help  Show this help\n"
                "/clear Clear conversation history and counters\n"
                "/cost  Show session turn/token usage\n"
                "/exit  Exit miniCoder"
            ),
        )
    if name == "/clear":
        history.clear()
        stats.turns = 0
        stats.input_tokens = 0
        stats.output_tokens = 0
        return SlashCommandResult(
            handled=True,
            output="Conversation history and usage counters cleared.",
        )
    if name == "/cost":
        return SlashCommandResult(
            handled=True,
            output=(
                f"Turns: {stats.turns}\n"
                f"Input tokens: {stats.input_tokens}\n"
                f"Output tokens: {stats.output_tokens}\n"
                f"Total tokens: {stats.input_tokens + stats.output_tokens}"
            ),
        )
    if name in {"/exit", "/quit"}:
        return SlashCommandResult(handled=True, should_exit=True, output="Bye.")
    return SlashCommandResult(
        handled=True,
        output=f"Unknown command: {name}. Use /help.",
    )


def run_agent_loop(
    *,
    client: Any,
    model: str,
    system_prompt: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    execute_tool: ToolExecutor,
    max_turns: int = DEFAULT_MAX_TURNS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    use_stream: bool = False,
    on_text_delta: Callable[[str], None] | None = None,
    on_tool_event: Callable[[str, str], None] | None = None,
) -> LoopResult:
    turns = 0
    input_tokens = 0
    output_tokens = 0
    while True:
        if turns >= max_turns:
            raise RuntimeError("max turns exceeded")
        turns += 1
        if not use_stream:
            response = client.messages.create(
                model=model,
                system=system_prompt,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
            )
        else:
            with client.messages.stream(
                model=model,
                system=system_prompt,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
            ) as stream:
                for chunk in getattr(stream, "text_stream", []):
                    if on_text_delta:
                        on_text_delta(chunk)
                if hasattr(stream, "get_final_message"):
                    response = stream.get_final_message()
                elif hasattr(stream, "get_final_response"):
                    response = stream.get_final_response()
                else:
                    response = getattr(stream, "_final_response")
        in_used, out_used = _extract_usage(response)
        input_tokens += in_used
        output_tokens += out_used
        messages.append({"role": "assistant", "content": response.content})
        tool_uses = [
            block
            for block in response.content
            if getattr(block, "type", None) == "tool_use"
        ]
        if response.stop_reason != "tool_use" or not tool_uses:
            return LoopResult(
                final_text=extract_text(response.content),
                turns=turns,
                messages=messages,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        results = []
        for block in tool_uses:
            if on_tool_event:
                on_tool_event(block.name, "start")
            tool_output = execute_tool(block.name, dict(block.input))
            if on_tool_event:
                on_tool_event(block.name, "end")
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": tool_output,
                }
            )
        messages.append({"role": "user", "content": results})


def build_client() -> Any:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise RuntimeError(
            "python-dotenv is required. Install with: uv pip install -r requirements.txt"
        ) from exc
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError(
            "anthropic is required. Install with: uv pip install -r requirements.txt"
        ) from exc

    load_dotenv(dotenv_path=ENV_PATH, override=True)
    if os.getenv("ANTHROPIC_BASE_URL"):
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
    return Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        base_url=os.getenv("ANTHROPIC_BASE_URL"),
    )


def main() -> None:
    client = build_client()
    history: list[dict[str, Any]] = []
    stats = SessionStats()
    rich_console = None
    Live = None
    Panel = None
    Spinner = None
    try:
        from rich.console import Console
        from rich.live import Live as _Live
        from rich.panel import Panel as _Panel
        from rich.spinner import Spinner as _Spinner

        rich_console = Console()
        Live = _Live
        Panel = _Panel
        Spinner = _Spinner
    except Exception:
        rich_console = None
    if rich_console:
        rich_console.print(f"[bold green]miniCoder[/] ready in {WORKDIR}")
    else:
        print(f"miniCoder ready in {WORKDIR}")
    while True:
        try:
            user_input = input("miniCoder >> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_input.lower() in {"", "q", "quit", "exit"}:
            break
        slash_result = handle_slash_command(user_input, history, stats)
        if slash_result.handled:
            if slash_result.output:
                if rich_console:
                    rich_console.print(slash_result.output)
                else:
                    print(slash_result.output)
            if slash_result.should_exit:
                break
            continue
        history.append({"role": "user", "content": user_input})
        if Live and Panel:
            buffer: list[str] = []
            tool_status: str | None = None
            with Live(Panel("", title="miniCoder"), console=rich_console, refresh_per_second=12) as live:
                def on_delta(chunk: str) -> None:
                    buffer.append(chunk)
                    live.update(Panel("".join(buffer), title="miniCoder"))

                def on_tool(tool: str, status: str) -> None:
                    nonlocal tool_status
                    tool_status = f"{tool} {status}"
                    live.update(Panel("".join(buffer) + f"\n\n[{tool_status}]", title="miniCoder"))

                try:
                    result = run_agent_loop(
                        client=client,
                        model=DEFAULT_MODEL,
                        system_prompt=SYSTEM_PROMPT,
                        messages=history,
                        tools=TOOLS,
                        execute_tool=execute_tool,
                        max_turns=DEFAULT_MAX_TURNS,
                        use_stream=True,
                        on_text_delta=on_delta,
                        on_tool_event=on_tool,
                    )
                except RuntimeError as exc:
                    if "max turns exceeded" not in str(exc):
                        raise
                    warning = (
                        f"Reached max turns ({DEFAULT_MAX_TURNS}). "
                        "Try increasing MINICODER_MAX_TURNS or narrow the request."
                    )
                    live.update(Panel("".join(buffer) + f"\n\n{warning}", title="miniCoder"))
                    if rich_console:
                        rich_console.print(f"\n{warning}")
                    continue
            if result.final_text and not buffer:
                rich_console.print(result.final_text)
            stats.turns += result.turns
            stats.input_tokens += result.input_tokens
            stats.output_tokens += result.output_tokens
        else:
            try:
                result = run_agent_loop(
                    client=client,
                    model=DEFAULT_MODEL,
                    system_prompt=SYSTEM_PROMPT,
                    messages=history,
                    tools=TOOLS,
                    execute_tool=execute_tool,
                    max_turns=DEFAULT_MAX_TURNS,
                    use_stream=False,
                )
            except RuntimeError as exc:
                if "max turns exceeded" not in str(exc):
                    raise
                print(
                    f"Reached max turns ({DEFAULT_MAX_TURNS}). "
                    "Try increasing MINICODER_MAX_TURNS or narrow the request."
                )
                continue
            if result.final_text:
                print(result.final_text)
            stats.turns += result.turns
            stats.input_tokens += result.input_tokens
            stats.output_tokens += result.output_tokens


if __name__ == "__main__":
    main()
