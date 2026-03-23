import os
import subprocess
import sys
import tempfile
import termios
import tty
from dataclasses import replace
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text

from ..context import Context
from .worktree import get_diff, get_repo_root, git_apply

console = Console(stderr=True)


def _getch() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _open_editor(path: Path) -> None:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR", "vi")
    subprocess.run([editor, str(path)])


def _edit_diff_with_difftool(diff: str) -> str | None:
    repo_root = get_repo_root()
    git_apply(repo_root, diff)
    try:
        subprocess.run(["git", "difftool", "-d", "-y"], cwd=repo_root)
        return get_diff(repo_root) or None
    finally:
        subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=repo_root, capture_output=True)


async def review_op(contexts: list[Context]) -> list[Context]:
    assert contexts, "no input contexts"
    assert sys.stdin.isatty(), "review requires an interactive terminal"

    kept = []
    total = len(contexts)
    try:
        for i, ctx in enumerate(contexts, 1):
            console.print()
            console.print(Rule(f"[bold]{i}/{total}[/bold]", style="bright_black"))
            console.print()
            console.print(Markdown(ctx.value))
            if ctx.diff:
                console.print(Syntax(ctx.diff, "diff", theme="ansi_dark"))
            console.print()
            console.print(Rule(style="bright_black"))

            with tempfile.TemporaryDirectory() as tmp:
                value_path = Path(tmp) / "value.md"
                value_path.write_text(ctx.value)

                while True:
                    hint = Text()
                    hint.append(" e ", style="bold reverse")
                    hint.append(" edit  ")
                    if ctx.diff:
                        hint.append(" d ", style="bold reverse")
                        hint.append(" diff  ")
                    hint.append(" y ", style="bold reverse")
                    hint.append(" keep  ")
                    hint.append(" n ", style="bold reverse")
                    hint.append(" skip")
                    console.print(hint)

                    key = _getch()
                    console.print()

                    if key == "e":
                        _open_editor(value_path)
                        ctx = replace(ctx, value=value_path.read_text())
                        console.print(Markdown(ctx.value))
                    elif key == "d" and ctx.diff:
                        ctx = replace(ctx, diff=_edit_diff_with_difftool(ctx.diff))
                        if ctx.diff:
                            console.print(Syntax(ctx.diff, "diff", theme="ansi_dark"))
                    elif key == "y" or key == "\r" or key == "\n":
                        kept.append(ctx)
                        break
                    elif key == "n":
                        break
    except KeyboardInterrupt:
        console.print()
        raise

    return kept
