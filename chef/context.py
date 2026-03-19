from dataclasses import dataclass


@dataclass
class Context:
    value: str
    worktree: str | None = None
    session_id: str | None = None
    forked: bool = False
