#!/usr/bin/env python3
"""CLI creativity engine that generates playful constraints."""

from __future__ import annotations

import argparse
import enum
import random
import sys
from collections.abc import Sequence
from typing import NamedTuple

EXIT_SUCCESS = 0
EXIT_FAILURE = 1

HEADER = "Constraint Toybox"
PROMPT_LINE = "Today's constraint:"

ENCOURAGEMENTS: tuple[str, ...] = (
    "Try it. See what happens.",
    "Start small. Go anywhere.",
    "No rules after this one.",
    "Make something. Anything.",
    "Begin before you're ready.",
    "The only wrong move is not starting.",
    "See where it takes you.",
    "Surprise yourself.",
)


class Difficulty(enum.Enum):
    """Constraint difficulty level."""

    GENTLE = "gentle"
    MEDIUM = "medium"
    STRANGE = "strange"


class Category(enum.Enum):
    """Constraint category."""

    CODE = "code"
    CREATIVE = "creative"
    EXPERIMENT = "experiment"
    PHILOSOPHICAL = "philosophical"
    WILD = "wild"


class Constraint(NamedTuple):
    """Immutable constraint record."""

    text: str
    difficulty: Difficulty


_G = Difficulty.GENTLE
_M = Difficulty.MEDIUM
_S = Difficulty.STRANGE

_ALL_CATEGORIES: tuple[Category, ...] = tuple(Category)


# ---------------------------------------------------------------------------
# Constraint pools
# ---------------------------------------------------------------------------

CODE_CONSTRAINTS: tuple[Constraint, ...] = (
    # Gentle
    Constraint("Write code with exactly three functions.", _G),
    Constraint("Make a program under thirty lines.", _G),
    Constraint("Use only one import statement.", _G),
    Constraint("Every function must return a string.", _G),
    Constraint("Use a class where a function would suffice.", _G),
    Constraint("Write a script that exits before reaching the end.", _G),
    Constraint("Constrain all variable names to four characters.", _G),
    Constraint("Build a tool that produces output without text.", _G),
    Constraint("Create a script that waits before acting.", _G),
    # Medium
    Constraint("Use recursion where a loop would be simpler.", _M),
    Constraint("Solve the problem without any loops.", _M),
    Constraint("Use a data structure you would normally avoid.", _M),
    Constraint("Name every variable after an animal.", _M),
    Constraint("Make the output a visual pattern in the terminal.", _M),
    Constraint("Use a list where a dictionary would be easier.", _M),
    Constraint("Force the program to fail gracefully on purpose.", _M),
    Constraint("Make naming the most important design decision.", _M),
    # Strange
    Constraint("Write a script designed to run exactly once.", _S),
    Constraint("Build something that deletes a file it created.", _S),
    Constraint("Write code where comments carry more meaning than logic.", _S),
    Constraint("Solve the problem without any conditional statements.", _S),
    Constraint("Build a tool that reacts differently on every run.", _S),
    Constraint("Make the output perfectly symmetrical.", _S),
    Constraint("Use randomness as an equal collaborator in the design.", _S),
    Constraint("Write a program whose interface is its source code.", _S),
)

CREATIVE_CONSTRAINTS: tuple[Constraint, ...] = (
    # Gentle
    Constraint("Include one deliberate imperfection in the output.", _G),
    Constraint("Add a decorative flourish that serves no function.", _G),
    Constraint("Use repetition as an intentional design element.", _G),
    Constraint("Make the output feel warm to read.", _G),
    Constraint("Build something that feels soft and unhurried.", _G),
    Constraint("Use rhythm as a structural principle.", _G),
    Constraint("Make the output feel as if it were handwritten.", _G),
    Constraint("Add a subtle visual pattern to the formatting.", _G),
    Constraint("Make something small but unmistakably intentional.", _G),
    # Medium
    Constraint("Write something that ends mid-thought.", _M),
    Constraint("Create output that feels deliberately unfinished.", _M),
    Constraint("Hide a small surprise at the very end.", _M),
    Constraint("Write output that shifts tone halfway through.", _M),
    Constraint("Insert one line that breaks the established pattern.", _M),
    Constraint("Build something that reveals its meaning slowly.", _M),
    Constraint("Include a detail that is beautiful but unnecessary.", _M),
    Constraint("Write something designed to be read twice.", _M),
    # Strange
    Constraint("Include a blank line that carries meaning.", _S),
    Constraint("Design something with humor hidden in the structure.", _S),
    Constraint("Create something that looks fragile but holds together.", _S),
    Constraint("Add a line whose meaning only appears later.", _S),
    Constraint("Create output that implies movement without animation.", _S),
    Constraint("Include one line that feels whispered among shouts.", _S),
    Constraint("Design something deliberately asymmetrical.", _S),
    Constraint("Include a word that no one would expect in context.", _S),
)

