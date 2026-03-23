import json
from dataclasses import asdict
from pathlib import Path

from rich.console import Console

from ..context import Context

CHECKPOINTS_DIR = Path.home() / ".cache" / "chef" / "checkpoints"

console = Console(stderr=True)


def save_checkpoint(path: Path, contexts: list[Context]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(ctx) for ctx in contexts], indent=2))


def load_checkpoint(uid: str) -> list[Context]:
    path = CHECKPOINTS_DIR / f"{uid}.json"
    if not path.exists():
        raise SystemExit(f"checkpoint not found: {uid} ({path})")
    contexts = [Context(**item) for item in json.loads(path.read_text())]
    console.print(f"[dim]loaded {len(contexts)} context(s) from checkpoint {uid}[/dim]")
    return contexts
