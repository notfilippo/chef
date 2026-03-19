import asyncio

from rich.console import Console
from rich.live import Live

from ..claude import claude_call
from ..context import Context
from .display import TaskDisplay
from .worktree import get_diff, has_changes, pool


async def reduce_op(contexts: list[Context], prompt: str) -> list[Context]:
    assert contexts, "no input contexts"
    assert prompt, "missing prompt argument"

    console = Console(stderr=True)
    console.print(f"[dim]reducing {len(contexts)} context(s)[/dim]")
    has_worktrees = any(ctx.worktree for ctx in contexts)

    if has_worktrees:
        parts = []
        for i, ctx in enumerate(contexts, 1):
            diff = get_diff(ctx.worktree) if ctx.worktree else ""
            part = f"--- Variant {i} ---\n{ctx.value}"
            if diff:
                part += f"\n\nChanges:\n```diff\n{diff}\n```"
            parts.append(part)
        combined = "\n\n".join(parts)
    else:
        combined = "\n\n".join(ctx.value for ctx in contexts)

    display = TaskDisplay(["reduce"])
    task = display.tasks[0]

    wt = await asyncio.to_thread(pool.acquire, lambda status: task.set_status(status))
    task.set_status("running")

    try:
        merged_ctx = Context(value=f"{prompt}\n\n{combined}", worktree=wt)
        with Live(display, console=console, refresh_per_second=4):
            result, session_id = await claude_call(merged_ctx, on_event=task.add_event)
            task.set_status("done")

        if not await asyncio.to_thread(has_changes, wt):
            await asyncio.to_thread(pool.release, wt)
            wt = None
    except Exception as e:
        task.set_status("error")
        task.add_event("text", str(e))
        await asyncio.to_thread(pool.release, wt)
        raise

    return [Context(value=result, session_id=session_id, worktree=wt)]