EXPERIMENT_CONSTRAINTS: tuple[Constraint, ...] = (
    # Gentle
    Constraint("Build something designed to feel temporary.", _G),
    Constraint("Use randomness but restrict it to a narrow range.", _G),
    Constraint("Write a script that changes exactly one value each run.", _G),
    Constraint("Create something that logs a single line and stops.", _G),
    Constraint("Write a tool that outputs fewer lines than expected.", _G),
    Constraint("Use the current time as the program's only input.", _G),
    Constraint("Alter the formatting intentionally with each execution.", _G),
    Constraint("Build something that creates a placeholder for later.", _G),
    Constraint("Write a tool that looks and behaves like a prototype.", _G),
    # Medium
    Constraint("Build something that stops itself before finishing.", _M),
    Constraint("Write code that transforms its own input before use.", _M),
    Constraint("Create a program that rejects input it deems unworthy.", _M),
    Constraint("Build something intentionally slower than necessary.", _M),
    Constraint("Make a program that prints its output in reverse order.", _M),
    Constraint("Write a script that pauses mid-execution for no reason.", _M),
    Constraint("Create something that feels interactive without input.", _M),
    Constraint("Build something that behaves differently each minute.", _M),
    # Strange
    Constraint("Make output that overwrites itself after appearing.", _S),
    Constraint("Write a tool that contradicts its own output once.", _S),
    Constraint("Create output that evolves across repeated executions.", _S),
    Constraint("Build something that measures its own execution speed.", _S),
    Constraint("Write output that shrinks in length with each run.", _S),
    Constraint("Create a script that removes part of what it produces.", _S),
    Constraint("Build something that actively resists completion.", _S),
    Constraint("Create output that references its own structure.", _S),
)

PHILOSOPHICAL_CONSTRAINTS: tuple[Constraint, ...] = (
    # Gentle
    Constraint("Build something where process matters more than result.", _G),
    Constraint("Make something that feels calm to use.", _G),
    Constraint("Write output that quietly acknowledges effort.", _G),
    Constraint("Create output that suggests possibility without directing.", _G),
    Constraint("Write a program that celebrates a small win.", _G),
    Constraint("Build something that values simplicity above all.", _G),
    Constraint("Write a tool that suggests starting small.", _G),
    Constraint("Make something that feels gentle to encounter.", _G),
    Constraint("Create output that leaves room for interpretation.", _G),
    # Medium
    Constraint("Write code that forgives user mistakes gracefully.", _M),
    Constraint("Create a tool that rewards patience.", _M),
    Constraint("Build something that intentionally slows the user down.", _M),
    Constraint("Create code that invites curiosity instead of answering.", _M),
    Constraint("Build something that feels reflective, not productive.", _M),
    Constraint("Write something that deliberately solves no problem.", _M),
    Constraint("Make a tool that openly acknowledges uncertainty.", _M),
    Constraint("Write code that expresses care in its error messages.", _M),
    # Strange
    Constraint("Create output that feels like a question with no answer.", _S),
    Constraint("Build output that encourages the user to rest.", _S),
    Constraint("Build something that reminds the user they tried.", _S),
    Constraint("Write something that holds space for doubt.", _S),
    Constraint("Value the attempt over the outcome.", _S),
    Constraint("Create output that asks nothing of the user.", _S),
    Constraint("Make something that resists being useful on purpose.", _S),
    Constraint("Build something that exists only to exist.", _S),
)

