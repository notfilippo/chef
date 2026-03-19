import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

from ..context import Context

console = Console(stderr=True)
session = PromptSession()


async def confirm_op(contexts: list[Context]) -> list[Context]:
    assert contexts, "no input contexts"
    assert sys.stdin.isatty(), "confirm requires an interactive terminal"

    kept = []
    total = len(contexts)
    try:
        for i, ctx in enumerate(contexts, 1):
            console.print()
            console.print(Rule(f"[bold]{i}/{total}[/bold]", style="bright_black"))
            console.print()
            console.print(Markdown(ctx.value))
            console.print()
            console.print(Rule(style="bright_black"))

            while True:
                answer = (
                    (
                        await session.prompt_async(
                            HTML(
                                "<bold><ansiyellow>Address this?</ansiyellow></bold> [Y/n]: "
                            )
                        )
                    )
                    .strip()
                    .lower()
                )
                if answer in ("y", "n", ""):
                    break
                console.print("[red]Please answer y or n.[/red]")

            if answer in ("y", ""):
                note = (
                    await session.prompt_async(
                        HTML("Add context (or press enter to skip): ")
                    )
                ).strip()
                value = f"{ctx.value}\n\nNote: {note}" if note else ctx.value
                kept.append(
                    Context(
                        value=value, worktree=ctx.worktree, session_id=ctx.session_id
                    )
                )
    except KeyboardInterrupt:
        console.print()
        raise

    return kept
