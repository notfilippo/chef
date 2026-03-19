from dataclasses import dataclass


@dataclass
class Context:
    value: str
    diff: str | None = None
    session_id: str | None = None
    forked: bool = False