WILD_CONSTRAINTS: tuple[Constraint, ...] = (
    # Gentle
    Constraint("Build something that feels like a toy.", _G),
    Constraint("Write output that behaves like a whisper.", _G),
    Constraint("Create a script that invites the user to break it.", _G),
    Constraint("Make a program that suggests more than it shows.", _G),
    Constraint("Build something that almost works but not quite.", _G),
    Constraint("Create a tool that gives guidance but leaves gaps.", _G),
    Constraint("Write output that reads like a found fragment.", _G),
    Constraint("Make a script that invents and enforces a temporary rule.", _G),
    Constraint("Build something that hints at a system behind it.", _G),
    # Medium
    Constraint("Build something that prints its own instructions.", _M),
    Constraint("Make a tool that contradicts its stated purpose.", _M),
    Constraint("Write code that feels like a puzzle to read.", _M),
    Constraint("Create output that could be mistaken for art.", _M),
    Constraint("Make a program that invents and defines a new word.", _M),
    Constraint("Write code that ends in silence with no final output.", _M),
    Constraint("Create output that resembles a signal from nowhere.", _M),
    Constraint("Build something that appears to be alive.", _M),
    # Strange
    Constraint("Write a program that makes no sense but feels right.", _S),
    Constraint("Build something that feels like a half-remembered dream.", _S),
    Constraint("Write code that feels imported from another universe.", _S),
    Constraint("Reference something in the output that does not exist.", _S),
    Constraint("Create a program that communicates only in fragments.", _S),
    Constraint("Build something that feels found rather than made.", _S),
    Constraint("Make something that operates on its own private logic.", _S),
    Constraint("Create output that slowly dissolves into nothing.", _S),
)


# ---------------------------------------------------------------------------
# Pool registry and validation
# ---------------------------------------------------------------------------

CONSTRAINT_POOLS: dict[Category, tuple[Constraint, ...]] = {
    Category.CODE: CODE_CONSTRAINTS,
    Category.CREATIVE: CREATIVE_CONSTRAINTS,
    Category.EXPERIMENT: EXPERIMENT_CONSTRAINTS,
    Category.PHILOSOPHICAL: PHILOSOPHICAL_CONSTRAINTS,
    Category.WILD: WILD_CONSTRAINTS,
}

VALID_CATEGORIES: dict[str, Category] = {c.value: c for c in Category}
VALID_DIFFICULTIES: dict[str, Difficulty] = {d.value: d for d in Difficulty}


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def select_constraint(
    *,
    category: Category | None,
    difficulty: Difficulty | None,
    rng: random.Random,
) -> Constraint:
    """Select a single constraint matching the given filters."""
    chosen_category: Category = (
        category if category is not None else rng.choice(_ALL_CATEGORIES)
    )
    pool: tuple[Constraint, ...] = CONSTRAINT_POOLS[chosen_category]
    if difficulty is not None:
        pool = tuple(c for c in pool if c.difficulty == difficulty)
    return rng.choice(pool)


def format_output(constraint: Constraint, rng: random.Random) -> str:
    """Format a constraint for terminal display."""
    encouragement = rng.choice(ENCOURAGEMENTS)
    return f"{HEADER}\n\n{PROMPT_LINE}\n\n{constraint.text}\n\n{encouragement}\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate a creative constraint to spark experimentation.",
    )
    parser.add_argument(
        "--category",
        default=None,
        help=("Filter by category: code, creative, experiment, philosophical, wild"),
    )
    parser.add_argument(
        "--difficulty",
        default=None,
        help="Filter by difficulty: gentle, medium, strange",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for reproducible constraint selection",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the constraint toybox CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    raw_category: str | None = args.category
    if raw_category is not None and raw_category not in VALID_CATEGORIES:
        sys.stderr.write(
            "Error: Unknown category.\n"
            "Valid options: code, creative, experiment,"
            " philosophical, wild\n"
        )
        return EXIT_FAILURE

    raw_difficulty: str | None = args.difficulty
    if raw_difficulty is not None and raw_difficulty not in VALID_DIFFICULTIES:
        sys.stderr.write("Error: Difficulty must be gentle, medium, or strange\n")
        return EXIT_FAILURE

    category: Category | None = (
        VALID_CATEGORIES[raw_category] if raw_category is not None else None
    )
    difficulty: Difficulty | None = (
        VALID_DIFFICULTIES[raw_difficulty] if raw_difficulty is not None else None
    )

    seed: int | None = args.seed
    rng = random.Random(seed)  # noqa: S311

    constraint = select_constraint(
        category=category,
        difficulty=difficulty,
        rng=rng,
    )
    sys.stdout.write(format_output(constraint, rng))

    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
