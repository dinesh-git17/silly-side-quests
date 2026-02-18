#!/usr/bin/env python3
"""Tiny Day Planner: a calm CLI micro-planner for daily task prioritization.

Transforms a list of tasks into a clear, human-readable daily execution plan.
Outputs the plan to stdout and writes a JSON session file for later reference.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import NoReturn

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SESSION_FILENAME: str = "dayplan_session.json"
MAX_TASKS: int = 50
MAX_CORE: int = 5

_ENERGY_CHOICES: tuple[str, ...] = ("low", "medium", "high")
_FOCUS_CHOICES: tuple[str, ...] = ("work", "personal", "health", "study", "mixed")
_STYLE_CHOICES: tuple[str, ...] = ("soft", "neutral", "direct")

_ENERGY_CORE_MAP: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
}

_CLOSING_LINES: dict[str, tuple[str, ...]] = {
    "soft": (
        "One thing at a time.",
        "That's enough.",
        "You know what matters today.",
        "Begin whenever you're ready.",
        "Small steps count.",
    ),
    "neutral": (
        "Proceed sequentially.",
        "Plan outlined above.",
        "Reference this list as needed.",
    ),
    "direct": (
        "Start now.",
        "Begin with the first task.",
        "Proceed.",
    ),
}

_CORE_LABELS: dict[str, tuple[str, str, str]] = {
    "soft": ("Start with:", "Then:", "If energy allows:"),
    "neutral": ("First:", "Next:", "Additionally:"),
    "direct": ("First:", "Next:", "Then:"),
}

_OPTIONAL_LABELS: dict[str, str] = {
    "soft": "If there's space later:",
    "neutral": "Optional:",
    "direct": "Remaining:",
}

_HEADER_NAMED: dict[str, str] = {
    "soft": "{name}'s gentle plan for today:",
    "neutral": "{name}'s plan for today:",
    "direct": "{name}'s plan for today:",
}

_HEADER_UNNAMED: dict[str, str] = {
    "soft": "Today's gentle plan:",
    "neutral": "Today's plan:",
    "direct": "Today's plan:",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlanConfig:
    """Validated, immutable configuration derived from CLI arguments."""

    tasks: tuple[str, ...]
    name: str | None = None
    energy: str = "medium"
    focus: str | None = None
    max_core: int | None = None
    style: str = "soft"


@dataclass(frozen=True, slots=True)
class Plan:
    """A fully resolved execution plan ready for formatting and export."""

    core_tasks: tuple[str, ...]
    optional_tasks: tuple[str, ...]
    header: str
    focus_line: str | None
    closing_line: str
    config: PlanConfig


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


class _DayPlanParser(argparse.ArgumentParser):
    """ArgumentParser that exits with code 1 on all argument errors."""

    def error(self, message: str) -> NoReturn:
        """Print error to stderr and exit with code 1."""
        print(f"Error: {message}", file=sys.stderr)  # noqa: T201
        sys.exit(1)


def _build_parser() -> _DayPlanParser:
    """Construct the CLI argument parser with all supported flags."""
    parser = _DayPlanParser(
        description=(
            "Tiny Day Planner \u2014 transform tasks into a calm,"
            " human-readable daily plan."
        ),
    )
    parser.add_argument(
        "--tasks",
        type=str,
        default=None,
        help=(
            'Comma-separated list of tasks (e.g. "email boss, grocery run, workout")'
        ),
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Personalize the plan header with your name",
    )
    parser.add_argument(
        "--energy",
        type=str,
        choices=_ENERGY_CHOICES,
        default="medium",
        help="Energy level controlling emphasized task count (default: medium)",
    )
    parser.add_argument(
        "--focus",
        type=str,
        choices=_FOCUS_CHOICES,
        default=None,
        help="Theme for framing the plan tone",
    )
    parser.add_argument(
        "--max-core",
        type=int,
        default=None,
        help="Override automatic core task count (1\u20135)",
    )
    parser.add_argument(
        "--style",
        type=str,
        choices=_STYLE_CHOICES,
        default="soft",
        help="Output tone: soft, neutral, or direct (default: soft)",
    )
    return parser


# ---------------------------------------------------------------------------
# Parsing and validation
# ---------------------------------------------------------------------------


def _parse_task_string(raw: str) -> tuple[str, ...]:
    """Parse a comma-separated task string into a normalized tuple.

    Trims whitespace from each token, discards empty tokens, and preserves
    both duplicates and the original ordering provided by the user.
    """
    tasks: list[str] = []
    for token in raw.split(","):
        cleaned = token.strip()
        if cleaned:
            tasks.append(cleaned)
    return tuple(tasks)


def _validate_and_build_config(args: argparse.Namespace) -> PlanConfig:
    """Validate parsed CLI arguments and construct a PlanConfig.

    Enforces all spec-mandated constraints. Prints error messages to stderr
    and exits with code 1 on any validation failure.
    """
    if args.tasks is None:
        print("Error: No tasks provided.", file=sys.stderr)  # noqa: T201
        print('Use --tasks "task1, task2"', file=sys.stderr)  # noqa: T201
        sys.exit(1)

    tasks = _parse_task_string(args.tasks)

    if not tasks:
        print("Error: No tasks provided.", file=sys.stderr)  # noqa: T201
        print('Use --tasks "task1, task2"', file=sys.stderr)  # noqa: T201
        sys.exit(1)

    if len(tasks) > MAX_TASKS:
        print(  # noqa: T201
            f"Error: Maximum supported tasks is {MAX_TASKS}.",
            file=sys.stderr,
        )
        sys.exit(1)

    max_core: int | None = args.max_core
    if max_core is not None and not 1 <= max_core <= MAX_CORE:
        print(  # noqa: T201
            f"Error: --max-core must be between 1 and {MAX_CORE}.",
            file=sys.stderr,
        )
        sys.exit(1)

    return PlanConfig(
        tasks=tasks,
        name=args.name,
        energy=args.energy,
        focus=args.focus,
        max_core=max_core,
        style=args.style,
    )


# ---------------------------------------------------------------------------
# Planning logic
# ---------------------------------------------------------------------------


def _resolve_core_count(config: PlanConfig) -> int:
    """Determine the number of core tasks.

    Uses --max-core if provided; otherwise derives from energy level.
    The result is clamped to the actual number of available tasks.
    """
    if config.max_core is not None:
        limit = config.max_core
    else:
        limit = _ENERGY_CORE_MAP[config.energy]
    return min(limit, len(config.tasks))


def _classify_tasks(
    config: PlanConfig,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split tasks into core and optional groups.

    The first N tasks become core, preserving user-provided ordering.
    All remaining tasks become optional.
    """
    n = _resolve_core_count(config)
    return config.tasks[:n], config.tasks[n:]


