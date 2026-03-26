from ..context import Context
from .checkpoint import load_checkpoint
from .registry import operator


@operator
async def checkpoint(contexts: list[Context], arg: str) -> list[Context]:
    """Load contexts from a checkpoint by UUID."""
    assert not contexts, "checkpoint is a source operator and must be first in the pipeline"
    assert arg, "missing checkpoint UUID"
    return load_checkpoint(arg)
