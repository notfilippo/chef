from dataclasses import dataclass

from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

_TAIL = 5


@dataclass
class _Line:
    type: str
    content: str


class Task:
    def __init__(self, label: str) -> None:
        self.label = label
        self.status = "running"
        self.lines: list[_Line] = []
        self._spinner = Spinner("dots")

    def add_event(self, event_type: str, content: str) -> None:
        for line in content.splitlines():
            if line.strip():
                self.lines.append(_Line(type=event_type, content=line))

    def set_status(self, status: str) -> None:
        self.status = status

    def _render_rows(self, grid: Table) -> None:
        if self.status in ("running", "copying", "resetting"):
            icon = self._spinner
            label = Text.from_markup(f"[bold]{self.label}[/bold] {self.status}...")
        elif self.status == "done":
            icon = Text("✓", style="green")
            label = Text.from_markup(f"[bold]{self.label}[/bold] [green]done[/green]")
        else:
            icon = Text("✗", style="red")
            label = Text.from_markup(f"[bold]{self.label}[/bold] [red]error[/red]")
        grid.add_row(icon, label)
        for line in self.lines[-_TAIL:]:
            if line.type == "tool_use":
                grid.add_row("", Text.from_markup(f"[cyan]→ {line.content}[/cyan]"))
            else:
                grid.add_row("", Text(line.content, style="dim"))


class TaskDisplay:
    def __init__(self, labels: list[str]) -> None:
        self.tasks = [Task(label) for label in labels]

    def __rich__(self) -> Table:
        grid = Table.grid(padding=(0, 1))
        grid.add_column()
        grid.add_column()
        for task in self.tasks:
            task._render_rows(grid)
        return grid
