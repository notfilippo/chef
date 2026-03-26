import sys

from rich.console import Console

from ..context import Context
from .registry import operator

console = Console(stderr=True)


@operator
async def stdin(contexts: list[Context], arg: str | None = None) -> list[Context]:
    """Read contexts from stdin."""
    assert not contexts, "stdin is a source operator and must be first in the pipeline"
    assert not sys.stdin.isatty(), "stdin operator requires piped input"
    raw = sys.stdin.read()
    if arg is None:
        items = [line.rstrip("\n") for line in raw.splitlines() if line.strip()]
    else:
        sep = arg.encode("raw_unicode_escape").decode("unicode_escape")
        items = [item.strip() for item in raw.split(sep) if item.strip()]
    assert items, "stdin is empty"
    console.print(f"[dim]read {len(items)} item(s) from stdin[/dim]")
    return [Context(value=item) for item in items]
