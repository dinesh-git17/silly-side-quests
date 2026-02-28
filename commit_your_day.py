#!/usr/bin/env python3
"""Git-style journaling CLI that turns daily reflections into structured life commits."""

from __future__ import annotations

import argparse
import calendar
import contextlib
import json
import logging
import os
import random
import shutil
import sys
import tempfile
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TypedDict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STORAGE_DIR: Path = Path.home() / ".commit_your_day"
STORAGE_FILE: Path = STORAGE_DIR / "life_commits.json"
SCHEMA_VERSION: str = "1.0"
JSON_INDENT: int = 2
DATA_ENCODING: str = "utf-8"
BACKUP_SUFFIX: str = ".bak"
MAX_BACKUPS: int = 3

MOOD_MIN: int = -2
MOOD_MAX: int = 2
MOOD_DEFAULT: int = 0
ENERGY_MIN: int = 1
ENERGY_MAX: int = 5
ENERGY_DEFAULT: int = 3

LOG_DEFAULT_COUNT: int = 10
REFLECTION_CHANCE: float = 0.3
COMMIT_INDENT: str = "    "
SHORT_ID_LENGTH: int = 7
TOP_THEMES_COUNT: int = 5
WEEK_DAYS: int = 7
STREAK_MIN_DISPLAY: int = 2

HEATMAP_WEEKS: int = 15
HEATMAP_INTENSITY_LEVELS: int = 4
HEATMAP_DAY_LABELS: tuple[str, ...] = ("Mon", "", "Wed", "", "Fri", "", "Sun")
HEATMAP_CHARS_COLOR: tuple[str, ...] = ("\u2591", "\u2592", "\u2593", "\u2588")
HEATMAP_CHARS_PLAIN: tuple[str, ...] = (".", "o", "O", "#")
HEATMAP_LABEL_WIDTH: int = 4
TAG_MOOD_MIN_OCCURRENCES: int = 2

VALID_COMMIT_TYPES: tuple[str, ...] = (
    "feat",
    "fix",
    "refactor",
    "chore",
    "docs",
    "style",
    "test",
)

TYPE_KEYWORDS: dict[str, str] = {
    "fixed": "fix",
    "repaired": "fix",
    "resolved": "fix",
    "debugged": "fix",
    "patched": "fix",
    "learned": "docs",
    "studied": "docs",
    "researched": "docs",
    "documented": "docs",
    "noted": "docs",
    "tried": "feat",
    "built": "feat",
    "created": "feat",
    "shipped": "feat",
    "launched": "feat",
    "finished": "feat",
    "completed": "feat",
    "started": "feat",
    "made": "feat",
    "added": "feat",
    "improved": "refactor",
    "optimized": "refactor",
    "refactored": "refactor",
    "restructured": "refactor",
    "simplified": "refactor",
    "cleaned": "chore",
    "organized": "chore",
    "maintained": "chore",
    "updated": "chore",
    "styled": "style",
    "designed": "style",
    "formatted": "style",
    "tested": "test",
    "verified": "test",
    "validated": "test",
}

REFLECTION_LINES: tuple[str, ...] = (
    "Small commits still move the project forward.",
    "Consistency compounds.",
    "You showed up today. That matters.",
    "Progress isn't always visible, but it's real.",
    "Every commit is a choice to keep going.",
    "The changelog of your life is being written.",
    "Ship it. Reflect. Repeat.",
)

# ---------------------------------------------------------------------------
# ANSI formatting
# ---------------------------------------------------------------------------

_SUPPORTS_COLOR: bool = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

_ANSI_BOLD: str = "\033[1m"
_ANSI_DIM: str = "\033[2m"
_ANSI_GREEN: str = "\033[32m"
_ANSI_YELLOW: str = "\033[33m"
_ANSI_RESET: str = "\033[0m"


def _bold(text: str) -> str:
    if not _SUPPORTS_COLOR:
        return text
    return f"{_ANSI_BOLD}{text}{_ANSI_RESET}"


