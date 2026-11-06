# tcal

A terminal UI for [Taskwarrior 3](https://taskwarrior.org/) that displays your tasks as a GANTT chart or a sorted list, and lets you act on them without leaving the terminal.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Taskwarrior 3](https://img.shields.io/badge/taskwarrior-3.x-green)

---

## What it does

- Displays pending tasks on a **GANTT timeline** — each task is indented according to its due date so you can see your workload at a glance
- Alternatively shows a **flat list** sorted by project
- Respects your active **Taskwarrior context**
- Lets you **navigate, select, and modify tasks** without typing raw `task` commands
- Supports **multi-selection** — select several tasks and act on all of them at once

---

## Requirements

- [Taskwarrior 3.x](https://taskwarrior.org/download/)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

---

## Installation

```fish
# Install as a global uv tool (run once, works from any directory)
uv tool install --editable /path/to/tcal-git/tcal

# Or from the GitHub repo directly
uv tool install "git+https://github.com/grovesteyn/tchart.git#subdirectory=tcal"
```

After installation, `tcal` is on your PATH.

---

## Usage

```text
tcal [options]
```

| Option | Description |
| --- | --- |
| _(none)_ | Show all tasks that have a due date, sorted by due date |
| `-p` / `--byproject` | Sort by project first, then due date |
| `-l` / `--list` | List mode instead of GANTT |
| `-f EXPR` / `--filter EXPR` | Custom Taskwarrior filter expression |

Examples:

```fish
tcal                        # default GANTT view
tcal -p                     # group by project
tcal -l                     # flat list
tcal -f project:work        # only work tasks
tcal -f "due:week +urgent"  # filter by tag and date range
```

---

## Key bindings

### Navigation

| Key | Action |
| --- | --- |
| `j` / `↓` | Move down |
| `k` / `↑` | Move up |
| `g` | Go to top |
| `G` | Go to bottom |

### Task actions

| Key | Action |
| --- | --- |
| `Space` | Toggle selection (multi-select) |
| `d` | Mark done |
| `e` | Delete (with confirmation) |
| `i` | Show task info |
| `m` / `Enter` | Modify (opens editable command) |
| `u` | Undo the last Taskwarrior change (shows what will be reverted, then asks) |

### Due-date shortcuts

These pre-fill the modify command — press `Enter` to confirm or edit further.

| Key | Sets due date to |
| --- | --- |
| `0` | Today |
| `1` – `7` | N days from now |
| `8` | 1 week |
| `9` | 2 weeks |

### View

| Key | Action |
| --- | --- |
| `p` | Toggle sort-by-project |
| `l` | Toggle GANTT / list mode |
| `r` | Reload from Taskwarrior |
| `/` | Direct task command (without typing `task`) |
| `?` | Show help |
| `q` / `ESC` | Quit |

---

## Multi-selection

Press `Space` to select the current task (highlighted in green) and move to the next one. Repeat for as many tasks as you need. Any action (`d`, `e`, `m`, `0`–`9`) then applies to all selected tasks at once. The selection is cleared after the action completes.

---

## GANTT layout

Tasks are indented from the left edge by the number of days between the current Monday and their due date. Tasks without a due date are shown at the top.

Colour coding:

- **Red** — overdue
- **Green** — due today
- **White** — due in the future
- **Bold + uppercase** — high priority (`priority:H`)
- An asterisk `*` after the task ID indicates the task has annotations

---

## Project structure

```text
src/tcal/
├── __main__.py   # CLI entry point and argument parsing
├── app.py        # Textual TUI application
├── client.py     # Taskwarrior subprocess interface
├── display.py    # GANTT rendering and task sorting
└── models.py     # Task and Annotation data classes
```
