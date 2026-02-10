#!/usr/bin/env python3
"""buddy.py - A cozy ASCII pocket pet for your terminal.

A single-file, zero-dependency CLI tool that renders a gentle ASCII
companion with mood-driven animations. Runs for a bounded duration,
then exits cleanly.

Usage:
    python buddy.py
    python buddy.py --name Mochi --mood happy --duration 30
"""

from __future__ import annotations

import argparse
import enum
import os
import random
import sys
import time
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VERSION = "1.0.0"

_MIN_DURATION_SECONDS = 5
_MAX_DURATION_SECONDS = 120
_DEFAULT_DURATION_SECONDS = 30

_FRAME_INTERVAL_SECONDS = 0.15
_ACTION_HOLD_FRAMES = 12
_BLINK_HOLD_FRAMES = 3

# ANSI escape helpers - safe on macOS, Linux, and Windows 10+ terminals.
_ESC_CLEAR = "\033[2J"
_ESC_HOME = "\033[H"
_ESC_HIDE_CURSOR = "\033[?25l"
_ESC_SHOW_CURSOR = "\033[?25h"
_ESC_CLEAR_LINE = "\033[K"


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class Mood(enum.Enum):
    """Behavioral mood that governs which animations the pet performs."""

    HAPPY = "happy"
    CHILL = "chill"
    SLEEPY = "sleepy"


class Action(enum.Enum):
    """Discrete animation the pet can perform between idle frames."""

    IDLE = "idle"
    BLINK = "blink"
    WIGGLE = "wiggle"
    BOUNCE = "bounce"
    DOZE = "doze"


@dataclass(frozen=True)
class PetConfig:
    """Immutable configuration for a single run of the pet."""

    name: str
    mood: Mood
    duration: int  # seconds


# ---------------------------------------------------------------------------
# Action weights per mood
# ---------------------------------------------------------------------------

# Mapping from mood to (action, relative_weight) pairs.  Weights are
# integers so the selection logic stays free of floating-point drift.
_MOOD_WEIGHTS: dict[Mood, list[tuple[Action, int]]] = {
    Mood.HAPPY: [
        (Action.IDLE, 3),
        (Action.BLINK, 3),
        (Action.WIGGLE, 3),
        (Action.BOUNCE, 2),
    ],
    Mood.CHILL: [
        (Action.IDLE, 5),
        (Action.BLINK, 3),
        (Action.WIGGLE, 1),
    ],
    Mood.SLEEPY: [
        (Action.IDLE, 3),
        (Action.BLINK, 2),
        (Action.DOZE, 4),
    ],
}


# ---------------------------------------------------------------------------
# ASCII art frames
# ---------------------------------------------------------------------------

_FRAME_IDLE = r"""
  /\_/\
 ( o.o )
  > ^ <
"""

_FRAME_BLINK = r"""
  /\_/\
 ( -.- )
  > ^ <
"""

_FRAME_WIGGLE_LEFT = r"""
  /\_/\
 ( o.o )
 /> ^ <
"""

_FRAME_WIGGLE_RIGHT = r"""
  /\_/\
 ( o.o )
  > ^ <\
"""

_FRAME_BOUNCE_UP = r"""
  /\_/\
 ( ^.^ )
  > ^ <
  /   \
"""

_FRAME_BOUNCE_DOWN = r"""

  /\_/\
 ( ^.^ )
  > ^ <
"""

_FRAME_DOZE = r"""
  /\_/\
 ( -.- ) z
  > ^ <
"""

_FRAME_DOZE_DEEP = r"""
  /\_/\
 ( -.- ) zZ
  > ^ <
"""


# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------


def _clamped_duration(value: str) -> int:
    """Validate and clamp the --duration flag to the allowed range.

    Args:
        value: Raw string from argparse.

    Returns:
        Duration in seconds, clamped to [_MIN_DURATION_SECONDS, _MAX_DURATION_SECONDS].

    Raises:
        argparse.ArgumentTypeError: If the value is not a valid integer.

    """
    try:
        parsed = int(value)
    except ValueError as exc:
        msg = f"'{value}' is not a valid integer"
        raise argparse.ArgumentTypeError(msg) from exc

    return max(_MIN_DURATION_SECONDS, min(parsed, _MAX_DURATION_SECONDS))


