import subprocess
import sys
from pathlib import Path

from rich.console import Console

from ..context import Context

console = Console(stderr=True)


def apply_op(contexts: list[Context]) -> list[Context]:
    assert contexts, "no input contexts"

    diffs = [ctx.diff for ctx in contexts if ctx.diff]
    assert diffs, "no diffs to apply"

    repo_root = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True
    )
    if status.stdout.strip():
        console.print("[yellow]warning: working tree has uncommitted changes[/yellow]")

    console.print(f"[dim]applying {len(diffs)} diff(s)[/dim]")
    result = subprocess.run(
        ["git", "apply", "--3way"],
        input="\n".join(diffs),
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git apply failed")

    stat = subprocess.run(
        ["git", "diff", "--stat"], cwd=repo_root, capture_output=True, text=True
    )
    if stat.stdout.strip():
        console.print(stat.stdout.rstrip())

    if sys.stderr.isatty():
        diff_tool = subprocess.run(
            ["git", "config", "diff.tool"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if diff_tool:
            console.print(f"[dim]opening {diff_tool}...[/dim]")
            subprocess.run(["git", "difftool", "-d", "-y"], cwd=repo_root)

    return contexts
