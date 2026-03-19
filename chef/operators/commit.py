import subprocess

from rich.console import Console

from ..context import Context
from .worktree import has_changes, pool

console = Console(stderr=True)


def commit_op(contexts: list[Context], message: str) -> list[Context]:
    assert contexts, "no input contexts"
    assert message, "missing commit message argument"

    results = []
    for ctx in contexts:
        if not ctx.worktree or not has_changes(ctx.worktree):
            results.append(ctx)
            continue

        subprocess.run(
            ["git", "add", "-A"], cwd=ctx.worktree, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=ctx.worktree,
            check=True,
            capture_output=True,
        )
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ctx.worktree, text=True
        ).strip()
        console.print(f"[green]committed[/green] {sha}")
        pool.release(ctx.worktree)
        results.append(Context(value=sha, session_id=ctx.session_id))

    return results