def _dim(text: str) -> str:
    if not _SUPPORTS_COLOR:
        return text
    return f"{_ANSI_DIM}{text}{_ANSI_RESET}"


def _green(text: str) -> str:
    if not _SUPPORTS_COLOR:
        return text
    return f"{_ANSI_GREEN}{text}{_ANSI_RESET}"


def _yellow(text: str) -> str:
    if not _SUPPORTS_COLOR:
        return text
    return f"{_ANSI_YELLOW}{text}{_ANSI_RESET}"


# ---------------------------------------------------------------------------
# Output helpers (T20-compliant: no print())
# ---------------------------------------------------------------------------


def _out(text: str = "") -> None:
    sys.stdout.write(text + "\n")


def _err(text: str) -> None:
    sys.stderr.write(text + "\n")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger: logging.Logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LifeCommit:
    """A single structured life commit entry."""

    commit_id: str
    timestamp: str
    commit_date: str
    commit_type: str
    message: str
    scope: str = "life"
    details: str = ""
    tags: tuple[str, ...] = ()
    mood_score: int = MOOD_DEFAULT
    energy_score: int = ENERGY_DEFAULT

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-compatible dictionary."""
        return {
            "id": self.commit_id,
            "timestamp": self.timestamp,
            "date": self.commit_date,
            "type": self.commit_type,
            "scope": self.scope,
            "message": self.message,
            "details": self.details,
            "tags": list(self.tags),
            "mood_score": self.mood_score,
            "energy_score": self.energy_score,
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> LifeCommit:
        """Deserialize from a JSON-parsed dictionary."""
        tags_raw = data.get("tags", [])
        tags: tuple[str, ...] = ()
        if isinstance(tags_raw, list):
            tags = tuple(str(t) for t in tags_raw)

        mood_raw = data.get("mood_score", MOOD_DEFAULT)
        mood = int(mood_raw) if isinstance(mood_raw, (int, float)) else MOOD_DEFAULT

        energy_raw = data.get("energy_score", ENERGY_DEFAULT)
        energy = (
            int(energy_raw) if isinstance(energy_raw, (int, float)) else ENERGY_DEFAULT
        )

        return LifeCommit(
            commit_id=str(data.get("id", "")),
            timestamp=str(data.get("timestamp", "")),
            commit_date=str(data.get("date", "")),
            commit_type=str(data.get("type", "feat")),
            scope=str(data.get("scope", "life")),
            message=str(data.get("message", "")),
            details=str(data.get("details", "")),
            tags=tags,
            mood_score=mood,
            energy_score=energy,
        )

    def short_id(self) -> str:
        """Return first 7 characters of the commit ID."""
        return self.commit_id[:SHORT_ID_LENGTH]

    def format_type_scope(self) -> str:
        """Format as 'type(scope)' string."""
        if self.scope:
            return f"{self.commit_type}({self.scope})"
        return self.commit_type

    def format_mood(self) -> str:
        """Format mood score with explicit sign."""
        if self.mood_score > 0:
            return f"+{self.mood_score}"
        return str(self.mood_score)


@dataclass
class CommitStore:
    """Container for the full commit history."""

    version: str = SCHEMA_VERSION
    created_at: str = ""
    commits: list[LifeCommit] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-compatible dictionary."""
        return {
            "version": self.version,
            "created_at": self.created_at,
            "commits": [c.to_dict() for c in self.commits],
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> CommitStore:
        """Deserialize from a JSON-parsed dictionary."""
        commits_raw = data.get("commits", [])
        commits: list[LifeCommit] = (
            [
                LifeCommit.from_dict(entry)
                for entry in commits_raw
                if isinstance(entry, dict)
            ]
            if isinstance(commits_raw, list)
            else []
        )
        return CommitStore(
            version=str(data.get("version", SCHEMA_VERSION)),
            created_at=str(data.get("created_at", "")),
            commits=commits,
        )


def _new_store() -> CommitStore:
    return CommitStore(
        version=SCHEMA_VERSION,
        created_at=datetime.now(tz=timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Persistence layer
# ---------------------------------------------------------------------------


def _backup_path(path: Path, generation: int) -> Path:
    return path.parent / f"{path.name}{BACKUP_SUFFIX}{generation}"


def _ensure_storage_dir() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _write_atomic_json(path: Path, data: dict[str, object]) -> None:
    """Write JSON data atomically using tempfile + fsync + replace."""
    serialized = json.dumps(data, indent=JSON_INDENT, ensure_ascii=False)
    fd, tmp_path_str = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding=DATA_ENCODING) as f:
            f.write(serialized)
            f.flush()
            os.fsync(f.fileno())
        tmp_path.replace(path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
        raise


def _rotate_backups(path: Path) -> None:
    for gen in range(MAX_BACKUPS - 1, 0, -1):
        src = _backup_path(path, gen)
        dst = _backup_path(path, gen + 1)
        if src.exists():
            shutil.move(str(src), dst)
    if path.exists():
        shutil.copy2(path, _backup_path(path, 1))


def _save_store(path: Path, store: CommitStore) -> None:
    """Persist the commit store with backup rotation and atomic write."""
    _ensure_storage_dir()
    _rotate_backups(path)
    _write_atomic_json(path, store.to_dict())


def _load_store(path: Path) -> CommitStore:
    """Load the commit store, falling back through backups on corruption."""
    candidates = [path, *[_backup_path(path, g) for g in range(1, MAX_BACKUPS + 1)]]

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            raw = candidate.read_text(encoding=DATA_ENCODING)
            data = json.loads(raw)
            if not isinstance(data, dict):
                logger.warning("Invalid root type in %s", candidate)
                continue
            store = CommitStore.from_dict(data)
            if candidate != path:
                logger.warning("Recovered from backup: %s", candidate)
                _write_atomic_json(path, store.to_dict())
            return store
        except (json.JSONDecodeError, OSError, KeyError, TypeError):
            logger.warning("Corrupt or unreadable: %s", candidate)
            if candidate == path:
                corrupted = path.parent / f"{path.name}.corrupted"
                with contextlib.suppress(OSError):
                    shutil.copy2(candidate, corrupted)

    return _new_store()


# ---------------------------------------------------------------------------
# Commit type detection
# ---------------------------------------------------------------------------


def _detect_commit_type(message: str) -> str:
    """Infer commit type from keywords in the message."""
    words = message.lower().split()
    for word in words:
        cleaned = word.strip(".,!?;:")
        if cleaned in TYPE_KEYWORDS:
            return TYPE_KEYWORDS[cleaned]
    return "feat"


# ---------------------------------------------------------------------------
# Date and time helpers
# ---------------------------------------------------------------------------


def _today() -> str:
    return date.today().isoformat()


def _now_utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _format_display_date(date_str: str) -> str:
    if date_str == _today():
        return "Today"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%b %d")
    except ValueError:
        return date_str


def _format_long_date(date_str: str) -> str:
    if date_str == _today():
        return "Today"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return date_str


def _relative_time(date_str: str) -> str:
    """Compute human-readable relative time from a date string."""
    try:
        commit_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return date_str

    days = (datetime.now(tz=timezone.utc) - commit_dt).days

    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < WEEK_DAYS:
        return f"{days} days ago"
    weeks = days // WEEK_DAYS
    if days < 30:
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    months = days // 30
    if days < 365:
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"


# ---------------------------------------------------------------------------
# Streak computation
# ---------------------------------------------------------------------------


def _compute_streak(commits: list[LifeCommit]) -> int:
    """Compute the current consecutive-day commit streak."""
    if not commits:
        return 0

    unique_dates = sorted({c.commit_date for c in commits}, reverse=True)
    today_str = _today()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    if unique_dates[0] not in (today_str, yesterday_str):
        return 0

    streak = 1
    for i in range(1, len(unique_dates)):
        try:
            prev = datetime.strptime(unique_dates[i - 1], "%Y-%m-%d").date()
            curr = datetime.strptime(unique_dates[i], "%Y-%m-%d").date()
        except ValueError:
            break
        if (prev - curr).days == 1:
            streak += 1
        else:
            break

    return streak


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------


def _display_summary(commits: list[LifeCommit], period_label: str) -> None:
    """Compute and display a summary of commits for a given period."""
    if not commits:
        _out(f"\n  No commits in the {period_label} period.\n")
        return

    total = len(commits)
    all_tags: list[str] = []
    mood_sum = 0
    energy_sum = 0
    for commit in commits:
        all_tags.extend(commit.tags)
        mood_sum += commit.mood_score
        energy_sum += commit.energy_score

    tag_counts = Counter(all_tags)
    top_themes = (
        [tag for tag, _ in tag_counts.most_common(TOP_THEMES_COUNT)]
        if tag_counts
        else []
    )
    mood_avg = mood_sum / total
    energy_avg = energy_sum / total

    _out()
    _out(f"  {_bold(f'{period_label.title()} Life Summary')}")
    _out()
    _out(f"  Commits:        {total}")
    if top_themes:
        _out(f"  Top themes:     {', '.join(top_themes)}")
    _out(f"  Mood average:   {mood_avg:+.1f}")
    _out(f"  Energy average: {energy_avg:.1f}")
    _out()
    if random.random() < REFLECTION_CHANCE:  # noqa: S311
        _out(f"  {_dim(random.choice(REFLECTION_LINES))}")  # noqa: S311
        _out()


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------


class _WeekStats(TypedDict):
    count: int
    mood_avg: float
    energy_avg: float


def _commits_by_date(commits: list[LifeCommit]) -> dict[str, list[LifeCommit]]:
    """Group commits by their ISO date string."""
    by_date: dict[str, list[LifeCommit]] = {}
    for commit in commits:
        by_date.setdefault(commit.commit_date, []).append(commit)
    return by_date


def _compute_tag_counts(commits: list[LifeCommit]) -> Counter[str]:
    """Aggregate tag usage counts across all commits."""
    all_tags: list[str] = []
    for commit in commits:
        all_tags.extend(commit.tags)
    return Counter(all_tags)


def _compute_type_distribution(commits: list[LifeCommit]) -> list[tuple[str, int]]:
    """Return commit types sorted by frequency descending."""
    type_counts: Counter[str] = Counter(c.commit_type for c in commits)
    return type_counts.most_common()


def _week_stats(commits: list[LifeCommit]) -> _WeekStats:
    """Compute aggregate stats for a list of commits."""
    if not commits:
        return {"count": 0, "mood_avg": 0.0, "energy_avg": 0.0}
    count = len(commits)
    mood_avg = sum(c.mood_score for c in commits) / count
    energy_avg = sum(c.energy_score for c in commits) / count
    return {"count": count, "mood_avg": mood_avg, "energy_avg": energy_avg}


def _compute_weekly_trend(
    commits: list[LifeCommit],
) -> tuple[_WeekStats, _WeekStats]:
    """Compare this week vs last week on commits, mood, and energy."""
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=WEEK_DAYS)

    this_week_iso = this_monday.isoformat()
    last_week_iso = last_monday.isoformat()
    today_iso = today.isoformat()

    this_week = [c for c in commits if this_week_iso <= c.commit_date <= today_iso]
    last_week = [c for c in commits if last_week_iso <= c.commit_date < this_week_iso]

    return _week_stats(this_week), _week_stats(last_week)


def _compute_tag_mood_correlation(
    commits: list[LifeCommit],
    top_n: int = TOP_THEMES_COUNT,
) -> list[tuple[str, float, int]]:
    """For top tags, compute average mood when that tag is present."""
    tag_counts = _compute_tag_counts(commits)
    top_tags = [tag for tag, _ in tag_counts.most_common(top_n)]

    results: list[tuple[str, float, int]] = []
    for tag in top_tags:
        tagged = [c for c in commits if tag in c.tags]
        count = len(tagged)
        if count < TAG_MOOD_MIN_OCCURRENCES:
            continue
        avg_mood = sum(c.mood_score for c in tagged) / count
        results.append((tag, avg_mood, count))

    return results


# ---------------------------------------------------------------------------
# Activity heatmap
# ---------------------------------------------------------------------------


def _build_heatmap_grid(
    commits: list[LifeCommit],
) -> tuple[list[list[int]], list[str], date]:
    """Build a 7-row x HEATMAP_WEEKS-column grid of daily commit counts.

    Returns (grid, month_labels, start_date).
    """
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    start_monday = current_monday - timedelta(weeks=HEATMAP_WEEKS - 1)

    date_counts: dict[str, int] = {
        k: len(v) for k, v in _commits_by_date(commits).items()
    }

    grid: list[list[int]] = [[0] * HEATMAP_WEEKS for _ in range(WEEK_DAYS)]
    month_labels: list[str] = [""] * HEATMAP_WEEKS

    prev_month: int = -1
    for week_idx in range(HEATMAP_WEEKS):
        week_monday = start_monday + timedelta(weeks=week_idx)

        if week_monday.month != prev_month:
            month_labels[week_idx] = calendar.month_abbr[week_monday.month]
            prev_month = week_monday.month

        for day_offset in range(WEEK_DAYS):
            cell_date = week_monday + timedelta(days=day_offset)
            if cell_date > today:
                grid[day_offset][week_idx] = -1
            else:
                grid[day_offset][week_idx] = date_counts.get(cell_date.isoformat(), 0)

    return grid, month_labels, start_monday


def _intensity_char(count: int, chars: tuple[str, ...]) -> str:
    """Map commit count to a display character with optional color."""
    if count < 0:
        return " "
    idx = min(count, HEATMAP_INTENSITY_LEVELS - 1)
    char = chars[idx]
    if not _SUPPORTS_COLOR or idx == 0:
        return char
    color_fns = (_dim, _yellow, _green)
    return color_fns[idx - 1](char)


def _render_heatmap(
    grid: list[list[int]],
    month_labels: list[str],
) -> list[str]:
    """Render the heatmap grid to a list of output lines."""
    chars = HEATMAP_CHARS_COLOR if _SUPPORTS_COLOR else HEATMAP_CHARS_PLAIN
    lines: list[str] = []

    month_row = " " * HEATMAP_LABEL_WIDTH
    for week_idx in range(len(grid[0])):
        label = month_labels[week_idx]
        if label:
            month_row += label[:3].ljust(2)
        else:
            month_row += "  "
    lines.append(month_row.rstrip())

    for day_idx in range(WEEK_DAYS):
        label = HEATMAP_DAY_LABELS[day_idx].ljust(HEATMAP_LABEL_WIDTH)
        row = label
        for week_idx in range(len(grid[0])):
            row += _intensity_char(grid[day_idx][week_idx], chars) + " "
        lines.append(row.rstrip())

    return lines


def _render_heatmap_legend() -> str:
    """Render the intensity legend line."""
    chars = HEATMAP_CHARS_COLOR if _SUPPORTS_COLOR else HEATMAP_CHARS_PLAIN
    if _SUPPORTS_COLOR:
        parts = [chars[0], _dim(chars[1]), _yellow(chars[2]), _green(chars[3])]
    else:
        parts = list(chars)
    return f"  Less {' '.join(parts)} More"


# ---------------------------------------------------------------------------
# Display formatting
# ---------------------------------------------------------------------------


def _display_commit_compact(commit: LifeCommit) -> None:
    display_date = _format_display_date(commit.commit_date).ljust(8)
    _out(f"  {_dim(display_date)}  {commit.format_type_scope()}: {commit.message}")


def _display_commit_full(commit: LifeCommit) -> None:
    _out(f"  {_yellow('commit')} {_yellow(commit.short_id())}")
    _out("  Author: You")
    _out(f"  Date:   {_format_long_date(commit.commit_date)}")
    _out()
    _out(f"{COMMIT_INDENT}{commit.format_type_scope()}: {commit.message}")
    if commit.details:
        _out()
        _out(f"{COMMIT_INDENT}{commit.details}")
    if commit.tags:
        _out(f"{COMMIT_INDENT}Tags: {', '.join(commit.tags)}")
    _out(f"{COMMIT_INDENT}Mood: {commit.format_mood()}  Energy: {commit.energy_score}")
    _out()
    _out(f"  {_dim('---')}")
    _out()


def _display_commit_recorded(commit: LifeCommit, streak: int) -> None:
    _out()
    _out(f"  {_green('✔')} Commit recorded")
    _out()
    _out(f"  {_yellow('commit')} {_yellow(commit.short_id())}")
    _out("  Author: You")
    _out(f"  Date:   {_format_long_date(commit.commit_date)}")
    _out()
    _out(f"{COMMIT_INDENT}{commit.format_type_scope()}: {commit.message}")
    _out()

    if streak >= STREAK_MIN_DISPLAY:
        _out(f"  \U0001f525 {streak} day commit streak")
        _out()

    if random.random() < REFLECTION_CHANCE:  # noqa: S311
        _out(f"  {_dim(random.choice(REFLECTION_LINES))}")  # noqa: S311
        _out()


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------


def _prompt_input(prompt_text: str, default: str = "") -> str:
    """Prompt for user input with optional default value."""
    try:
        suffix = f" [{default}]" if default else ""
        response = input(f"{prompt_text}{suffix} ")
    except (EOFError, KeyboardInterrupt):
        _out()
        sys.exit(0)
    stripped = response.strip()
    if not stripped and default:
        return default
    return stripped


def _prompt_int(prompt_text: str, default: int, min_val: int, max_val: int) -> int:
    """Prompt for an integer within bounds."""
    raw = _prompt_input(f"  {prompt_text} ({min_val}\u2013{max_val})?", str(default))
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(min_val, min(max_val, value))


# ---------------------------------------------------------------------------
# Commit creation
# ---------------------------------------------------------------------------


def _create_commit(
    message: str,
    *,
    commit_type: str | None = None,
    scope: str = "life",
    details: str = "",
    tags: tuple[str, ...] = (),
    mood: int = MOOD_DEFAULT,
    energy: int = ENERGY_DEFAULT,
) -> LifeCommit:
    """Build a new LifeCommit with generated ID and timestamps."""
    resolved_type = commit_type if commit_type else _detect_commit_type(message)
    return LifeCommit(
        commit_id=str(uuid.uuid4()),
        timestamp=_now_utc_iso(),
        commit_date=_today(),
        commit_type=resolved_type,
        scope=scope,
        message=message,
        details=details,
        tags=tags,
        mood_score=max(MOOD_MIN, min(MOOD_MAX, mood)),
        energy_score=max(ENERGY_MIN, min(ENERGY_MAX, energy)),
    )


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _cmd_log(full_mode: bool) -> None:
    store = _load_store(STORAGE_FILE)
    if not store.commits:
        _out("\n  No commits yet. Start with: commit-your-day\n")
        return

    commits = list(reversed(store.commits))

    if full_mode:
        _out()
        _out(f"  {_bold('Life Commits')}")
        _out()
        for commit in commits:
            _display_commit_full(commit)
    else:
        display_count = min(LOG_DEFAULT_COUNT, len(commits))
        _out()
        _out(f"  {_bold('Recent life commits:')}")
        _out()
        for commit in commits[:display_count]:
            _display_commit_compact(commit)
        remaining = len(commits) - display_count
        if remaining > 0:
            _out()
            _out(f"  {_dim(f'... and {remaining} more (use --log --full)')}")
        _out()


def _cmd_random() -> None:
    store = _load_store(STORAGE_FILE)
    if not store.commits:
        _out("\n  No commits yet. Start with: commit-your-day\n")
        return

    commit = random.choice(store.commits)  # noqa: S311
    time_ago = _relative_time(commit.commit_date)

    _out()
    _out(f"  {_dim(f'From {time_ago}:')}")
    _out()
    _out(f"  {commit.format_type_scope()}: {commit.message}")
    if commit.tags:
        _out(f"  Tags: {', '.join(commit.tags)}")
    _out(f"  Mood: {commit.format_mood()}")
    _out()


def _cmd_summary(period: str) -> None:
    store = _load_store(STORAGE_FILE)
    if period == "week":
        cutoff = (date.today() - timedelta(days=WEEK_DAYS)).isoformat()
        filtered = [c for c in store.commits if c.commit_date >= cutoff]
        _display_summary(filtered, "weekly")


def _cmd_stats() -> None:
    """Display comprehensive stats with activity heatmap."""
    store = _load_store(STORAGE_FILE)
    commits = store.commits

    if not commits:
        _out("\n  No commits yet. Start with: commit-your-day\n")
        return

    total = len(commits)
    streak = _compute_streak(commits)
    mood_avg = sum(c.mood_score for c in commits) / total
    energy_avg = sum(c.energy_score for c in commits) / total

    _out()
    _out(f"  {_bold('Life Stats')}")
    _out()
    _out(f"  Total commits:  {total}")
    _out(f"  Current streak: {streak} day{'s' if streak != 1 else ''}")
    _out(f"  Mood average:   {mood_avg:+.1f}")
    _out(f"  Energy average: {energy_avg:.1f}")
    _out()

    tag_counts = _compute_tag_counts(commits)
    if tag_counts:
        _out(f"  {_bold('Top Tags')}")
        _out()
        for tag, count in tag_counts.most_common(TOP_THEMES_COUNT):
            _out(f"    {tag:<20s} {count}")
        _out()

    type_dist = _compute_type_distribution(commits)
    if type_dist:
        _out(f"  {_bold('Commit Types')}")
        _out()
        for ctype, count in type_dist:
            _out(f"    {ctype:<12s} {count}")
        _out()

    this_week, last_week = _compute_weekly_trend(commits)
    _out(f"  {_bold('Weekly Trend')}")
    _out()
    _out(f"    {'':14s} {'This week':>10s}  {'Last week':>10s}")
    _out(f"    {'Commits':<14s} {this_week['count']:>10}  {last_week['count']:>10}")
    _out(
        f"    {'Mood avg':<14s} {this_week['mood_avg']:>+10.1f}"
        f"  {last_week['mood_avg']:>+10.1f}"
    )
    _out(
        f"    {'Energy avg':<14s} {this_week['energy_avg']:>10.1f}"
        f"  {last_week['energy_avg']:>10.1f}"
    )
    _out()

    correlations = _compute_tag_mood_correlation(commits)
    if correlations:
        _out(f"  {_bold('Tag-Mood Correlation')}")
        _out()
        for tag, avg_mood, count in correlations:
            _out(f"    {tag:<20s} mood {avg_mood:+.1f}  ({count} commits)")
        _out()

    _out(f"  {_bold('Activity')}")
    _out()
    grid, month_labels, _start = _build_heatmap_grid(commits)
    heatmap_lines = _render_heatmap(grid, month_labels)
    for line in heatmap_lines:
        _out(f"  {line}")
    _out()
    _out(_render_heatmap_legend())
    _out()


def _cmd_quick_commit(args: argparse.Namespace) -> None:
    message_raw: str = args.message or ""
    if not message_raw.strip():
        _err("  Error: commit message cannot be empty.")
        sys.exit(1)

    commit_type: str | None = args.commit_type
    scope: str = args.scope or "life"
    details: str = args.details or ""

    tags_raw: str | None = args.tags
    tags: tuple[str, ...] = ()
    if tags_raw:
        tags = tuple(t.strip() for t in tags_raw.split(",") if t.strip())

    mood_val: int | None = args.mood
    mood: int = mood_val if mood_val is not None else MOOD_DEFAULT

    energy_val: int | None = args.energy
    energy: int = energy_val if energy_val is not None else ENERGY_DEFAULT

    if mood < MOOD_MIN or mood > MOOD_MAX:
        msg = f"Mood must be between {MOOD_MIN} and {MOOD_MAX}"
        _err(f"  Error: {msg}")
        sys.exit(1)

    if energy < ENERGY_MIN or energy > ENERGY_MAX:
        msg = f"Energy must be between {ENERGY_MIN} and {ENERGY_MAX}"
        _err(f"  Error: {msg}")
        sys.exit(1)

    commit = _create_commit(
        message_raw.strip(),
        commit_type=commit_type,
        scope=scope,
        details=details,
        tags=tags,
        mood=mood,
        energy=energy,
    )

    store = _load_store(STORAGE_FILE)
    store.commits.append(commit)
    _save_store(STORAGE_FILE, store)

    streak = _compute_streak(store.commits)
    _display_commit_recorded(commit, streak)


def _cmd_interactive() -> None:
    _out()
    raw_message = _prompt_input("  What changed today?\n  >")

    if not raw_message:
        _out("\n  Nothing to commit.\n")
        return

    detected_type = _detect_commit_type(raw_message)
    suggested = f"{detected_type}(life): {raw_message}"

    _out()
    _out("  Suggested commit:")
    _out()
    _out(f"  {_bold(suggested)}")
    _out()

    accept = _prompt_input("  Accept? (Y/n/edit)", "Y")

    if accept.lower() == "n":
        _out("\n  Commit discarded.\n")
        return

    if accept.lower() == "edit":
        raw_message = _prompt_input("  Enter commit message:\n  >")
        if not raw_message:
            _out("\n  Nothing to commit.\n")
            return
        detected_type = _detect_commit_type(raw_message)

    tags_raw = _prompt_input("  Add tags? (comma separated or skip)")
    tags: tuple[str, ...] = ()
    if tags_raw and tags_raw.lower() != "skip":
        tags = tuple(t.strip() for t in tags_raw.split(",") if t.strip())

    energy = _prompt_int("Energy today", ENERGY_DEFAULT, ENERGY_MIN, ENERGY_MAX)
    mood = _prompt_int("Mood today", MOOD_DEFAULT, MOOD_MIN, MOOD_MAX)

    commit = _create_commit(
        raw_message,
        commit_type=detected_type,
        tags=tags,
        mood=mood,
        energy=energy,
    )

    store = _load_store(STORAGE_FILE)
    store.commits.append(commit)
    _save_store(STORAGE_FILE, store)

    streak = _compute_streak(store.commits)
    _display_commit_recorded(commit, streak)


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="commit-your-day",
        description="Git-style journaling CLI for structured life commits.",
    )
    parser.add_argument("-m", "--message", help="quick commit message")
    parser.add_argument(
        "--type",
        dest="commit_type",
        choices=VALID_COMMIT_TYPES,
        help="commit type override",
    )
    parser.add_argument("--scope", default="life", help="commit scope (default: life)")
    parser.add_argument("--tags", help="comma-separated tags")
    parser.add_argument(
        "--mood",
        type=int,
        help=f"mood score ({MOOD_MIN} to {MOOD_MAX})",
    )
    parser.add_argument(
        "--energy",
        type=int,
        help=f"energy score ({ENERGY_MIN} to {ENERGY_MAX})",
    )
    parser.add_argument("--details", help="extended details for the commit")
    parser.add_argument("--log", action="store_true", help="view commit history")
    parser.add_argument(
        "--full",
        action="store_true",
        help="show full commit details (with --log)",
    )
    parser.add_argument(
        "--random",
        action="store_true",
        dest="random_commit",
        help="surface a random past commit",
    )
    parser.add_argument(
        "--summary",
        choices=["week"],
        metavar="PERIOD",
        help="generate summary (week)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="show comprehensive stats with activity heatmap",
    )
    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    parser = _build_parser()
    args = parser.parse_args()
    _ensure_storage_dir()

    if args.log:
        _cmd_log(full_mode=bool(args.full))
    elif args.random_commit:
        _cmd_random()
    elif args.summary:
        _cmd_summary(period=str(args.summary))
    elif args.stats:
        _cmd_stats()
    elif args.message:
        _cmd_quick_commit(args)
    else:
        _cmd_interactive()


if __name__ == "__main__":
    main()