def _build_header(config: PlanConfig) -> str:
    """Generate the plan header line based on name and style."""
    if config.name is not None:
        return _HEADER_NAMED[config.style].format(name=config.name)
    return _HEADER_UNNAMED[config.style]


def _build_focus_line(config: PlanConfig) -> str | None:
    """Generate the focus annotation line, or None if unspecified."""
    if config.focus is None:
        return None
    return f"Focus: {config.focus.capitalize()}"


def _select_closing_line(style: str) -> str:
    """Select a random closing line appropriate to the given style."""
    return random.choice(_CLOSING_LINES[style])  # noqa: S311


def _build_plan(config: PlanConfig) -> Plan:
    """Construct a fully resolved Plan from validated configuration."""
    core, optional = _classify_tasks(config)
    return Plan(
        core_tasks=core,
        optional_tasks=optional,
        header=_build_header(config),
        focus_line=_build_focus_line(config),
        closing_line=_select_closing_line(config.style),
        config=config,
    )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _format_core_section(tasks: tuple[str, ...], style: str) -> str:
    """Format the core task section with style-appropriate labels.

    Returns an empty string when no core tasks exist.
    """
    if not tasks:
        return ""

    first_label, second_label, rest_label = _CORE_LABELS[style]
    lines: list[str] = [first_label, f"\u2022 {tasks[0]}"]

    if len(tasks) >= 2:
        lines.append("")
        lines.append(second_label)
        lines.append(f"\u2022 {tasks[1]}")

    if len(tasks) >= 3:
        lines.append("")
        lines.append(rest_label)
        for task in tasks[2:]:
            lines.append(f"\u2022 {task}")

    return "\n".join(lines)


def _format_optional_section(tasks: tuple[str, ...], style: str) -> str:
    """Format the optional task section.

    Returns an empty string when no optional tasks exist, causing the
    section to be omitted from the final output.
    """
    if not tasks:
        return ""

    lines: list[str] = [_OPTIONAL_LABELS[style]]
    for task in tasks:
        lines.append(f"\u2022 {task}")
    return "\n".join(lines)


def _format_plan(plan: Plan) -> str:
    """Render a Plan into the complete human-readable output string."""
    sections: list[str] = []

    header_block = plan.header
    if plan.focus_line is not None:
        header_block = f"{header_block}\n{plan.focus_line}"
    sections.append(header_block)

    core = _format_core_section(plan.core_tasks, plan.config.style)
    if core:
        sections.append(core)

    optional = _format_optional_section(
        plan.optional_tasks,
        plan.config.style,
    )
    if optional:
        sections.append(optional)

    sections.append(plan.closing_line)

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# JSON session export
# ---------------------------------------------------------------------------


def _export_session(plan: Plan) -> None:
    """Write the current plan to a JSON session file.

    The file is placed in the current working directory, overwriting any
    previous session. On failure, a warning is printed to stderr but
    execution continues and exit code remains 0.
    """
    session: dict[str, str | list[str] | None] = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "name": plan.config.name,
        "focus": plan.config.focus,
        "energy": plan.config.energy,
        "core_tasks": list(plan.core_tasks),
        "optional_tasks": list(plan.optional_tasks),
        "style": plan.config.style,
        "closing_line": plan.closing_line,
    }
    try:
        with open(SESSION_FILENAME, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError as exc:
        print(  # noqa: T201
            f"Warning: Could not write session file: {exc}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Tiny Day Planner.

    Parses CLI arguments, generates a calm daily plan, prints the plan to
    stdout, and writes a JSON session file. Returns 0 on success.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = _validate_and_build_config(args)

    plan = _build_plan(config)
    output = _format_plan(plan)

    print(output)  # noqa: T201
    _export_session(plan)

    return 0


if __name__ == "__main__":
    sys.exit(main())
