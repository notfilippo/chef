import sys

from rich.console import Console

from ..context import Context

console = Console(stderr=True)


def stdin_op(contexts: list[Context], sep: str | None = None) -> list[Context]:
    assert not contexts, "stdin is a source operator and must be first in the pipeline"
    assert not sys.stdin.isatty(), "stdin operator requires piped input"
    raw = sys.stdin.read()
    if sep is None:
        items = [line.rstrip("\n") for line in raw.splitlines() if line.strip()]
    else:
        sep = sep.encode("raw_unicode_escape").decode("unicode_escape")
        items = [item.strip() for item in raw.split(sep) if item.strip()]
    assert items, "stdin is empty"
    console.print(f"[dim]read {len(items)} item(s) from stdin[/dim]")
    return [Context(value=item) for item in items]
