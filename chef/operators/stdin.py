import sys

from rich.console import Console

from ..context import Context

console = Console(stderr=True)


def stdin_op(contexts: list[Context]) -> list[Context]:
    assert not contexts, "stdin is a source operator and must be first in the pipeline"
    assert not sys.stdin.isatty(), "stdin operator requires piped input"
    lines = [line.rstrip("\n") for line in sys.stdin if line.strip()]
    assert lines, "stdin is empty"
    console.print(f"[dim]read {len(lines)} line(s) from stdin[/dim]")
    return [Context(value=line) for line in lines]
