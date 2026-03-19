import json
from pathlib import Path

from rich.console import Console

from ..context import Context
from .worktree import get_diff

CHECKPOINTS_DIR = Path.home() / ".cache" / "chef" / "checkpoints"

console = Console(stderr=True)


def save_checkpoint(path: Path, contexts: list[Context]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = []
    for ctx in contexts:
        entry: dict = {"value": ctx.value, "session_id": ctx.session_id}
        if ctx.worktree:
            if diff := get_diff(ctx.worktree):
                entry["diff"] = diff
        data.append(entry)
    path.write_text(json.dumps(data, indent=2))


def load_checkpoint(uid: str) -> list[Context]:
    path = CHECKPOINTS_DIR / f"{uid}.json"
    data = json.loads(path.read_text())
    contexts = []
    for item in data:
        value = item["value"]
        if diff := item.get("diff"):
            value += f"\n\nChanges:\n```diff\n{diff}\n```"
        contexts.append(Context(value=value, session_id=item.get("session_id")))
    console.print(f"[dim]loaded {len(contexts)} context(s) from checkpoint {uid}[/dim]")
    return contexts
