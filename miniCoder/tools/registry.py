from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List


ToolExecutor = Callable[[Dict[str, Any]], str]


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]
    execute: ToolExecutor


_REGISTRY: Dict[str, ToolSpec] = {}
_CURRENT_WORKDIR: Path | None = None


def register_tool(spec: ToolSpec) -> None:
    if not spec.name or not isinstance(spec.name, str):
        raise ValueError("tool name required")
    _REGISTRY[spec.name] = spec


def get_tool_schemas() -> List[Dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_schema,
        }
        for spec in _REGISTRY.values()
    ]


def execute_tool(name: str, payload: Dict[str, Any]) -> str:
    spec = _REGISTRY.get(name)
    if not spec:
        return f"Error: unknown tool '{name}'"
    try:
        return spec.execute(payload)
    except Exception as exc:
        return f"Error: {exc}"


def _resolve_path(workdir: Path, path_value: str) -> Path:
    raw = Path(path_value)
    target = raw.resolve() if raw.is_absolute() else (workdir / raw).resolve()
    if target != workdir and workdir not in target.parents:
        raise ValueError(f"path escapes workdir: {path_value}")
    return target


def _bash_init(workdir: Path) -> ToolSpec:
    import subprocess

    def _run(payload: Dict[str, Any]) -> str:
        command = str(payload["command"])
        blocked_fragments = [
            "rm -rf /",
            "sudo ",
            " shutdown",
            "reboot",
            "> /dev/",
        ]
        if any(fragment in command for fragment in blocked_fragments):
            return "Error: dangerous command blocked"
        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return "Error: timeout after 120s"
        output = (completed.stdout + completed.stderr).strip()
        return output[:50_000] if output else "(no output)"

    return ToolSpec(
        name="bash",
        description="Run a shell command in the working directory.",
        input_schema={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
        execute=_run,
    )


def _read_file_init(workdir: Path) -> ToolSpec:
    def _run(payload: Dict[str, Any]) -> str:
        path = str(payload["path"])
        target = _resolve_path(workdir, path)
        if not target.exists():
            return f"Error: file not found: {path}"
        if not target.is_file():
            return f"Error: not a file: {path}"
        return target.read_text(encoding="utf-8")

    return ToolSpec(
        name="read_file",
        description="Read a UTF-8 text file from the working directory.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        execute=_run,
    )


def _write_file_init(workdir: Path) -> ToolSpec:
    def _run(payload: Dict[str, Any]) -> str:
        path = str(payload["path"])
        content = str(payload["content"])
        target = _resolve_path(workdir, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {path}"

    return ToolSpec(
        name="write_file",
        description="Write UTF-8 text content to a file in the working directory.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
        execute=_run,
    )


def _file_edit_init(workdir: Path) -> ToolSpec:
    def _run(payload: Dict[str, Any]) -> str:
        path = str(payload["path"])
        old = str(payload["old_text"])
        new = str(payload["new_text"])
        target = _resolve_path(workdir, path)
        if not target.exists():
            return f"Error: file not found: {path}"
        content = target.read_text(encoding="utf-8")
        if old not in content:
            return "Error: old_text not found"
        updated = content.replace(old, new)
        target.write_text(updated, encoding="utf-8")
        return f"Updated {path}"

    return ToolSpec(
        name="file_edit",
        description="Replace text in a UTF-8 file within the working directory.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
        execute=_run,
    )


def _glob_init(workdir: Path) -> ToolSpec:
    import glob

    def _run(payload: Dict[str, Any]) -> str:
        pattern = str(payload["pattern"])
        matches = glob.glob(str(workdir / pattern), recursive=True)
        rels = []
        for match in matches:
            candidate = Path(match).resolve()
            if not candidate.is_file():
                continue
            if candidate != workdir and workdir not in candidate.parents:
                continue
            rels.append(candidate.relative_to(workdir).as_posix())
        return "\n".join(rels) if rels else "(no matches)"

    return ToolSpec(
        name="glob",
        description="Find files matching a pattern (supports **). Returns newline-separated relative paths.",
        input_schema={
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
        execute=_run,
    )


def _grep_init(workdir: Path) -> ToolSpec:
    import re

    def _run(payload: Dict[str, Any]) -> str:
        pattern = str(payload["pattern"])
        path_value = str(payload.get("path", "")).strip()
        try:
            rx = re.compile(pattern, re.MULTILINE)
        except re.error as exc:
            return f"Error: invalid regex: {exc}"
        roots: Iterable[Path]
        if path_value:
            base = _resolve_path(workdir, path_value)
            if base.is_file():
                roots = [base]
            else:
                roots = (p for p in base.rglob("*") if p.is_file())
        else:
            roots = (p for p in workdir.rglob("*") if p.is_file())
        lines: List[str] = []
        for file in roots:
            try:
                text = file.read_text(encoding="utf-8")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if rx.search(line):
                    rel = file.resolve().relative_to(workdir).as_posix()
                    lines.append(f"{rel}:{i}:{line}")
                    if len(lines) >= 5000:
                        lines.append("...truncated...")
                        return "\n".join(lines)
        return "\n".join(lines) if lines else "(no matches)"

    return ToolSpec(
        name="grep",
        description="Regex search across files within workdir. Returns lines as path:line:text",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["pattern"],
        },
        execute=_run,
    )


def _web_fetch_init(_workdir: Path) -> ToolSpec:
    def _run(payload: Dict[str, Any]) -> str:
        url = str(payload["url"])
        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=20) as resp:
                raw = resp.read()
                text = raw.decode("utf-8", errors="replace")
                if len(text) > 50_000:
                    text = text[:50_000]
                return text
        except Exception as exc:
            return f"Error: fetch failed: {exc}"

    return ToolSpec(
        name="web_fetch",
        description="Fetch text content from a URL (UTF-8, truncated).",
        input_schema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
        execute=_run,
    )


def _init_defaults(workdir: Path) -> None:
    _REGISTRY.clear()
    register_tool(_bash_init(workdir))
    register_tool(_read_file_init(workdir))
    register_tool(_write_file_init(workdir))
    register_tool(_file_edit_init(workdir))
    register_tool(_glob_init(workdir))
    register_tool(_grep_init(workdir))
    register_tool(_web_fetch_init(workdir))

def initialize_tools(workdir: Path | None = None) -> None:
    global _CURRENT_WORKDIR
    wd = workdir or Path.cwd()
    resolved = wd.resolve()
    if _CURRENT_WORKDIR != resolved:
        _CURRENT_WORKDIR = resolved
        _init_defaults(resolved)


if not _REGISTRY:
    initialize_tools()
