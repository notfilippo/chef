import argparse
import asyncio
import atexit
import json
import sys
import uuid
from dataclasses import asdict

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

from .context import Context

console = Console()
err_console = Console(stderr=True)


def _read_input(operator_name: str) -> list[Context]:
    if sys.stdin.isatty() or operator_name == "stdin":
        return []
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [Context(**item) for item in data]
    except Exception:
        pass
    lines = [line.rstrip("\n") for line in raw.splitlines() if line.strip()]
    return [Context(value=line) for line in lines]


def _parse_op_arg(args: list[str]):
    if not args:
        return None
    if len(args) == 1:
        try:
            return int(args[0])
        except ValueError:
            return args[0]
    return args


def _write_output(contexts: list[Context]) -> None:
    if sys.stdout.isatty():
        for i, ctx in enumerate(contexts):
            if len(contexts) > 1:
                err_console.print(
                    Text.from_markup(f"[bright_black]·[/bright_black] [bold]{i + 1}/{len(contexts)}[/bold]")
                )
            console.print(Markdown(ctx.value))
    else:
        print(json.dumps([asdict(ctx) for ctx in contexts]))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "completions":
        from .completions import print_completions

        if len(sys.argv) < 3:
            print("usage: ch completions <bash|zsh|fish>", file=sys.stderr)
            sys.exit(1)
        print_completions(sys.argv[2])
        return

    from . import operators as _ops  # noqa: F401 — registers all operators
    from .operators.checkpoint import CHECKPOINTS_DIR, save_checkpoint
    from .operators.registry import all_operators, get_operator

    ops = all_operators()

    ap = argparse.ArgumentParser(
        prog="ch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "shell completions:\n"
            "  ch completions <bash|zsh|fish>\n"
            "\n"
            "  bash   source <(ch completions bash)           # add to ~/.bashrc\n"
            "  zsh    source <(ch completions zsh)            # add to ~/.zshrc\n"
            "  fish   ch completions fish | source            # or save to ~/.config/fish/completions/ch.fish"
        ),
    )
    ap.add_argument("operator", choices=[op.name for op in ops], metavar="operator")
    ap.add_argument("args", nargs="*", metavar="arg")
    parsed = ap.parse_args()

    if sys.stderr.isatty():
        atexit.register(sys.stderr.flush)
        atexit.register(sys.stderr.write, "\033[!p\033[?25h\033[0m")

    contexts = _read_input(parsed.operator)
    op_arg = _parse_op_arg(parsed.args)
    meta = get_operator(parsed.operator)

    try:
        result = asyncio.run(meta.fn(contexts, op_arg))
    except AssertionError as e:
        err_console.print(f"[red]error:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)

    if result is None:
        return

    uid = uuid.uuid4().hex[:8]
    checkpoint_path = CHECKPOINTS_DIR / f"{uid}.json"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(json.dumps([asdict(ctx) for ctx in result], indent=2))
    err_console.print(f"[dim]checkpoint [cyan]{uid}[/cyan][/dim]")

    _write_output(result)
