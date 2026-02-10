"""Pocket Poet: a tiny CLI that prints a short, calm poem.

A single-file Python CLI tool that generates gentle, grounding poems
using curated word banks and simple line templates. Designed for quiet
moments and small comforts.

Typical usage:

    python pocket_poet.py
    python pocket_poet.py --seed 42
    python pocket_poet.py --lines 6
"""

from __future__ import annotations

import argparse
import random
import re
from collections.abc import Sequence

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MIN_LINES: int = 5
_MAX_LINES: int = 6
_DEFAULT_LINES: int = 5

# ---------------------------------------------------------------------------
# Curated word banks
# ---------------------------------------------------------------------------
# Each bank is a tuple of words chosen for warmth, simplicity, and grounding
# quality.  Words are intentionally plain — no abstractions, no cleverness,
# just the texture of a quiet day.

_NOUNS: tuple[str, ...] = (
    "light",
    "morning",
    "rain",
    "river",
    "stone",
    "leaf",
    "sky",
    "field",
    "garden",
    "window",
    "door",
    "path",
    "bread",
    "breath",
    "stillness",
    "silence",
    "tea",
    "sparrow",
    "cloud",
    "shore",
    "blanket",
    "creek",
    "porch",
    "candle",
    "hearth",
    "wool",
    "hill",
)

_ADJECTIVES: tuple[str, ...] = (
    "quiet",
    "soft",
    "small",
    "warm",
    "gentle",
    "still",
    "calm",
    "slow",
    "kind",
    "simple",
    "tender",
    "pale",
    "faint",
    "cool",
    "low",
    "thin",
    "deep",
    "steady",
    "hushed",
)

_VERBS: tuple[str, ...] = (
    "rests",
    "waits",
    "holds",
    "opens",
    "settles",
    "arrives",
    "stays",
    "lingers",
    "gathers",
    "drifts",
    "lands",
    "turns",
    "folds",
    "hums",
    "glows",
    "breathes",
    "listens",
)

_INFINITIVES: tuple[str, ...] = (
    "rest",
    "wait",
    "hold",
    "open",
    "settle",
    "arrive",
    "stay",
    "linger",
    "gather",
    "drift",
    "land",
    "turn",
    "fold",
    "hum",
    "glow",
    "breathe",
    "listen",
)

_PLACES: tuple[str, ...] = (
    "the window",
    "the door",
    "the garden",
    "the table",
    "the path",
    "the hill",
    "the shore",
    "the porch",
    "the field",
    "the hearth",
)

# ---------------------------------------------------------------------------
# Line templates
# ---------------------------------------------------------------------------
# Each template is a single line of poetry with placeholder tokens drawn
# from the word banks above.  Placeholders: {adj}, {adj2}, {noun}, {noun2},
# {verb}, {inf}, {place}.  All templates produce 3–8 words after rendering.

_LINE_TEMPLATES: tuple[str, ...] = (
    "the {adj} {noun} {verb}",
    "a {adj} {noun} {verb} near {place}",
    "{noun} {verb} on the {noun2}",
    "you breathe and the {noun} {verb}",
    "there is {noun} in the {adj} {noun2}",
    "let the {noun} {inf}",
    "the {noun} knows how to {inf}",
    "something {adj} {verb} here",
    "a little {noun} near {place}",
    "the {adj} air {verb}",
    "nothing to do but {inf}",
    "the {noun} is enough",
    "all the {adj} things {inf}",
    "you are {adj} like the {noun}",
    "even the {noun} {verb}",
    "here is a {adj} place to {inf}",
    "{adj} {noun} and {adj2} {noun2}",
    "the world {verb} around you",
    "somewhere a {noun} {verb}",
    "be {adj} with the {noun}",
)

# ---------------------------------------------------------------------------
# Template engine
# ---------------------------------------------------------------------------
# Maps each placeholder name to its source word bank.  A compiled regex
# matches any {token} in a template and a callback resolves it against the
# corresponding bank, so each placeholder is replaced independently.

_BANK_MAP: dict[str, tuple[str, ...]] = {
    "adj": _ADJECTIVES,
    "adj2": _ADJECTIVES,
    "noun": _NOUNS,
    "noun2": _NOUNS,
    "verb": _VERBS,
    "inf": _INFINITIVES,
    "place": _PLACES,
}

_PLACEHOLDER_RE: re.Pattern[str] = re.compile(r"\{(\w+)\}")


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------


def _pick(rng: random.Random, bank: tuple[str, ...]) -> str:
    """Selects a single entry from a word bank.

    Args:
        rng: A seeded Random instance for reproducibility.
        bank: A tuple of candidate words or phrases.

    Returns:
        A randomly chosen entry from the bank.
    """
    return rng.choice(bank)


def _render_line(rng: random.Random, template: str) -> str:
    """Fills a line template with words drawn from curated banks.

    Each placeholder is resolved independently via regex substitution,
    so a template containing both {noun} and {noun2} may receive two
    different nouns.

    Args:
        rng: A seeded Random instance for reproducibility.
        template: A template string containing {placeholder} tokens.

    Returns:
        A fully rendered line of poetry.
    """

    def _substitute(match: re.Match[str]) -> str:
        return _pick(rng, _BANK_MAP[match.group(1)])

    return _PLACEHOLDER_RE.sub(_substitute, template)


def _generate_poem(rng: random.Random, line_count: int) -> list[str]:
    """Generates a poem by selecting and rendering line templates.

    Templates are sampled without replacement to avoid structural
    repetition within a single poem.

    Args:
        rng: A seeded Random instance for reproducibility.
        line_count: Number of lines to produce (5 or 6).

    Returns:
        A list of rendered poem lines.
    """
    templates = rng.sample(_LINE_TEMPLATES, k=line_count)
    return [_render_line(rng, t) for t in templates]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Constructs the argument parser for Pocket Poet.

    Returns:
        A configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="pocket_poet",
        description="Print a short, calm poem.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="integer seed for reproducible output",
    )
    parser.add_argument(
        "--lines",
        type=int,
        default=_DEFAULT_LINES,
        choices=range(_MIN_LINES, _MAX_LINES + 1),
        metavar=f"{{{_MIN_LINES},{_MAX_LINES}}}",
        help=(
            f"number of lines in the poem"
            f" (default: {_DEFAULT_LINES}, max: {_MAX_LINES})"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point for Pocket Poet.

    Parses CLI arguments, initializes a random number generator,
    generates a short poem, and prints it to stdout.

    Args:
        argv: Command-line arguments.  Uses sys.argv[1:] when None.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    poem = _generate_poem(rng, args.lines)

    for line in poem:
        print(line)


if __name__ == "__main__":
    main()
