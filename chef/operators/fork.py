from rich.console import Console

from ..context import Context
from .registry import operator

console = Console(stderr=True)


@operator
async def fork(contexts: list[Context], arg: int | list[str]) -> list[Context]:
    """Duplicate contexts into variants."""
    assert contexts, "no input contexts"
    assert arg, "missing fork argument"

    result = []
    if isinstance(arg, int):
        assert arg > 0, "argument must be a positive integer"
        console.print(
            f"[dim]forking {len(contexts)} context(s) × {arg} = {len(contexts) * arg}[/dim]"
        )
        for ctx in contexts:
            for _ in range(arg):
                result.append(
                    Context(value=ctx.value, session_id=ctx.session_id, forked=True)
                )
    else:
        console.print(
            f"[dim]forking {len(contexts)} context(s) into {len(arg)} variant(s) = {len(contexts) * len(arg)}[/dim]"
        )
        for ctx in contexts:
            for variant in arg:
                result.append(
                    Context(
                        value=f"{ctx.value}\n\n{variant}",
                        session_id=ctx.session_id,
                        forked=True,
                    )
                )
    return result
