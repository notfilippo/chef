import asyncio
import subprocess
from pathlib import Path

from rich.console import Console
from rich.live import Live

from ..claude import claude_call
from ..context import Context
from .display import TaskDisplay
from .worktree import get_diff, get_repo_root, git_apply

console = Console(stderr=True)

_COMMIT_PROMPT = """\
Write a git commit message for the following diff.
Use the conventional commits format (type: description).
Optionally add a blank line followed by a short body if the change warrants explanation.
Output only the commit message, nothing else. Do not wrap it in quotes or any other formatting.
"""


def _git_commit(path: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, capture_output=True)
    result = subprocess.run(
        ["git", "commit", "-m", message], cwd=path, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or f"git commit failed (exit {result.returncode})"
        )
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True
    ).strip()


async def commit_op(contexts: list[Context], hint: str | None = None) -> list[Context]:
    assert contexts, "no input contexts"

    repo_root = get_repo_root()

    console.print(f"[dim]committing {len(contexts)} context(s)[/dim]")
    display = TaskDisplay([f"commit {i + 1}" for i in range(len(contexts))])
    results: list[Context | None] = []

    with Live(display, console=console, refresh_per_second=4):
        for i, ctx in enumerate(contexts):
            task = display.tasks[i]
            try:
                if ctx.diff:
                    await asyncio.to_thread(git_apply, repo_root, ctx.diff)

                diff = ctx.diff or await asyncio.to_thread(get_diff, repo_root)
                if not diff:
                    task.set_status("done")
                    results.append(ctx)
                    continue

                prompt = _COMMIT_PROMPT
                if hint:
                    prompt += f"\nHint: {hint}\n"
                prompt += f"\n```diff\n{diff}\n```"

                task.set_status("running")
                msg_ctx = await claude_call(
                    Context(value=prompt), repo_root, on_event=task.add_event
                )
                message = msg_ctx.value.strip()

                sha = await asyncio.to_thread(_git_commit, repo_root, message)
                task.set_status("done")
                task.add_event("text", f"{sha[:8]} {message}")
                results.append(Context(value=sha, session_id=ctx.session_id))
            except Exception as e:
                task.set_status("error")
                task.add_event("text", str(e))
                results.append(None)

    return [ctx for ctx in results if ctx is not None]
