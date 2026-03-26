import argparse

import shtab

from .operators import all_operators


def _build_shtab_parser() -> argparse.ArgumentParser:
    ops = all_operators()
    ap = argparse.ArgumentParser(prog="ch")
    op_arg = ap.add_argument("operator", metavar="operator")
    op_arg.complete = shtab.Choice([(op.name, op.description) for op in ops])  # type: ignore[attr-defined]
    ap.add_argument("args", nargs="*", metavar="arg")
    return ap


def _fish_script() -> str:
    ops = all_operators()
    operator_completions = "\n".join(
        f"complete -c ch -f -n 'test (count (commandline -opc)) -eq 1'"
        f" -a {op.name!r} -d {op.description!r}"
        for op in ops
    )
    return f"""\
{operator_completions}
"""


def print_completions(shell: str) -> None:
    supported = {"bash", "zsh", "fish"}
    if shell not in supported:
        raise SystemExit(
            f"unsupported shell: {shell!r} (supported: {', '.join(sorted(supported))})"
        )
    if shell == "fish":
        print(_fish_script(), end="")
        return
    ap = _build_shtab_parser()
    print(shtab.complete(ap, shell=shell), end="")
