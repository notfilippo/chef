import re
from dataclasses import dataclass


OperatorArg = str | int | list[str] | None


@dataclass
class OperatorNode:
    name: str
    arg: OperatorArg

    @property
    def label(self) -> str:
        if self.arg is None:
            return self.name
        if isinstance(self.arg, list):
            args = " ".join(f'"{a}"' for a in self.arg)
        elif isinstance(self.arg, str):
            args = f'"{self.arg}"'
        else:
            args = str(self.arg)
        return f"{self.name} {args}"


@dataclass
class PipelineNode:
    stages: list[OperatorNode]


TOKEN_RE = re.compile(
    r'(?P<STRING>"[^"]*")'
    r"|(?P<NUMBER>\d+)"
    r"|(?P<IDENT>[a-zA-Z_]\w*)"
)


def _tokenize(expr: str) -> list[tuple[str, str]]:
    return [(m.lastgroup, m.group()) for m in TOKEN_RE.finditer(expr)]


def _parse_operator(seg: str) -> OperatorNode:
    tokens = _tokenize(seg)
    assert tokens and tokens[0][0] == "IDENT", f"expected an operator, got: {seg!r}"
    _, name = tokens[0]
    arg = None
    rest = tokens[1:]
    if rest:
        if all(k == "STRING" for k, _ in rest):
            strings = [v[1:-1] for _, v in rest]
            arg = strings[0] if len(strings) == 1 else strings
        elif len(rest) == 1 and rest[0][0] == "NUMBER":
            arg = int(rest[0][1])
        else:
            raise AssertionError(f"invalid arguments for operator {name!r}: {seg!r}")
    return OperatorNode(name=name, arg=arg)


def parse(expr: str) -> PipelineNode:
    segments = [s.strip() for s in expr.split("|")]
    stages = [_parse_operator(seg) for seg in segments if seg]
    return PipelineNode(stages=stages)
