from rich.console import Console
from rich.live import Live

from ..claude import claude_call
from ..context import Context
from .display import TaskDisplay
from .worktree import get_diff, git_repo_root


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
    repo_root = git_repo_root()
    merged_ctx = Context(value=f"{prompt}\n\n{combined}", worktree=repo_root)

    with Live(display, console=console, refresh_per_second=4):
        result, session_id = await claude_call(merged_ctx, on_event=task.add_event)
        task.set_status("done")

    return [Context(value=result, session_id=session_id, worktree=repo_root)]
