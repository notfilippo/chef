import asyncio

from rich.console import Console
from rich.live import Live

from ..claude import claude_call
from ..context import Context
from .display import TaskDisplay
from .worktree import get_diff, worktree

console = Console(stderr=True)

_MAP_PROMPT = """\
Complete the task precisely. Make all changes directly in the codebase.
Do not explain or summarize what you did.
"""


async def map_op(contexts: list[Context], prompt: str) -> list[Context]:
    assert contexts, "no input contexts"
    assert prompt, "missing prompt argument"

    console.print(f"[dim]mapping {len(contexts)} context(s)[/dim]")
    display = TaskDisplay([f"map {i + 1}" for i in range(len(contexts))])

    async def call(ctx: Context, i: int) -> Context | None:
        task = display.tasks[i]
        try:
            async with worktree(lambda s: task.set_status(s)) as wt:
                task.set_status("running")
                call_ctx = Context(
                    value=f"{_MAP_PROMPT}\n{prompt}\n\n{ctx.value}",
                    session_id=ctx.session_id,
                    forked=ctx.forked,
                )
                res_ctx = await claude_call(call_ctx, wt, on_event=task.add_event)
                res_ctx.diff = get_diff(wt)
                task.set_status("done")
                return res_ctx
        except Exception as e:
            task.set_status("error")
            task.add_event("text", str(e))
            return None

    with Live(display, console=console, refresh_per_second=4):
        results = await asyncio.gather(
            *[call(ctx, i) for i, ctx in enumerate(contexts)]
        )
    return [ctx for ctx in results if ctx is not None]
