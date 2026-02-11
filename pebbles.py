#!/usr/bin/env python3
"""Gratitude Pebbles -- a quiet jar for small, good things."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_ENV_VAR: str = "GRATITUDE_PEBBLES_FILE"
_DEFAULT_PATH: Path = Path.home() / ".gratitude_pebbles.json"
_SHAKE_MIN: int = 3
_SHAKE_MAX: int = 5

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Pebble:
    """A single moment of gratitude."""

    text: str
    timestamp: str  # ISO 8601, UTC


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _data_path() -> Path:
    """Returns the resolved path to the pebbles data file."""
    override = os.environ.get(_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return _DEFAULT_PATH


def _new_pebble(text: str) -> _Pebble:
    """Creates a pebble timestamped to the current UTC moment."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return _Pebble(text=text, timestamp=now)


def _format_date(iso_timestamp: str) -> str:
    """Formats an ISO 8601 timestamp as a short, friendly date."""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%b %d, %Y").lower()
    except ValueError:
        return iso_timestamp


def _pluralize(count: int) -> str:
    """Returns 'pebble' or 'pebbles' based on count."""
    return "pebble" if count == 1 else "pebbles"


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _die(message: str) -> NoReturn:
    """Prints a gentle error message to stderr and exits."""
    print(f"  {message}", file=sys.stderr)
    raise SystemExit(1)


def _put(message: str = "") -> None:
    """Prints a softly indented line, or an empty line if no message."""
    if message:
        print(f"  {message}")
    else:
        print()


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _load(path: Path) -> list[_Pebble]:
    """Reads pebbles from the data file.

    Returns an empty list when the file is missing or empty.

    Raises:
        SystemExit: If the file contains corrupt or unrecognized data.
    """
    if not path.exists():
        return []

    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        _die(f"could not read {path}: {exc}")

    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _die(f"data file is corrupt: {path}")

    if not isinstance(data, list):
        _die(f"unexpected format in {path}")

    pebbles: list[_Pebble] = []
    for entry in data:
        if (
            isinstance(entry, dict)
            and isinstance(entry.get("text"), str)
            and isinstance(entry.get("timestamp"), str)
        ):
            pebbles.append(_Pebble(text=entry["text"], timestamp=entry["timestamp"]))
    return pebbles


def _save(path: Path, pebbles: list[_Pebble]) -> None:
    """Atomically writes pebbles to the data file.

    Writes to a temporary file in the same directory, fsyncs, then
    atomically replaces the target. The data file is never left in a
    partial or corrupt state.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        [asdict(p) for p in pebbles],
        indent=2,
        ensure_ascii=False,
    )

    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    succeeded = False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
        succeeded = True
    finally:
        if not succeeded:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _cmd_add(path: Path, text: str | None) -> int:
    """Adds a new pebble to the jar."""
    if text is None:
        try:
            text = input("  what's something good? ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1

    if not text:
        _put("a pebble needs a few words.")
        return 1

    pebbles = _load(path)
    pebbles.append(_new_pebble(text))
    _save(path, pebbles)
    _put("noted.")
    return 0


def _cmd_shake(path: Path) -> int:
    """Randomly surfaces a handful of past pebbles."""
    pebbles = _load(path)

    if not pebbles:
        _put("your jar is empty.")
        _put('try: pebbles add "something good"')
        return 0

    count = min(len(pebbles), random.randint(_SHAKE_MIN, _SHAKE_MAX))
    chosen = random.sample(pebbles, count)

    _put()
    for pebble in chosen:
        _put(f"  \u00b7 {pebble.text}")
    _put()
    return 0


def _cmd_list(path: Path) -> int:
    """Lists all pebbles in chronological order."""
    pebbles = _load(path)

    if not pebbles:
        _put("no pebbles yet.")
        return 0

    _put()
    for pebble in pebbles:
        date = _format_date(pebble.timestamp)
        _put(f"{date}  {pebble.text}")
    _put()
    return 0


def _cmd_clear(path: Path) -> int:
    """Removes all pebbles after user confirmation."""
    pebbles = _load(path)

    if not pebbles:
        _put("already empty.")
        return 0

    count = len(pebbles)
    noun = _pluralize(count)

    try:
        answer = input(f"  remove {count} {noun}? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return 1

    if answer not in ("y", "yes"):
        _put("kept everything.")
        return 0

    _save(path, [])
    _put("jar emptied.")
    return 0


def _cmd_stats(path: Path) -> int:
    """Shows a brief summary of the jar contents."""
    pebbles = _load(path)

    if not pebbles:
        _put("no pebbles yet.")
        return 0

    first = _format_date(pebbles[0].timestamp)
    latest = _format_date(pebbles[-1].timestamp)
    noun = _pluralize(len(pebbles))

    _put()
    _put(f"{len(pebbles)} {noun}")
    _put(f"first:   {first}")
    _put(f"latest:  {latest}")
    _put()
    return 0


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Constructs the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="pebbles",
        description="a quiet jar for small, good things.",
    )
    sub = parser.add_subparsers(dest="command")

    add_parser = sub.add_parser("add", help="add a pebble")
    add_parser.add_argument("text", nargs="?", default=None, help="a few words")

    sub.add_parser("shake", help="shake the jar")
    sub.add_parser("list", help="list all pebbles")
    sub.add_parser("clear", help="empty the jar")
    sub.add_parser("stats", help="jar summary")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the Gratitude Pebbles CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    path = _data_path()

    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "add":
        return _cmd_add(path, args.text)
    if args.command == "shake":
        return _cmd_shake(path)
    if args.command == "list":
        return _cmd_list(path)
    if args.command == "clear":
        return _cmd_clear(path)
    if args.command == "stats":
        return _cmd_stats(path)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
