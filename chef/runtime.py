import asyncio
import uuid

from rich.console import Console
from rich.rule import Rule
from rich.table import Table

from .context import Context
from .parser import PipelineNode
from .operators import (
    apply_op,
    commit_op,
    confirm_op,
    fork_op,
    map_op,
    reduce_op,
    review_comments_op,
    stdin_op,
    text_op,
)
from .operators.checkpoint import CHECKPOINTS_DIR, save_checkpoint

console = Console(stderr=True)


async def run(
    pipeline: PipelineNode, initial_contexts: list[Context] = []
) -> list[Context]:
    contexts: list[Context] = list(initial_contexts)
    checkpoints: list[tuple[str, str]] = []

    try:
        for i, stage in enumerate(pipeline.stages):
            if i > 0:
                console.print(Rule(f"[bold]{stage.label}[/bold]", style="bright_black"))
            try:
                new_contexts: list[Context] | None = None
                match stage.name:
                    case "apply":
                        new_contexts = await asyncio.to_thread(apply_op, contexts)
                    case "stdin":
                        new_contexts = stdin_op(contexts)
                    case "text":
                        new_contexts = text_op(contexts, stage.arg)
                    case "review_comments":
                        new_contexts = await asyncio.to_thread(
                            review_comments_op, contexts, stage.arg
                        )
                    case "map":
                        new_contexts = await map_op(contexts, stage.arg)
                    case "confirm":
                        new_contexts = await confirm_op(contexts)
                    case "fork":
                        new_contexts = fork_op(contexts, stage.arg)
                    case "reduce":
                        new_contexts = await reduce_op(contexts, stage.arg)
                    case "commit":
                        new_contexts = await commit_op(contexts, stage.arg)
                    case _:
                        raise AssertionError(f"unknown operator: {stage.name!r}")

                if new_contexts is not None:
                    contexts = new_contexts
                    uid = uuid.uuid4().hex[:8]
                    await asyncio.to_thread(
                        save_checkpoint, CHECKPOINTS_DIR / f"{uid}.json", contexts
                    )
                    checkpoints.append((stage.label, uid))

            except AssertionError as e:
                raise AssertionError(f"[{stage.name}] {e}") from e
    finally:
        if checkpoints:
            console.print()
            console.print(Rule("checkpoints", style="bright_black"))
            table = Table.grid(padding=(0, 2))
            for label, uid in checkpoints:
                table.add_row(f"[bold cyan]{uid}[/bold cyan]", f"[dim]{label}[/dim]")
            console.print(table)
            console.print()

    return contexts
