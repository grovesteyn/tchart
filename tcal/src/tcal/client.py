"""Taskwarrior 3.x interface via subprocess + JSON export."""
from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime, timedelta
from typing import Optional

from .models import Annotation, Task

# Compute local timezone offset once at import time.
_TZ_OFFSET = time.timezone if time.localtime().tm_isdst == 0 else time.altzone


def _to_local(s: str) -> datetime:
    """Convert a Taskwarrior UTC timestamp string to a local datetime."""
    return datetime.strptime(s, "%Y%m%dT%H%M%SZ") - timedelta(seconds=_TZ_OFFSET)


def get_context() -> tuple[str, str]:
    """Return (context_name, context_read_filter). Both empty if no context set."""
    name = subprocess.getoutput("task rc.verbose:nothing _get rc.context").strip()
    if name:
        filter_ = subprocess.getoutput(
            f"task rc.verbose:nothing _get rc.context.{name}.read"
        ).strip()
        return name, filter_
    return "", ""


def export(filter_str: str) -> list[Task]:
    """Run `task <filter_str> export` and return parsed Task objects."""
    cmd = f"task {filter_str} export rc.verbose:nothing"
    output = subprocess.getoutput(cmd)
    if not output.strip() or output.strip().startswith("No matches"):
        return []
    try:
        raw_tasks = json.loads(output)
    except json.JSONDecodeError:
        return []
    return [_parse_task(t) for t in raw_tasks]


def _parse_task(raw: dict) -> Task:
    annotations = [
        Annotation(
            entry=_to_local(a["entry"]) if a["entry"].endswith("Z") else datetime.fromisoformat(a["entry"]),
            description=a["description"],
        )
        for a in raw.get("annotations", [])
    ]
    return Task(
        id=raw.get("id", 0),
        uuid=raw["uuid"],
        description=raw["description"],
        status=raw["status"],
        entry=_to_local(raw["entry"]),
        project=raw.get("project"),
        due=_to_local(raw["due"]) if "due" in raw else None,
        priority=raw.get("priority"),
        tags=raw.get("tags", []),
        annotations=annotations,
        urgency=raw.get("urgency", 0.0),
    )


def run(command: str) -> tuple[str, str]:
    """Run a shell command and return (stdout, stderr)."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr


def task_info(task_id: int) -> str:
    """Return the output of `task <id> info`."""
    return subprocess.getoutput(f"task {task_id} info")


_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_UNDO_PROMPT = "The undo command is not reversible"
# One row of the undo table: a UUID (only on a task's first row) then the operation.
_UNDO_ROW = re.compile(rf"^(?P<uuid>{_UUID})?\s+(?P<op>\S.*)$")
# The operation wordings Taskwarrior 3.x prints in its undo preview.
_OP_UPDATE = re.compile(r"^Update property '(?P<prop>[^']+)' from '(?P<old>.*)' to '(?P<new>.*)'$")
_OP_ADD = re.compile(r"^Add property '(?P<prop>[^']+)' with value '(?P<new>.*)'$")
_OP_DELETE = re.compile(r"^Delete property '(?P<prop>[^']+)' \(was '(?P<old>.*)'\)$")
_OP_TAG = re.compile(r"^(?P<verb>Add|Remove) tag '(?P<tag>.*)'$")
_EPOCH = re.compile(r"^\d{9,11}$")
_NONE = "(none)"


def _fmt_value(value: str) -> str:
    """Show a stored value readably: Unix timestamps become local dates."""
    if not _EPOCH.match(value):
        return value
    dt = datetime.fromtimestamp(int(value))
    fmt = "%a %d %b %Y" if (dt.hour, dt.minute) == (0, 0) else "%a %d %b %Y %H:%M"
    return dt.strftime(fmt)


def _prop_label(prop: str) -> str:
    return "annotation" if prop.startswith("annotation_") else prop


def _describe_undo(op: str, created: bool) -> Optional[str]:
    """
    Turn one Taskwarrior operation into what undoing it will do, as
    "property: current → after undo". Returns None for operations that are
    bookkeeping or already covered by another line.
    """
    m = _OP_UPDATE.match(op) or _OP_ADD.match(op) or _OP_DELETE.match(op)
    if m:
        prop = m.group("prop")
        # 'modified' is Taskwarrior's own change timestamp; 'tags'/'tag_*'
        # duplicate the "Add/Remove tag" lines. Adding a task's properties is
        # covered by "task deleted" when the whole task is being un-created.
        if prop == "modified" or prop == "tags" or prop.startswith("tag_") or created:
            return None
        old = m.groupdict().get("old")
        new = m.groupdict().get("new")
        before = _fmt_value(new) if new is not None else _NONE
        after = _fmt_value(old) if old is not None else _NONE
        return f"{_prop_label(prop)}: {before} → {after}"
    m = _OP_TAG.match(op)
    if m:
        action = "removed" if m.group("verb") == "Add" else "restored"
        return f"tag +{m.group('tag')} {action}"
    if op == "Create task":
        return "task deleted (undoes adding it)"
    return op  # unknown wording: show it as Taskwarrior wrote it


def undo_preview() -> Optional[list[tuple[str, list[str]]]]:
    """
    Describe what `task undo` would change, without changing anything.

    Runs undo with confirmation forced on and answers "no" to the prompt, so
    Taskwarrior prints the operations it would revert and then declines.
    Returns [(task description, [change, ...]), ...], or None when there is
    nothing to undo.
    """
    result = subprocess.run(
        ["task", "rc.confirmation:on", "rc.color:off", "rc.defaultwidth:1000", "undo"],
        input="no\n",
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if _UNDO_PROMPT not in output:
        return None  # e.g. "No operations to undo."
    table = output.split(_UNDO_PROMPT)[0]

    ops_by_uuid: dict[str, list[str]] = {}
    current: Optional[str] = None
    for line in table.splitlines():
        m = _UNDO_ROW.match(line)
        if not m:
            continue  # heading lines
        if m.group("uuid"):
            current = m.group("uuid")
        if current:
            ops_by_uuid.setdefault(current, []).append(m.group("op").strip())

    preview: list[tuple[str, list[str]]] = []
    for uuid, ops in ops_by_uuid.items():
        created = "Create task" in ops
        changes = [c for op in ops if (c := _describe_undo(op, created))]
        desc = subprocess.getoutput(
            f"task rc.verbose:nothing _get {uuid}.description"
        ).strip()
        preview.append((desc or uuid, changes))
    return preview


def undo() -> tuple[bool, str]:
    """Revert the most recent Taskwarrior change. Returns (ok, output)."""
    result = subprocess.run(
        ["task", "rc.confirmation:off", "undo"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()
