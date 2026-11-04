"""Textual TUI application for tcal."""
from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional

_CONFIG_PATH = Path.home() / ".config" / "tcal" / "config.json"


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text())
    except Exception:
        return {}


def _save_config(data: dict) -> None:
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(json.dumps(data, indent=2))
    except Exception:
        pass

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Button, Footer, Input, Label, ListItem, ListView, Static

from . import client
from .display import (
    build_gantt_header,
    build_task_text,
    sort_tasks,
    split_note_annotation,
    week_start,
)
from .models import Task

# ── Due-date shortcut map ──────────────────────────────────────────────────────

DUE_SHORTCUTS: dict[str, str] = {
    "0": "mod due:today",
    "1": "mod due:1d",
    "2": "mod due:2d",
    "3": "mod due:3d",
    "4": "mod due:4d",
    "5": "mod due:5d",
    "6": "mod due:6d",
    "7": "mod due:7d",
    "8": "mod due:1w",
    "9": "mod due:2w",
}

HELP_TEXT = """\
Navigation
──────────────────────────────────────────
  j / ↓        Move down
  k / ↑        Move up
  g            Go to top
  G            Go to bottom

Task actions
──────────────────────────────────────────
  Space        Toggle selection (acts on all selected)
  d            Mark done
  e            Delete (with confirmation)
  i            Show task info
  Enter / m    Modify (opens command input)

Due-date shortcuts (pre-fill modify)
──────────────────────────────────────────
  0            due:today
  1 – 7        due:Nd  (N days from now)
  8            due:1w
  9            due:2w

View
──────────────────────────────────────────
  p            Toggle sort-by-project
  l            Toggle GANTT ↔ list mode
  r            Reload from Taskwarrior
  /            Direct task command (without typing "task")

  q / ESC      Quit
  ?            This help
"""

# ── Widgets ───────────────────────────────────────────────────────────────────


class TaskListItem(ListItem):
    """A list item that carries an optional Task reference."""

    def __init__(self, tw_task: Optional[Task], display_text: Text) -> None:
        super().__init__()
        self.tw_task = tw_task  # renamed: 'task' conflicts with a Textual ListItem property
        self._text = display_text

    def compose(self) -> ComposeResult:
        yield Label(self._text)


class GanttHeader(Static):
    """Fixed header widget showing dates and day columns."""


# ── Modal screens ─────────────────────────────────────────────────────────────


class InfoModal(ModalScreen[None]):
    """Read-only text display (task info, command output, help)."""

    BINDINGS = [("escape", "dismiss", "Close"), ("q", "dismiss", "Close"),
                ("enter", "dismiss", "Close")]

    def __init__(self, content: str, title: str = "") -> None:
        super().__init__()
        self._content = content
        self._title = title

    def compose(self) -> ComposeResult:
        with Static(id="info-dialog"):
            if self._title:
                yield Label(f"[bold]{self._title}[/bold]", id="info-title")
            yield Static(self._content, id="info-body")
            yield Button("OK  [ESC]", variant="primary", id="ok")

    def on_button_pressed(self, _: Button.Pressed) -> None:
        self.dismiss()


