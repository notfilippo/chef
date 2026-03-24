import asyncio
import json
import subprocess
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

POOL_DIR = Path.home() / ".cache" / "chef" / "worktrees"

_bazel_output_base_cache: dict[str, str] = {}

_SYMLINK_DIRS = ["node_modules", ".venv", "venv", "target"]


def _get_bazel_output_base(repo_root: Path) -> str | None:
    key = str(repo_root)
    if key not in _bazel_output_base_cache:
        result = subprocess.run(
            ["bazel", "info", "output_base"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            _bazel_output_base_cache[key] = result.stdout.strip()
        else:
            return None
    return _bazel_output_base_cache.get(key)


def _setup_caches(wt: Path, repo_root: Path) -> None:
    # Bazel: share output base so worktrees reuse already-built artifacts
    output_base = _get_bazel_output_base(repo_root)
    if output_base:
        (wt / "user.bazelrc").write_text(f"startup --output_base={output_base}\n")

    # Symlink dependency/build dirs from the main repo, but only if they are
    # gitignored in the worktree (to avoid polluting git status).
    for name in _SYMLINK_DIRS:
        src = repo_root / name
        dst = wt / name
        if not src.exists() or dst.exists() or dst.is_symlink():
            continue
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", name],
            cwd=wt,
            capture_output=True,
        )
        if ignored.returncode == 0:
            dst.symlink_to(src)


def get_repo_root() -> Path:
    return Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )


def get_diff(path: Path) -> str:
    return subprocess.check_output(["git", "diff", "HEAD"], cwd=path, text=True).strip()


def git_apply(path: Path, diff: str, three_way: bool = False) -> None:
    if not diff.endswith("\n"):
        diff += "\n"
    cmd = ["git", "apply"]
    if three_way:
        cmd.append("--3way")
    result = subprocess.run(cmd, input=diff, cwd=path, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or f"git apply failed (exit {result.returncode})"
        )


def _write_bazelrc(wt: Path, repo_root: Path) -> None:
    output_base = _get_bazel_output_base(repo_root)
    if output_base:
        (wt / "user.bazelrc").write_text(f"startup --output_base={output_base}\n")


def acquire(on_status: Callable[[str], None] | None = None) -> Path:
    POOL_DIR.mkdir(parents=True, exist_ok=True)

    repo_root = get_repo_root()

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

        _setup_caches(wt, repo_root)
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

    _setup_caches(wt, repo_root)
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