def parse_args(argv: list[str] | None = None) -> PetConfig:
    """Parse command-line arguments into an immutable PetConfig.

    Args:
        argv: Argument list.  Defaults to sys.argv[1:] when None.

    Returns:
        Fully validated PetConfig ready for the animation loop.

    """
    parser = argparse.ArgumentParser(
        prog="buddy",
        description="A cozy ASCII pocket pet that keeps you company.",
        epilog="Press Ctrl+C at any time to say goodbye early.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="Buddy",
        help="Give your pet a name (default: Buddy)",
    )
    parser.add_argument(
        "--mood",
        type=str,
        choices=[m.value for m in Mood],
        default=Mood.CHILL.value,
        help="Set the pet's mood (default: chill)",
    )
    parser.add_argument(
        "--duration",
        type=_clamped_duration,
        default=_DEFAULT_DURATION_SECONDS,
        metavar="SECONDS",
        help=(
            f"How long the pet stays, in seconds "
            f"({_MIN_DURATION_SECONDS}-{_MAX_DURATION_SECONDS}, "
            f"default: {_DEFAULT_DURATION_SECONDS})"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_VERSION}",
    )

    args = parser.parse_args(argv)
    return PetConfig(
        name=args.name,
        mood=Mood(args.mood),
        duration=args.duration,
    )


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------


def _enable_win_vt() -> None:
    """Enable virtual-terminal processing on Windows 10+.

    No-op on non-Windows platforms.  Silently ignored if the call fails
    (e.g. older Windows or non-console handle).
    """
    if os.name != "nt":
        return
    try:
        import ctypes  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        # 0x0004 = ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except (ImportError, OSError, ValueError):
        pass


def clear_screen() -> None:
    """Clear the terminal and reset the cursor to the top-left corner."""
    sys.stdout.write(_ESC_CLEAR + _ESC_HOME)
    sys.stdout.flush()


def _hide_cursor() -> None:
    """Hide the terminal cursor for cleaner animation."""
    sys.stdout.write(_ESC_HIDE_CURSOR)
    sys.stdout.flush()


def _show_cursor() -> None:
    """Restore the terminal cursor."""
    sys.stdout.write(_ESC_SHOW_CURSOR)
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render(name: str, frame: str, status: str) -> None:
    """Write a single animation frame to the terminal.

    Moves the cursor home instead of clearing to avoid full-screen flicker.
    Each output line is padded with a clear-to-EOL escape so leftover
    characters from wider previous frames are erased.

    Args:
        name: Display name shown above the pet.
        frame: Multi-line ASCII art string for this frame.
        status: Short status line shown below the pet.

    """
    lines: list[str] = [
        "",
        f"  {name}",
        *frame.strip("\n").splitlines(),
        "",
        f"  {status}",
        "",
    ]
    buf = _ESC_HOME + "".join(line + _ESC_CLEAR_LINE + "\n" for line in lines)
    sys.stdout.write(buf)
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Animation primitives
# ---------------------------------------------------------------------------


def idle_frames() -> list[str]:
    """Return frames for the idle (standing) animation.

    Returns:
        Single-element list containing the default pose.

    """
    return [_FRAME_IDLE]


def blink_frames() -> list[str]:
    """Return frames for a single eye-blink.

    Returns:
        Sequence: eyes closed, then eyes open.

    """
    return [_FRAME_BLINK] * _BLINK_HOLD_FRAMES + [_FRAME_IDLE]


def wiggle_frames() -> list[str]:
    """Return frames for a left-right wiggle.

    Returns:
        Sequence alternating left and right leans.

    """
    return [
        _FRAME_WIGGLE_LEFT,
        _FRAME_IDLE,
        _FRAME_WIGGLE_RIGHT,
        _FRAME_IDLE,
        _FRAME_WIGGLE_LEFT,
        _FRAME_IDLE,
    ]


