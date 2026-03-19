from rich.console import Console

from ..context import Context

console = Console(stderr=True)


def text_op(contexts: list[Context], arg: str | list[str]) -> list[Context]:
    assert not contexts, "text is a source operator and must be first in the pipeline"
    assert arg, "missing text argument"
    values = [arg] if isinstance(arg, str) else arg
    console.print(f"[dim]loaded {len(values)} text context(s)[/dim]")
    return [Context(value=v) for v in values]
