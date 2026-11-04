"""Pure functions for sorting tasks and building Rich Text for display."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from rich.style import Style
from rich.text import Text

from .models import Task

INDENT = 3  # characters per day column in GANTT mode

# Annotation forms that carry a link to an Obsidian note:
#   "Note: <title> — obsidian://open?vault=Work&file=..."   (readable label + URL)
#   "obsidian://open?vault=Work&file=..."                   (bare URL, older tasks)
_NOTE_ANN = re.compile(r"^Note:\s*(?P<label>.+?)\s+\u2014\s+(?P<url>obsidian://\S+)$")
_BARE_URL = re.compile(r"^(?P<url>obsidian://\S+)$")


def split_note_annotation(description: str) -> tuple[str, str | None]:
    """
    Return (display_text, url) for an annotation.

    A note-link annotation is shown by its readable label; the URL rides along
    as an OSC 8 terminal hyperlink so the label is clickable in terminals that
    support it (iTerm2, Ghostty, Kitty, WezTerm). Other annotations are
    returned unchanged with url=None.
    """
    m = _NOTE_ANN.match(description)
    if m:
        return m.group("label"), m.group("url")
    m = _BARE_URL.match(description)
    if m:
        return "Obsidian note", m.group("url")
    return description, None


def week_start(d: date) -> date:
    """Return the Monday of the week containing *d*."""
    return d - timedelta(days=d.weekday())


def sort_tasks(tasks: list[Task], *, by_project: bool, list_mode: bool) -> list[Task]:
    """
    Split into due / no-due buckets, sort each, then recombine.
    No-due tasks are always placed at the front.
    """
    due = [t for t in tasks if t.due is not None]
    no_due = [t for t in tasks if t.due is None]

    try:
        if list_mode:
            all_tasks = no_due + due
            all_tasks.sort(key=lambda t: (t.project or ""))
        elif by_project:
            due.sort(key=lambda t: (t.project or "", t.due.date()))  # type: ignore[union-attr]
            all_tasks = no_due + due
        else:
            due.sort(key=lambda t: (t.due.date(), t.project or ""))  # type: ignore[union-attr]
            all_tasks = no_due + due
    except (KeyError, AttributeError):
        all_tasks = no_due + sorted(due, key=lambda t: t.due)  # type: ignore[arg-type]

    return all_tasks


def build_task_text(task: Task, ws: date, *, gantt_mode: bool) -> Text:
    """
    Build a Rich Text line (possibly multi-line with annotations) for *task*.

    In GANTT mode the line is indented by (days since Monday) × INDENT spaces.
    """
    if task.due is None:
        # Tasks without a due date are placed at Sunday of the current week.
        tdate = datetime.combine(ws + timedelta(days=6), datetime.min.time())
    else:
        tdate = task.due

    daydiff = (tdate.date() - ws).days if gantt_mode else 0
    pad = " " * INDENT * daydiff

    desc = task.description.upper() if task.priority == "H" else task.description
    project_str = f"({task.project or 'none'})"
    tags_str = f"[{', '.join(task.tags)}] " if task.tags else ""
    annotated = "*" if task.annotations else " "

    line = f"{pad}{project_str} {task.id}{annotated}{tags_str}{desc} "

    text = Text(line, no_wrap=True)

    if tdate.date() < date.today():
        style = "bold bright_red blink" if task.priority == "H" else "bright_red"
    elif tdate.date() == date.today():
        style = "bright_green bold" if task.priority == "H" else "bright_green"
    else:
        style = "bold" if task.priority == "H" else ""

    if style:
        text.stylize(style)

    for ann in task.annotations:
        label, url = split_note_annotation(ann.description)
        text.append(
            f"\n  {pad}{ann.entry.year}-{ann.entry.month:02d}-{ann.entry.day:02d} ",
            style="dim",
        )
        if url:
            # OSC 8 hyperlink for terminals that pass Cmd-click through (iTerm2),
            # plus a Textual click action so it also works where the terminal
            # hands the click to the app (Ghostty, Kitty, WezTerm).
            link_style = Style.parse(f"dim underline link {url}") + Style(
                meta={"@click": f"app.open_note('{url}')"}
            )
            text.append(label, style=link_style)
        else:
            text.append(label, style="dim")

    return text


def build_gantt_header(ws: date, weeks: int) -> Text:
    """Build the date + day-name header for GANTT mode."""
    wdays = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

    # Date line: Monday dates spaced every 7*INDENT characters.
    dateline = ws.strftime("%d %b %Y")
    for w in range(1, weeks):
        target = len(wdays) * w * INDENT
        pad = max(0, target - len(dateline))
        dateline += " " * pad + (ws + timedelta(weeks=w)).strftime("%d %b %Y")

    text = Text(dateline + "\n", style="bold")

    # Three rows of day-name letters (M, O, N / T, U, E / …).
    for row in range(3):
        for day in wdays * weeks:
            letter = day[row]
            text.append(letter, style="bold" if day == "MON" else "")
            text.append(" " * (INDENT - 1))
        text.append("\n")

    return text
