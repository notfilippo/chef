import os
import subprocess
import tempfile
import termios
import tty
from dataclasses import replace
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text

from ..context import Context
from .registry import operator
from .worktree import get_diff, get_repo_root, git_apply

console = Console(stderr=True)


def _getch() -> str:
    with open("/dev/tty") as tty_fd:
        fd = tty_fd.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = tty_fd.read(1)
            if ch == "\x03":
                raise KeyboardInterrupt
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _open_editor(path: Path) -> None:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR", "vi")
    tty_fd = os.open("/dev/tty", os.O_RDWR)
    try:
        subprocess.run([editor, str(path)], stdin=tty_fd, stdout=tty_fd, stderr=tty_fd)
    finally:
        os.close(tty_fd)


def _edit_diff_with_difftool(diff: str) -> str | None:
    repo_root = get_repo_root()
    git_apply(repo_root, diff)
    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR)
        try:
            subprocess.run(
                ["git", "difftool", "-d", "-y"],
                cwd=repo_root,
                stdin=tty_fd,
                stdout=tty_fd,
                stderr=tty_fd,
            )
        finally:
            os.close(tty_fd)
        return get_diff(repo_root) or None
    finally:
        subprocess.run(
            ["git", "reset", "--hard", "HEAD"], cwd=repo_root, capture_output=True
        )


@operator
async def review(contexts: list[Context], arg: None = None) -> list[Context]:
    """Interactively review and edit contexts."""
    assert contexts, "no input contexts"
    assert os.path.exists("/dev/tty"), "review requires an interactive terminal"

    kept = []
    total = len(contexts)
    try:
        for i, ctx in enumerate(contexts, 1):
            console.rule(f"[bold]{i}/{total}[/bold]")
            console.print()
            console.print(Markdown(ctx.value.strip()))
            if ctx.diff:
                console.print(Syntax(ctx.diff, "diff", theme="ansi_dark"))

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
                    hint.append(" k ", style="bold reverse")
                    hint.append(" keep  ")
                    hint.append(" s ", style="bold reverse")
                    hint.append(" skip")
                    console.print()
                    console.rule(style="dim")
                    console.print(hint)

                    key = _getch()
                    console.print()

                    if key == "e":
                        _open_editor(value_path)
                        ctx = replace(ctx, value=value_path.read_text())
                        console.print(Markdown(ctx.value.strip()))
                    elif key == "d" and ctx.diff:
                        ctx = replace(ctx, diff=_edit_diff_with_difftool(ctx.diff))
                        if ctx.diff:
                            console.print(Syntax(ctx.diff, "diff", theme="ansi_dark"))
                    elif key == "k" or key == "\r" or key == "\n":
                        kept.append(ctx)
                        break
                    elif key == "s":
                        break
    except KeyboardInterrupt:
        console.print()
        raise

    return kept
