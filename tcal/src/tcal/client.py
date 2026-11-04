"""Taskwarrior 3.x interface via subprocess + JSON export."""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timedelta

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
