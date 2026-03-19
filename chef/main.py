import argparse
import asyncio
import atexit
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

from .operators.checkpoint import load_checkpoint
from .parser import parse
from .runtime import run

console = Console()
err_console = Console(stderr=True)


def main():
    ap = argparse.ArgumentParser(prog="chef")
    ap.add_argument("recipe")
    ap.add_argument("--from", dest="from_checkpoint", metavar="UUID")
    args = ap.parse_args()

    initial_contexts = []
    if args.from_checkpoint:
        initial_contexts = load_checkpoint(args.from_checkpoint)

    if sys.stderr.isatty():
        atexit.register(sys.stderr.flush)
        atexit.register(sys.stderr.write, "\033[!p\033[?25h\033[0m")

    pipeline = parse(args.recipe)
    try:
        results = asyncio.run(run(pipeline, initial_contexts))
    except AssertionError as e:
        err_console.print(f"[red]error:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
    for i, ctx in enumerate(results):
        label = f"[bold]{i + 1}/{len(results)}[/bold]" if len(results) > 1 else ""
        console.print(Rule(label, style="bright_black"))
        console.print(Markdown(ctx.value))
