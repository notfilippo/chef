import asyncio
import json
from collections.abc import Callable

from .context import Context


def _format_tool_use(name: str, inp: dict) -> str:
    match name:
        case "Read":
            return f"read {inp.get('file_path', '')}"
        case "Write":
            return f"write {inp.get('file_path', '')}"
        case "Edit":
            return f"edit {inp.get('file_path', '')}"
        case "Bash":
            cmd = inp.get("command", "")
            return f"bash {cmd[:80]}{'...' if len(cmd) > 80 else ''}"
        case "Glob":
            return f"glob {inp.get('pattern', '')}"
        case "Grep":
            return f"grep {inp.get('pattern', '')} {inp.get('path', '')}".strip()
        case _:
            return name.lower()


async def claude_call(
    ctx: Context,
    on_event: Callable[[str, str], None] | None = None,
) -> tuple[str, str]:
    args = [
        "claude",
        "-p",
        ctx.value,
        "--output-format",
        "stream-json",
        "--verbose",
        "--allowedTools",
        "Edit,Write,Read,Glob,Grep,Bash",
    ]
    if ctx.session_id:
        args += ["--resume", ctx.session_id]
        if ctx.forked:
            args += ["--fork-session"]

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=ctx.worktree,
        limit=2**24,
    )

    result = None
    session_id = None
    stderr_lines = []

    async for line in proc.stdout:
        text = line.decode().strip()
        if not text:
            continue
        try:
            event = json.loads(text)
        except json.JSONDecodeError:
            continue

        if event.get("type") == "assistant":
            if on_event:
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        on_event("text", block["text"])
                    elif block.get("type") == "tool_use":
                        on_event(
                            "tool_use",
                            _format_tool_use(block["name"], block.get("input", {})),
                        )
        elif event.get("type") == "result":
            result = event.get("result", "")
            session_id = event.get("session_id", "")

    async for line in proc.stderr:
        stderr_lines.append(line.decode())

    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("".join(stderr_lines).strip())

    return result, session_id
