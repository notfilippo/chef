import asyncio

from rich.console import Console
from rich.live import Live

from ..claude import claude_call
from ..context import Context
from .display import TaskDisplay
from .worktree import has_changes, pool


async def map_op(contexts: list[Context], prompt: str) -> list[Context]:
    assert contexts, "no input contexts"
    assert prompt, "missing prompt argument"

    console = Console(stderr=True)
    console.print(f"[dim]mapping {len(contexts)} context(s)[/dim]")
    display = TaskDisplay([f"map {i + 1}" for i in range(len(contexts))])

    async def call(ctx: Context, i: int) -> Context | None:
        task = display.tasks[i]
        wt = await asyncio.to_thread(
            pool.acquire, lambda status: task.set_status(status)
        )
        task.set_status("running")
        try:
            call_ctx = Context(
                value=f"{prompt}\n\n{ctx.value}",
                worktree=wt,
                session_id=ctx.session_id,
                forked=ctx.forked,
            )
            result, session_id = await claude_call(call_ctx, on_event=task.add_event)
            if not await asyncio.to_thread(has_changes, wt):
                await asyncio.to_thread(pool.release, wt)
                wt = None
            task.set_status("done")
            return Context(value=result, worktree=wt, session_id=session_id)
        except Exception as e:
            task.set_status("error")
            task.add_event("text", str(e))
            if wt:
                await asyncio.to_thread(pool.release, wt)
            return None

    with Live(display, console=console, refresh_per_second=4):
        results = await asyncio.gather(
            *[call(ctx, i) for i, ctx in enumerate(contexts)]
        )
    return [ctx for ctx in results if ctx is not None]