class ModifyModal(ModalScreen[Optional[str]]):
    """Editable command input that returns the final command string."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, initial_cmd: str) -> None:
        super().__init__()
        self._initial = initial_cmd

    def compose(self) -> ComposeResult:
        with Static(id="modify-dialog"):
            yield Label("Command to execute:")
            yield Input(value=self._initial, id="cmd-input")
            yield Button("Run  [Enter]", variant="primary", id="run")
            yield Button("Cancel  [ESC]", id="cancel")

    def on_mount(self) -> None:
        inp = self.query_one("#cmd-input", Input)
        inp.focus()
        inp.cursor_position = len(inp.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run":
            self.dismiss(self.query_one("#cmd-input", Input).value)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmModal(ModalScreen[bool]):
    """Yes / No confirmation dialog."""

    BINDINGS = [("escape", "no", "No"), ("n", "no", "No"),
                ("y", "yes", "Yes"), ("enter", "yes", "Yes")]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Static(id="confirm-dialog"):
            yield Label(self._message, id="confirm-msg")
            yield Button("Yes  [y]", variant="error", id="yes")
            yield Button("No  [n / ESC]", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


# ── Main application ──────────────────────────────────────────────────────────


class TCalApp(App[None]):
    DEFAULT_CSS = """
    Screen {
        background: $surface;
    }
    Vertical#frame {
        height: 1fr;
        border: solid $primary;
        padding: 0;
    }
    GanttHeader {
        height: 7;
        padding: 0 1;
        background: $primary-darken-2;
        color: white;
        border-bottom: solid $primary;
    }
    #task-list {
        height: 1fr;
        border: none;
        background: $surface;
    }
    TaskListItem {
        height: auto;
        padding: 0 1;
        background: $surface;
    }
    TaskListItem.--highlight {
        background: $accent 30%;
    }
    TaskListItem.selected {
        background: $success 25%;
    }
    TaskListItem.selected.--highlight {
        background: $success 45%;
    }
    #info-dialog, #modify-dialog, #confirm-dialog {
        width: 80%;
        height: auto;
        max-height: 40;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
        layer: overlay;
        align: center middle;
    }
    #info-title { text-style: bold; padding-bottom: 1; }
    #info-body  { height: auto; max-height: 30; overflow-y: auto; padding: 1 0; }
    #modify-dialog Label { padding-bottom: 1; }
    #cmd-input  { width: 100%; margin-bottom: 1; }
    #confirm-msg { padding-bottom: 1; }
    Button { margin: 0 1; }
    Footer { background: $panel; }
    """

    BINDINGS = [
        # Navigation
        Binding("j", "cursor_down", "↓", show=False),
        Binding("k", "cursor_up", "↑", show=False),
        Binding("down", "cursor_down", "↓", show=False),
        Binding("up", "cursor_up", "↑", show=False),
        Binding("g", "goto_top", "Top", show=False),
        Binding("G", "goto_bottom", "Bottom", show=False),
        # Task actions
        Binding("space", "toggle_selection", "Select", show=True),
        Binding("d", "mark_done", "Done"),
        Binding("e", "delete_task", "Delete"),
        Binding("i", "show_info", "Info"),
        Binding("o", "open_note", "Note"),
        Binding("m", "modify_task", "Modify"),
        Binding("enter", "modify_task", "Modify", show=False),
        # Due-date shortcuts
        Binding("0", "due_shortcut('0')", "Today", show=False),
        Binding("1", "due_shortcut('1')", "1d", show=False),
        Binding("2", "due_shortcut('2')", "2d", show=False),
        Binding("3", "due_shortcut('3')", "3d", show=False),
        Binding("4", "due_shortcut('4')", "4d", show=False),
        Binding("5", "due_shortcut('5')", "5d", show=False),
        Binding("6", "due_shortcut('6')", "6d", show=False),
        Binding("7", "due_shortcut('7')", "7d", show=False),
        Binding("8", "due_shortcut('8')", "1w", show=False),
        Binding("9", "due_shortcut('9')", "2w", show=False),
        # View
        Binding("p", "toggle_project", "By project"),
        Binding("l", "toggle_list_mode", "List/GANTT"),
        Binding("r", "refresh_tasks", "Refresh"),
        # Other
        Binding("slash", "direct_command", "Command"),
        Binding("question_mark", "show_help", "Help"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit", show=False),
    ]

    def __init__(
        self,
        filter_str: str,
        by_project: bool = False,
        list_mode: bool = False,
    ) -> None:
        super().__init__()
        self.filter_str = filter_str
        self.by_project = by_project
        self.list_mode = list_mode
        self.context_name, _ = client.get_context()
        self.tasks: list[Task] = []
        self._ws = week_start(date.today())
        self._selected_ids: set[int] = set()
        cfg = _load_config()
        if "theme" in cfg:
            self.theme = cfg["theme"]

    def watch_theme(self, theme: str) -> None:
        cfg = _load_config()
        cfg["theme"] = theme
        _save_config(cfg)

    # ── Compose & mount ───────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Vertical(id="frame"):
            yield GanttHeader("", id="gantt-header")
            yield ListView(id="task-list")
        yield Footer()

    def on_mount(self) -> None:
        # Defer until after the first layout pass so self.size.width is real.
        self.call_after_refresh(self._load_and_render)
        self.call_after_refresh(lambda: self.query_one("#task-list", ListView).focus())

    def on_resize(self) -> None:
        # Guard: may fire before on_mount has run.
        try:
            self._render_header()
        except Exception:
            pass

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _weeks_to_show(self) -> int:
        # size.width can be 0 before first layout pass; fall back to 80.
        w = self.size.width or 80
        return max(1, w // (3 * 7))

    def _load_and_render(self) -> None:
        self.tasks = sort_tasks(
            client.export(self.filter_str),
            by_project=self.by_project,
            list_mode=self.list_mode,
        )
        self._render_header()
        self._render_list()

    def _render_header(self) -> None:
        header = self.query_one("#gantt-header", GanttHeader)
        mode = "LIST" if self.list_mode else ("GANTT · by project" if self.by_project else "GANTT")
        ctx = f"  ·  context: {self.context_name}" if self.context_name else ""
        sel = f"  ·  {len(self._selected_ids)} selected" if self._selected_ids else ""
        status_line = Text(f"tcal  ·  {mode}{ctx}  ·  {len(self.tasks)} tasks{sel}  ·  task {self.filter_str}\n", style="bold")

        if self.list_mode:
            header.styles.height = 2  # status line + blank line
            header.update(status_line)
        else:
            header.styles.height = 7  # status + blank + date row + 3 letter rows + border
            weeks = self._weeks_to_show()
            full = Text()
            full.append_text(status_line)
            full.append("\n")
            full.append_text(build_gantt_header(self._ws, weeks))
            header.update(full)

    def _render_list(self) -> None:
        lv = self.query_one("#task-list", ListView)
        # Remember current position so we can restore it after reload.
        old_index = lv.index or 0

        lv.clear()
        seen_projects: set[str] = set()
        items: list[TaskListItem] = []

        seen_top: set[str] = set()
        for task in self.tasks:
            if self.by_project:
                if not task.project:
                    bucket = "(no project)"
                    if bucket not in seen_projects:
                        seen_projects.add(bucket)
                        sep = Text("\n(no project)" if self.list_mode else "(no project)",
                                   style="bold cyan")
                        items.append(TaskListItem(None, sep))
                else:
                    parts = task.project.split(".", 1)
                    top = parts[0]
                    sub = parts[1] if len(parts) > 1 else None

                    if top not in seen_top:
                        seen_top.add(top)
                        sep = Text("\n" + top.lower() if self.list_mode else top.lower(),
                                   style="bold underline cyan")
                        items.append(TaskListItem(None, sep))

                    full = task.project
                    if full not in seen_projects:
                        seen_projects.add(full)
                        if sub is not None:
                            sub_label = "  " + sub.lower()
                            sep2 = Text("\n" + sub_label if self.list_mode else sub_label,
                                        style="cyan")
                            items.append(TaskListItem(None, sep2))

            text = build_task_text(task, self._ws, gantt_mode=not self.list_mode)
            items.append(TaskListItem(task, text))

        for item in items:
            lv.append(item)

        if items:
            lv.index = min(old_index, len(lv.children) - 1)

        # Re-apply selected highlight after re-render.
        for child in lv.children:
            if isinstance(child, TaskListItem) and child.tw_task:
                child.set_class(child.tw_task.id in self._selected_ids, "selected")

    def _current_task(self) -> Optional[Task]:
        lv = self.query_one("#task-list", ListView)
        item = lv.highlighted_child
        if isinstance(item, TaskListItem):
            return item.tw_task  # None for project-header rows
        return None

    def _effective_tasks(self) -> list[Task]:
        """Selected tasks if any; otherwise just the cursor task."""
        if self._selected_ids:
            return [t for t in self.tasks if t.id in self._selected_ids]
        task = self._current_task()
        return [task] if task else []

    def _task_ids_arg(self, tasks: list[Task]) -> str:
        """Comma-separated ID string, with rc.bulk suppression for >1 task."""
        ids = ",".join(str(t.id) for t in tasks)
        bulk = f" rc.bulk:{len(tasks) + 1}" if len(tasks) > 1 else ""
        return f"{ids}{bulk}"

    def _run_cmd_and_refresh(self, cmd: Optional[str]) -> None:
        if not cmd:
            return
        stdout, stderr = client.run(cmd)
        self._selected_ids.clear()
        self._load_and_render()
        msg = (stdout + stderr).strip() or "Done."
        self.push_screen(InfoModal(msg, title="Result"))

    # ── Navigation actions ────────────────────────────────────────────────────

    def action_cursor_down(self) -> None:
        self.query_one("#task-list", ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#task-list", ListView).action_cursor_up()

    def action_goto_top(self) -> None:
        lv = self.query_one("#task-list", ListView)
        if len(lv.children):
            lv.index = 0

    def action_goto_bottom(self) -> None:
        lv = self.query_one("#task-list", ListView)
        if len(lv.children):
            lv.index = len(lv.children) - 1

    # ── View actions ──────────────────────────────────────────────────────────

    def action_toggle_project(self) -> None:
        self.by_project = not self.by_project
        self._load_and_render()

    def action_toggle_list_mode(self) -> None:
        self.list_mode = not self.list_mode
        self._load_and_render()

    def action_refresh_tasks(self) -> None:
        self._load_and_render()

    def action_show_help(self) -> None:
        self.push_screen(InfoModal(HELP_TEXT, title="Help"))

    # ── Task actions ──────────────────────────────────────────────────────────

    def action_toggle_selection(self) -> None:
        task = self._current_task()
        if task is None:
            return
        item = self.query_one("#task-list", ListView).highlighted_child
        if task.id in self._selected_ids:
            self._selected_ids.discard(task.id)
            if isinstance(item, TaskListItem):
                item.remove_class("selected")
        else:
            self._selected_ids.add(task.id)
            if isinstance(item, TaskListItem):
                item.add_class("selected")
        self._render_header()  # update selection count in status line
        self.query_one("#task-list", ListView).action_cursor_down()

    def action_open_note(self, url: str | None = None) -> None:
        """Open the Obsidian note linked from the current task (or *url*)."""
        if url is None:
            task = self._current_task()
            if task is None:
                return
            for ann in task.annotations:
                _, found = split_note_annotation(ann.description)
                if found:
                    url = found
                    break
        if url is None:
            self.notify("No Obsidian note linked to this task", severity="warning")
            return
        try:
            subprocess.Popen(["open", url])
        except OSError as exc:  # pragma: no cover
            self.notify(f"Could not open note: {exc}", severity="error")

    def action_show_info(self) -> None:
        task = self._current_task()
        if task is None:
            return
        self.push_screen(InfoModal(client.task_info(task.id), title=f"Task {task.id}"))

    def action_mark_done(self) -> None:
        tasks = self._effective_tasks()
        if not tasks:
            return
        ids_arg = self._task_ids_arg(tasks)
        summary = f"{len(tasks)} tasks" if len(tasks) > 1 else tasks[0].description

        def _confirm(confirmed: bool) -> None:
            if confirmed:
                self._run_cmd_and_refresh(f"task {ids_arg} done rc.confirmation=off")

        self.push_screen(ConfirmModal(f"Mark done?\n\n{summary}"), _confirm)

    def action_delete_task(self) -> None:
        tasks = self._effective_tasks()
        if not tasks:
            return
        ids_arg = self._task_ids_arg(tasks)
        summary = f"{len(tasks)} tasks" if len(tasks) > 1 else tasks[0].description

        def _confirm(confirmed: bool) -> None:
            if confirmed:
                self._run_cmd_and_refresh(f"task {ids_arg} rc.confirmation=false rm")

        self.push_screen(ConfirmModal(f"Delete?\n\n{summary}"), _confirm)

    def action_modify_task(self) -> None:
        tasks = self._effective_tasks()
        if not tasks:
            return
        ids_arg = self._task_ids_arg(tasks)
        self.push_screen(ModifyModal(f"task {ids_arg} mod "), self._run_cmd_and_refresh)

    def action_direct_command(self) -> None:
        def _run(cmd: Optional[str]) -> None:
            if cmd:
                self._run_cmd_and_refresh(f"task {cmd}")
        self.push_screen(ModifyModal(""), _run)

    def action_due_shortcut(self, key: str) -> None:
        tasks = self._effective_tasks()
        if not tasks:
            return
        mod = DUE_SHORTCUTS.get(key, "")
        if not mod:
            return
        ids_arg = self._task_ids_arg(tasks)
        self.push_screen(ModifyModal(f"task {ids_arg} {mod}"), self._run_cmd_and_refresh)
