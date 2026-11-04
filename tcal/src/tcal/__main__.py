"""CLI entry point: parse arguments, build the Taskwarrior filter, launch the app."""
from __future__ import annotations

import argparse

from . import client
from .app import TCalApp


def _build_filter(args: argparse.Namespace) -> str:
    """
    Construct the filter string passed to `task … export`.

    - If a TW context is active its read-filter is prepended.
    - If the user supplies --filter it is appended (with status:pending added
      when missing).
    - Without --filter we default to tasks that have any due date set.

    `export` and `rc.verbose:nothing` are intentionally omitted here;
    client.export() appends them.
    """
    _, context_filter = client.get_context()

    parts: list[str] = []
    if context_filter:
        parts.append(f"({context_filter})")

    if args.filter:
        user_filter = " ".join(args.filter)
        parts.append(user_filter)
        combined = " ".join(parts)
        if "status:" not in combined and "status." not in combined:
            combined += " status:pending"
    else:
        combined = " ".join(parts)
        suffix = "due.any: status:pending"
        combined = f"{combined} {suffix}".strip() if combined else suffix

    return combined


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tcal",
        description="Taskwarrior GANTT / list TUI",
    )
    parser.add_argument(
        "-p", "--byproject",
        action="store_true",
        help="Sort tasks by project before date",
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="Start in list mode instead of GANTT",
    )
    parser.add_argument(
        "-f", "--filter",
        nargs="+",
        metavar="EXPR",
        help="Taskwarrior filter expression (passed directly to task)",
    )
    args = parser.parse_args()

    filter_str = _build_filter(args)

    TCalApp(
        filter_str=filter_str,
        by_project=args.byproject,
        list_mode=args.list,
    ).run()


if __name__ == "__main__":
    main()
