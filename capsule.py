#!/usr/bin/env python3
"""Kindness Time Capsule — leave gentle notes for your future self."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_FILE: Path = Path("capsule_data.json")

# --- Data persistence ---


def load_data() -> list[dict[str, Any]]:
    """Read capsule messages from disk, returning an empty list on any failure."""
    if not DATA_FILE.exists():
        return []
    try:
        text = DATA_FILE.read_text(encoding="utf-8")
        data = json.loads(text)
        if isinstance(data, list):
            return data  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_data(capsules: list[dict[str, Any]]) -> None:
    """Write capsule messages to disk as pretty-printed JSON."""
    DATA_FILE.write_text(
        json.dumps(capsules, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# --- Time helpers ---


def _relative_time(iso_stamp: str) -> str:
    """Turn an ISO timestamp into a warm, human-readable relative string."""
    then = datetime.fromisoformat(iso_stamp)
    now = datetime.now(timezone.utc)
    seconds = int((now - then).total_seconds())

    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        unit = "minute" if minutes == 1 else "minutes"
        return f"{minutes} {unit} ago"
    hours = minutes // 60
    if hours < 24:
        unit = "hour" if hours == 1 else "hours"
        return f"{hours} {unit} ago"
    days = hours // 24
    if days < 30:
        unit = "day" if days == 1 else "days"
        return f"{days} {unit} ago"
    months = days // 30
    if months < 12:
        unit = "month" if months == 1 else "months"
        return f"{months} {unit} ago"
    years = days // 365
    unit = "year" if years == 1 else "years"
    return f"{years} {unit} ago"


def _gentle_print(text: str, delay: float = 0.02) -> None:
    """Print text character-by-character for a calm, typewriter feel."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")


# --- Commands ---


def add_message(text: str) -> None:
    """Bury a new message in the capsule for your future self."""
    capsules = load_data()
    capsules.append(
        {
            "message": text,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tags": [],
        }
    )
    save_data(capsules)

    print()
    _gentle_print("  \U0001f331  Your words have been buried safely.")
    _gentle_print("  Someday, you\u2019ll find them again.")
    print()


def open_random() -> None:
    """Open the capsule and rediscover a random past message."""
    capsules = load_data()
    if not capsules:
        print()
        _gentle_print("  The capsule is empty.")
        _gentle_print("  Maybe leave something for future-you?")
        print()
        return

    entry = random.choice(capsules)
    ago = _relative_time(entry["created_at"])

    print()
    print("  \u2500" * 30)
    print()
    _gentle_print(f"  \U0001f4dc  You left this for yourself {ago}:")
    print()
    _gentle_print(f"     \u201c{entry['message']}\u201d")
    print()
    print("  \u2500" * 30)
    print()


def list_messages() -> None:
    """Show every message in the capsule, most recent first."""
    capsules = load_data()
    if not capsules:
        print()
        _gentle_print("  Nothing here yet. The capsule is waiting.")
        print()
        return

    print()
    _gentle_print("  \U0001f30d  Everything you\u2019ve buried so far:\n")

    for i, entry in enumerate(capsules, start=1):
        ago = _relative_time(entry["created_at"])
        preview = entry["message"]
        if len(preview) > 50:
            preview = preview[:47] + "\u2026"
        print(f"  {i:>3}.  \u201c{preview}\u201d")
        print(f"        \u2014 {ago}")
        print()

    print(
        f"  {len(capsules)} little note{'s' if len(capsules) != 1 else ''}, "
        "waiting to be remembered.\n"
    )


def open_oldest() -> None:
    """Revisit the very first message you ever buried."""
    capsules = load_data()
    if not capsules:
        print()
        _gentle_print("  No memories yet. Write one today?")
        print()
        return

    oldest = min(capsules, key=lambda c: c["created_at"])
    ago = _relative_time(oldest["created_at"])

    print()
    _gentle_print("  \U0001f30c  Here\u2019s where it all began\u2026")
    print()
    _gentle_print(f"  You wrote this {ago}:")
    print()
    _gentle_print(f"     \u201c{oldest['message']}\u201d")
    print()
    _gentle_print("  Look how far you\u2019ve come.")
    print()


# --- CLI ---


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the capsule."""
    parser = argparse.ArgumentParser(
        description="Kindness Time Capsule \u2014 leave gentle notes for future-you.",
    )
    sub = parser.add_subparsers(dest="command")

    add_parser = sub.add_parser("add", help="Bury a new message")
    add_parser.add_argument("message", help="The words you want to save")

    sub.add_parser("open", help="Open the capsule and find a surprise")
    sub.add_parser("list", help="See everything you\u2019ve buried")
    sub.add_parser("oldest", help="Revisit your very first message")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        raise SystemExit(0)
    return args


def main() -> None:
    """Entry point for the Kindness Time Capsule."""
    args = parse_args()

    if args.command == "add":
        add_message(args.message)
    elif args.command == "open":
        open_random()
    elif args.command == "list":
        list_messages()
    elif args.command == "oldest":
        open_oldest()


if __name__ == "__main__":
    main()