def bounce_frames() -> list[str]:
    """Return frames for a small vertical bounce.

    Returns:
        Sequence: up, down, up, settle.

    """
    return [
        _FRAME_BOUNCE_UP,
        _FRAME_BOUNCE_DOWN,
        _FRAME_BOUNCE_UP,
        _FRAME_IDLE,
    ]


def doze_frames() -> list[str]:
    """Return frames for a sleepy doze animation.

    Returns:
        Sequence cycling through doze depths.

    """
    return [
        _FRAME_DOZE,
        _FRAME_DOZE,
        _FRAME_DOZE_DEEP,
        _FRAME_DOZE_DEEP,
        _FRAME_DOZE,
        _FRAME_BLINK,
    ]


_ACTION_FRAMES: dict[Action, list[str]] = {
    Action.IDLE: idle_frames(),
    Action.BLINK: blink_frames(),
    Action.WIGGLE: wiggle_frames(),
    Action.BOUNCE: bounce_frames(),
    Action.DOZE: doze_frames(),
}

_ACTION_STATUS: dict[Action, str] = {
    Action.IDLE: "...",
    Action.BLINK: "*blink*",
    Action.WIGGLE: "~wiggle~",
    Action.BOUNCE: "^bounce^",
    Action.DOZE: "zzz...",
}


# ---------------------------------------------------------------------------
# Action selection
# ---------------------------------------------------------------------------


def choose_action(mood: Mood) -> Action:
    """Select a random action weighted by the pet's current mood.

    Uses ``random.choices`` with integer weights so results are
    deterministic for a given PRNG state.

    Args:
        mood: The pet's active mood governing action probabilities.

    Returns:
        A single Action to animate next.

    """
    entries = _MOOD_WEIGHTS[mood]
    actions = [a for a, _ in entries]
    weights = [w for _, w in entries]
    return random.choices(actions, weights=weights, k=1)[0]  # noqa: S311


# ---------------------------------------------------------------------------
# Greeting / Goodbye
# ---------------------------------------------------------------------------


def print_greeting(config: PetConfig) -> None:
    """Render the opening greeting when the pet appears.

    Args:
        config: Current run configuration.

    """
    clear_screen()
    lines = [
        "",
        f"  {config.name} has arrived!",
        f"  Mood: {config.mood.value}",
        f"  Staying for {config.duration}s",
        "",
    ]
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()
    time.sleep(1.5)


def print_goodbye(name: str) -> None:
    """Render the farewell message when the pet leaves.

    Args:
        name: The pet's display name.

    """
    clear_screen()
    lines = [
        "",
        f"  {name} waves goodbye!",
        "",
        _FRAME_IDLE,
        "  See you next time!",
        "",
    ]
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Main animation loop
# ---------------------------------------------------------------------------


def run_animation(config: PetConfig) -> None:
    """Drive the frame-based animation loop until duration expires.

    The loop is structured around *actions*: each action is a short
    sequence of frames held for ``_ACTION_HOLD_FRAMES`` ticks before
    a new action is chosen.  Between actions, the pet returns to idle
    for a brief rest so the rhythm feels calm rather than frenetic.

    Args:
        config: Current run configuration.

    """
    deadline = time.monotonic() + config.duration
    frames_in_action = 0
    current_action = Action.IDLE
    current_frames = _ACTION_FRAMES[Action.IDLE]
    frame_index = 0

    while time.monotonic() < deadline:
        # Advance or pick a new action when the current one completes.
        if frames_in_action >= _ACTION_HOLD_FRAMES:
            current_action = choose_action(config.mood)
            current_frames = _ACTION_FRAMES[current_action]
            frame_index = 0
            frames_in_action = 0

        frame_art = current_frames[frame_index % len(current_frames)]
        status = _ACTION_STATUS[current_action]

        render(config.name, frame_art, status)

        frame_index += 1
        frames_in_action += 1
        time.sleep(_FRAME_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments, run the animation, and exit cleanly."""
    config = parse_args()

    _enable_win_vt()
    _hide_cursor()

    try:
        print_greeting(config)
        run_animation(config)
    except KeyboardInterrupt:
        pass
    finally:
        _show_cursor()
        print_goodbye(config.name)


if __name__ == "__main__":
    main()
