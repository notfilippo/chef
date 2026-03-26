import asyncio

from rich.console import Console
from rich.live import Live

from ..claude import claude_call
from ..context import Context
from .display import TaskDisplay
from .registry import operator
from .worktree import get_diff, get_repo_root, worktree

console = Console(stderr=True)

_REDUCE_PROMPT = """\
Complete the task precisely. Make all changes directly in the codebase.
Do not explain or summarize what you did.
The original repository is at {repo_root}.
"""


@operator
async def reduce(contexts: list[Context], arg: str) -> list[Context]:
    """Merge all contexts into one with Claude."""
    assert contexts, "no input contexts"
    assert arg, "missing prompt argument"

    console.print(f"[dim]reducing {len(contexts)} context(s)[/dim]")

    parts = []
    for i, ctx in enumerate(contexts, 1):
        part = f"--- Variant {i} ---\n{ctx.value}"
        if ctx.diff:
            part += f"\n\nChanges:\n```diff\n{ctx.diff}\n```"
        parts.append(part)
    combined = "\n\n".join(parts)

    display = TaskDisplay(["reduce"])
    task = display.tasks[0]

    with Live(display, console=console, refresh_per_second=4):
        async with worktree(lambda s: task.set_status(s)) as wt:
            task.set_status("running")
            merged_ctx = Context(
                value=f"{_REDUCE_PROMPT.format(repo_root=get_repo_root())}\n{arg}\n\n{combined}"
            )
            try:
                res_ctx = await claude_call(merged_ctx, wt, on_event=task.add_event)
                res_ctx.diff = get_diff(wt)
                task.set_status("done")
            except Exception as e:
                task.set_status("error")
                task.add_event("text", str(e))
                raise

    return [res_ctx]
