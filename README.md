# tcal — a GANTT-style terminal UI for Taskwarrior

`tcal` shows your pending [Taskwarrior](https://taskwarrior.org/) tasks on a
week-by-week timeline, indented by due date, so you can see at a glance what
is overdue, what is due today and what is coming up. From the same screen you
can mark tasks done, move due dates with a single keystroke, modify or delete
tasks, undo mistakes, and open linked notes — without typing `task` commands.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Taskwarrior 3](https://img.shields.io/badge/taskwarrior-3.x-green)
![Licence GPL-2.0](https://img.shields.io/badge/licence-GPL--2.0-lightgrey)

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ tcal  ·  GANTT  ·  8 tasks  ·  task due.any: status:pending                                  │
│                                                                                              │
│ 02 Nov 2026          09 Nov 2026          16 Nov 2026          23 Nov 2026                   │
│ M  T  W  T  F  S  S  M  T  W  T  F  S  S  M  T  W  T  F  S  S  M  T  W  T  F  S  S           │
│ O  U  E  H  R  A  U  O  U  E  H  R  A  U  O  U  E  H  R  A  U  O  U  E  H  R  A  U           │
│ N  E  D  U  I  T  N  N  E  D  U  I  T  N  N  E  D  U  I  T  N  N  E  D  U  I  T  N           │
│──────────────────────────────────────────────────────────────────────────────────────────────│
│       (admin) 1 Renew car licence                                                            │
│          (work.report) 2*SEND DRAFT REPORT TO CLIENT                                         │
│            2026-11-06 Client wants the executive summary first                               │
│             (home) 4 [errand] Collect parcel from post office                                │
│             (work.report) 3 Reply to reviewer comments                                       │
│                         (work.tender) 5*Prepare pricing schedule                             │
│                           2026-11-06 Tender kick-off meeting                                 │
│                            (admin) 6 Pay quarterly VAT                                       │
│                                  (work.report) 7 Final report due                            │
│                                              (home) 8 Book dentist appointment               │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
 space Select  d Done  e Delete  i Info  o Note  m Modify  u Undo  p By project  l List/GANTT …
```

Each task sits in the column of the day it is due (three characters per day,
with the Monday of the current week at the left edge). In the terminal,
overdue tasks are red and today's tasks are green: here task 1 is overdue,
tasks 3 and 4 are due today, and task 2 is a high-priority task shown in
capitals.

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Command-line options and filters](#command-line-options-and-filters)
- [The views](#the-views)
- [Reading a task line](#reading-a-task-line)
- [Keys](#keys)
- [Working with several tasks at once](#working-with-several-tasks-at-once)
- [Changing tasks](#changing-tasks)
- [Undo](#undo)
- [Obsidian note links](#obsidian-note-links)
- [Themes](#themes)
- [Tips](#tips)
- [Development](#development)
- [History and licence](#history-and-licence)

## Requirements

- **Taskwarrior 3.x** (`task` must be on your `PATH`; developed against 3.5.0)
- **Python 3.11 or newer**
- [**uv**](https://docs.astral.sh/uv/) is the easiest way to install; `pip` also works
- A terminal of at least 80 columns. The wider the terminal, the more weeks
  the timeline shows (one week per 21 columns).

The `o` key, which opens a linked note, uses the macOS `open` command (see
[Obsidian note links](#obsidian-note-links)). Everything else is
platform-independent.

## Installation

Install straight from GitHub as a standalone command:

```bash
uv tool install "git+https://github.com/grovesteyn/tchart.git#subdirectory=tcal"
```

or, if you have cloned the repository and want edits to the source to take
effect immediately:

```bash
uv tool install --editable /path/to/tchart/tcal
```

With plain `pip`:

```bash
pip install "git+https://github.com/grovesteyn/tchart.git#subdirectory=tcal"
```

Either way you end up with a `tcal` command on your `PATH`. Check it with
`tcal --help`.

## Quick start

```bash
tcal
```

This shows every pending task that has a due date, on the timeline. Then:

| Want to…                      | Press                                         |
| ----------------------------- | --------------------------------------------- |
| Move around                   | `↓` / `↑` (or `j` / `k`)                      |
| Mark the task done            | `d`, then `y` to confirm                      |
| Make the task due in 2 days   | `2`, then `Enter`                             |
| See everything about a task   | `i`                                           |
| Change anything else          | `m`, finish the `task … mod` command, `Enter` |
| Take back the last change     | `u`, then `y`                                 |
| See all the keys              | `?`                                           |
| Leave                         | `q`                                           |

## Command-line options and filters

```text
tcal [-p] [-l] [-f EXPR [EXPR ...]]
```

| Option                 | Effect                                                   |
| ---------------------- | -------------------------------------------------------- |
| *(none)*               | Timeline of all pending tasks that have a due date       |
| `-p`, `--byproject`    | Group tasks by project (and sub-project) within the view |
| `-l`, `--list`         | Start in list view instead of the timeline               |
| `-f EXPR…`, `--filter` | Show only the tasks matching a Taskwarrior filter        |

### How the filter is built

`tcal` runs `task <filter> export` and shows what comes back. The filter is
assembled as follows:

1. If a Taskwarrior **context** is active, its read filter is applied first,
   exactly as it would be for `task` itself. The context name is shown in
   the status line.
2. **Without `-f`**, the filter is `due.any: status:pending`: pending tasks
   that have a due date. Tasks without a due date are not shown.
3. **With `-f`**, your expression is used instead, and `status:pending` is
   added unless your expression already mentions `status`. Tasks without a
   due date *are* shown if they match; they appear first, in the Sunday
   column of the current week.

The full filter in use is always shown in the status line at the top of the
screen, so you can see exactly what `task` is being asked for.

Examples:

```bash
tcal -f project:work              # one project
tcal -f +urgent                   # one tag
tcal -f due.before:eom            # due before the end of the month
tcal -f due.after:-10d            # due in the last 10 days or later
tcal -f "project:work -waiting"   # several terms: quote them, or list them separately
tcal -p -f project:work           # combine with the view options
```

> **Filter syntax gotcha.** Taskwarrior's date comparisons use *dot*
> notation: `due.after:-10d`, `due.before:eom`. Writing `due:after:-10d`
> (with a colon) makes Taskwarrior treat `after:-10d` as a literal date, the
> export fails, and `tcal` shows no tasks. If the task count in the status
> line is 0 when you expected tasks, run the filter from the status line
> with `task … export` to see Taskwarrior's error.

## The views

Press `l` to switch between the timeline and the list, and `p` to toggle
project grouping in either one. The status line shows which view is active.

**Timeline (GANTT)** — the default, shown above. Tasks are sorted by due
date, then by project. The header shows as many weeks as fit in the terminal,
starting from the Monday of the current week.

**Timeline, by project (`p`)** — the same timeline, but tasks are grouped
under their top-level project, with dotted sub-projects (`work.report`) as
indented sub-headings:

```text
│ admin                                                                                        │
│       (admin) 1 Renew car licence                                                            │
│                            (admin) 6 Pay quarterly VAT                                       │
│ home                                                                                         │
│             (home) 4 [errand] Collect parcel from post office                                │
│                                              (home) 8 Book dentist appointment               │
│ work                                                                                         │
│   report                                                                                     │
│          (work.report) 2*SEND DRAFT REPORT TO CLIENT                                         │
│            2026-11-06 Client wants the executive summary first                               │
│             (work.report) 3 Reply to reviewer comments                                       │
│                                  (work.report) 7 Final report due                            │
│   tender                                                                                     │
│                         (work.tender) 5*Prepare pricing schedule                             │
│                           2026-11-06 Tender kick-off meeting                                 │
```

**List (`l`)** — a flat list sorted by project, with no timeline header or
indentation. Useful when the terminal is narrow or the due dates are spread
over many weeks. Colours still show what is overdue or due today.

## Reading a task line

```text
(work.report) 2*[errand] SEND DRAFT REPORT TO CLIENT
  2026-11-06 Client wants the executive summary first
```

| Part                        | Meaning                                                                                    |
| --------------------------- | ------------------------------------------------------------------------------------------ |
| `(work.report)`             | Project (`(none)` if the task has no project)                                              |
| `2`                         | Taskwarrior task ID — the number you would use on the command line                         |
| `*` after the ID            | The task has annotations; they are listed underneath, dimmed, with the date each was added |
| `[errand]`                  | Tags, if any                                                                               |
| CAPITALS, bold              | High priority (`priority:H`)                                                               |
| **Red**                     | Overdue (high-priority overdue tasks blink)                                                |
| **Green**                   | Due today                                                                                  |
| Normal                      | Due in the future                                                                          |
| Indentation (timeline only) | Due date: 3 characters per day from the Monday of the current week                         |

## Keys

Keys act on the highlighted task, or on all selected tasks if any are
selected (see [below](#working-with-several-tasks-at-once)). `?` shows this
list inside the program.

### Navigation

| Key       | Action       |
| --------- | ------------ |
| `↓` / `j` | Move down    |
| `↑` / `k` | Move up      |
| `g`       | Go to top    |
| `G`       | Go to bottom |

### Acting on tasks

| Key           | Action                                                                |
| ------------- | --------------------------------------------------------------------- |
| `Space`       | Select / deselect the task and move down                              |
| `d`           | Mark done (asks for confirmation)                                     |
| `e`           | Delete (asks for confirmation)                                        |
| `m` / `Enter` | Modify: opens `task <id> mod ` for you to complete                    |
| `0`–`9`       | Due-date shortcuts, see below                                         |
| `i`           | Show `task <id> info` for the highlighted task                        |
| `o`           | Open the Obsidian note linked to the highlighted task                 |
| `u`           | Undo the most recent Taskwarrior change (shows what it will do first) |

### Due-date shortcuts

These pre-fill the modify command with a new due date; press `Enter` to run
it, or edit it first.

| Key     | Sets due date to  |
| ------- | ----------------- |
| `0`     | Today             |
| `1`–`7` | 1–7 days from now |
| `8`     | 1 week from now   |
| `9`     | 2 weeks from now  |

### View and other

| Key         | Action                                              |
| ----------- | --------------------------------------------------- |
| `p`         | Toggle grouping by project                          |
| `l`         | Toggle timeline / list view                         |
| `r`         | Reload from Taskwarrior                             |
| `/`         | Run any `task` command (type it without the `task`) |
| `Ctrl+P`    | Command palette (change theme, …)                   |
| `?`         | Help                                                |
| `q` / `Esc` | Quit                                                |

Inside a dialog, `Esc` closes the dialog and `y` / `n` answer a confirmation.

## Working with several tasks at once

Press `Space` on a task to select it: it is highlighted in green and the
cursor moves to the next task, so you can run down a list pressing `Space`
on each task you want. The status line shows how many are selected. Press
`Space` again on a selected task to deselect it.

With tasks selected, `d`, `e`, `m` and the due-date shortcuts `0`–`9` act on
**all selected tasks** in one Taskwarrior command (for example
`task 3,4,7 mod due:2d`). The selection is cleared once the command has run.

`i`, `o` and `u` ignore the selection: `i` and `o` always use the highlighted
task, and `u` undoes the last change whatever it was.

## Changing tasks

Every change goes through a real Taskwarrior command, which you see before it
runs:

- **`m` / `Enter`** opens a dialog pre-filled with `task <ids> mod ` and the
  cursor at the end. Type the rest (`due:fri`, `+urgent`, `project:home`,
  `pri:H`, a new description…) and press `Enter`. `Esc` cancels.
- **`0`–`9`** open the same dialog with `due:…` already filled in, so a
  typical reschedule is two keystrokes: `3` `Enter`.
- **`/`** opens an empty dialog for any `task` command. Type it without the
  leading `task`, e.g. `add project:home due:sat Buy paint` or
  `12 annotate Called them, no answer`.
- **`d`** and **`e`** ask for confirmation, then run `task <ids> done` or
  `task <ids> delete`.

After the command runs, the view reloads and Taskwarrior's output is shown
in a dialog (`Esc` or `Enter` closes it). If Taskwarrior reports an error,
nothing has changed; fix the command and try again.

## Undo

Press `u` to revert the most recent change made to your tasks, whether it
was made in `tcal` or from the command line. Before anything happens, a
dialog shows each affected task and what undoing will do, with dates shown
as dates rather than Taskwarrior's internal timestamps:

```text
Undo will make these changes:

  Send draft report to client
      due: Fri 20 Nov 2026 → Tue 10 Nov 2026
```

Press `y` to undo or `n` to keep things as they are. A brief notice confirms
the undo; a dialog appears only if Taskwarrior could not undo. Press `u`
again to go back one more step.

## Obsidian note links

If a task's annotation has the form

```text
Note: <title> — obsidian://open?vault=Work&file=Meetings%2FTender%20kick-off
```

(with an em dash, `—`, surrounded by spaces), `tcal` shows just the title
under the task and makes it a link. A bare `obsidian://…` annotation is shown
as "Obsidian note". To create one:

```bash
task 5 annotate "Note: Tender kick-off meeting — obsidian://open?vault=Work&file=Meetings%2FTender%20kick-off"
```

To open the note, press `o` on the task, click the title (Ghostty, Kitty,
WezTerm) or Cmd-click it (iTerm2). Opening uses the macOS `open` command; on
Linux, change `"open"` to `"xdg-open"` in `action_open_note` in
`tcal/src/tcal/app.py`.

## Themes

`tcal` uses [Textual](https://textual.textualize.io/)'s built-in themes.
Press `Ctrl+P`, choose *Theme* and pick one. The choice is saved to
`~/.config/tcal/config.json` and used next time.

## Tips

- **Aliases for your usual views**, for example in `~/.zshrc`:

  ```bash
  alias tww='tcal -p -f project:work'
  alias tc2='tcal -f due.before:2w'
  ```

- **Contexts.** `task context work` narrows `tcal` just as it narrows
  `task`; the active context is named in the status line.
- **Narrow terminal?** Press `l` for the list view, which needs no width.
- **Nothing shown?** Check the task count and filter in the status line, and
  see the filter gotcha above.

## Development

The package lives in [`tcal/`](tcal/) and is managed with
[uv](https://docs.astral.sh/uv/):

```bash
cd tcal
uv run tcal                 # run from source
uv sync --extra dev         # ruff and textual-dev
uv run ruff check src
```

```text
tcal/src/tcal/
├── __main__.py   # command-line parsing and filter construction
├── app.py        # the Textual application: screen layout, keys, dialogs
├── client.py     # runs `task` (export, info, undo) and parses the results
├── display.py    # sorting, the timeline header and the task lines
└── models.py     # Task and Annotation dataclasses
```

`client.py` is the only module that talks to Taskwarrior. It runs the `task`
command and reads its JSON export, so `tcal` never touches the task database
directly.

Contributions and pull requests are welcome.

## History and licence

This project began in 2013 as **tchart**, a single Python script that
printed a GANTT-style report and offered a curses listbox for quick edits.
It was rewritten in 2026 as **tcal**, a full-screen
[Textual](https://textual.textualize.io/) application for Taskwarrior 3, with
the same timeline idea and a much larger set of keys. The repository keeps
its original name.

Licensed under the [GNU General Public License, version 2](LICENSE).
