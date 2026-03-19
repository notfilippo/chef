import json
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path

from ..context import Context


def git_repo_root() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()


def has_changes(worktree: str) -> bool:
    result = subprocess.run(
        ["git", "diff", "HEAD", "--quiet"],
        cwd=worktree,
        capture_output=True,
    )
    return result.returncode != 0


def get_diff(worktree: str) -> str:
    result = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=worktree,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class Pool:
    def __init__(
        self, pool_dir: Path = Path.home() / ".cache" / "chef" / "worktrees"
    ) -> None:
        self._dir = pool_dir

    def _create(self, repo_root: str, path: str) -> None:
        subprocess.run(
            ["git", "-C", repo_root, "worktree", "add", "--detach", path],
            check=True,
            capture_output=True,
        )

    def _reset(self, repo_root: str, path: str, head: str) -> None:
        subprocess.run(["git", "reset", "--hard", head], cwd=path, capture_output=True)
        subprocess.run(["git", "clean", "-fd"], cwd=path, capture_output=True)

    def acquire(self, on_status: Callable[[str], None] | None = None) -> str:
        repo_root = git_repo_root()
        self._dir.mkdir(parents=True, exist_ok=True)
        head = subprocess.check_output(
            ["git", "-C", repo_root, "rev-parse", "HEAD"], text=True
        ).strip()

        for meta_file in self._dir.glob("*.meta"):
            entry_id = meta_file.stem
            lock_file = self._dir / f"{entry_id}.lock"
            worktree = self._dir / entry_id

            try:
                meta = json.loads(meta_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if meta.get("repo_root") != repo_root:
                continue
            if not worktree.exists():
                continue
            try:
                lock_file.open("x").close()
            except FileExistsError:
                continue

            if on_status:
                on_status("resetting")
            self._reset(repo_root, str(worktree), head)
            return str(worktree)

        repo_name = Path(repo_root).name
        entry_id = f"{repo_name}-{head[:8]}-{uuid.uuid4().hex[:8]}"
        worktree = self._dir / entry_id
        if on_status:
            on_status("copying")
        self._create(repo_root, str(worktree))
        (self._dir / f"{entry_id}.meta").write_text(
            json.dumps({"repo_root": repo_root})
        )
        (self._dir / f"{entry_id}.lock").touch()
        return str(worktree)

    def release(self, path: str) -> None:
        p = Path(path)
        if not p.is_relative_to(self._dir):
            return
        (self._dir / f"{p.name}.lock").unlink(missing_ok=True)


pool = Pool()


def remove_worktrees(contexts: list[Context]) -> None:
    for ctx in contexts:
        if ctx.worktree:
            pool.release(ctx.worktree)
