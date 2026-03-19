import asyncio
import subprocess
from pathlib import Path

from rich.console import Console
from rich.live import Live

from ..claude import claude_call
from ..context import Context
from .display import TaskDisplay
from .worktree import worktree

console = Console(stderr=True)

_COMMIT_PROMPT = """\
Write a concise git commit message for the following diff.
Output only the commit message, nothing else. Use the conventional commits format (type: description).
"""


def _git_apply(wt: Path, diff: str) -> None:
    subprocess.run(
        ["git", "apply"], input=diff, cwd=wt, check=True, capture_output=True, text=True
    )


def _git_commit(wt: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=wt, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message], cwd=wt, check=True, capture_output=True
    )
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=wt, text=True
    ).strip()


async def commit_op(contexts: list[Context], hint: str | None = None) -> list[Context]:
    assert contexts, "no input contexts"

    console.print(f"[dim]committing {len(contexts)} context(s)[/dim]")
    display = TaskDisplay([f"commit {i + 1}" for i in range(len(contexts))])

    async def commit(ctx: Context, i: int) -> Context | None:
        if not ctx.diff:
            display.tasks[i].set_status("done")
            return ctx

        task = display.tasks[i]
        try:
            async with worktree() as wt:
                await asyncio.to_thread(_git_apply, wt, ctx.diff)

                prompt = _COMMIT_PROMPT
                if hint:
                    prompt += f"\nHint: {hint}\n"
                prompt += f"\n```diff\n{ctx.diff}\n```"

                task.set_status("running")
                msg_ctx = await claude_call(
                    Context(value=prompt), wt, on_event=task.add_event
                )
                message = msg_ctx.value.strip()

                sha = await asyncio.to_thread(_git_commit, wt, message)
                task.set_status("done")
                task.add_event("text", f"{sha[:8]} {message}")
                return Context(value=sha, session_id=ctx.session_id)
        except Exception as e:
            task.set_status("error")
            task.add_event("text", str(e))
            return None

    with Live(display, console=console, refresh_per_second=4):
        results = await asyncio.gather(
            *[commit(ctx, i) for i, ctx in enumerate(contexts)]
        )
    return [ctx for ctx in results if ctx is not None]
