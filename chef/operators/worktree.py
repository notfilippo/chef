import asyncio
import json
import subprocess
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

POOL_DIR = Path.home() / ".cache" / "chef" / "worktrees"


def get_diff(worktree: Path) -> str:
    result = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=worktree,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def acquire(on_status: Callable[[str], None] | None = None) -> Path:
    POOL_DIR.mkdir(parents=True, exist_ok=True)

    repo_root = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )

    head = subprocess.check_output(
        ["git", "-C", repo_root, "rev-parse", "HEAD"],
        text=True,
    ).strip()

    for meta_file in POOL_DIR.glob("*.meta"):
        entry_id = meta_file.stem
        lock_file = POOL_DIR / f"{entry_id}.lock"
        wt = POOL_DIR / entry_id

        try:
            meta = json.loads(meta_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if meta.get("repo_root") != str(repo_root):
            continue
        if not wt.exists():
            continue
        try:
            lock_file.open("x").close()
        except FileExistsError:
            continue

        if on_status:
            on_status("resetting")

        subprocess.run(
            ["git", "reset", "--hard", head],
            cwd=wt,
            capture_output=True,
        )
        subprocess.run(
            ["git", "clean", "-fd"],
            cwd=wt,
            capture_output=True,
        )

        return wt

    repo_name = Path(repo_root).name
    entry_id = f"{repo_name}-{uuid.uuid4().hex[:8]}"
    wt = POOL_DIR / entry_id

    if on_status:
        on_status("copying")

    subprocess.run(
        ["git", "-C", repo_root, "worktree", "add", "--detach", wt],
        check=True,
        capture_output=True,
    )

    (POOL_DIR / f"{entry_id}.meta").write_text(
        json.dumps({"repo_root": str(repo_root)})
    )
    (POOL_DIR / f"{entry_id}.lock").touch()

    return wt


def release(path: Path) -> None:
    if not path.is_relative_to(POOL_DIR):
        return
    (POOL_DIR / f"{path.name}.lock").unlink(missing_ok=True)


@asynccontextmanager
async def worktree(on_status: Callable[[str], None] | None = None):
    wt = await asyncio.to_thread(acquire, on_status)
    try:
        yield wt
    finally:
        await asyncio.to_thread(release, wt)
