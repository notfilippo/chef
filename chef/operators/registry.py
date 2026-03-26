from dataclasses import dataclass
from typing import Callable

@dataclass
class OperatorMeta:
    name: str
    description: str
    fn: Callable

_registry: dict[str, OperatorMeta] = {}


def operator(fn: Callable = None, *, name: str = None) -> Callable:
    def decorator(fn: Callable) -> Callable:
        op_name = name or fn.__name__
        description = (fn.__doc__ or "").strip().splitlines()[0]
        _registry[op_name] = OperatorMeta(name=op_name, description=description, fn=fn)
        return fn

    if fn is not None:
        return decorator(fn)
    return decorator


def all_operators() -> list[OperatorMeta]:
    return list(_registry.values())


def get_operator(name: str) -> OperatorMeta | None:
    return _registry.get(name)
