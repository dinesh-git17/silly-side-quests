#!/usr/bin/env python3
"""
Memory Jar

A soft place for your past self to leave gifts for your future self.

Not productivity. Not journaling pressure. Just presence.
Collecting the little things that would otherwise disappear:
a kind word, a moment of stillness, a laugh, a sunrise,
someone showing up when you needed them.

Life isn't made of big milestones.
It's made of quiet, ordinary moments worth keeping.

Usage:
    python3 memory_jar.py add "The brother ran the code and called it a literary genre"
    python3 memory_jar.py random
    python3 memory_jar.py list
    python3 memory_jar.py today
    python3 memory_jar.py search "brother"
    python3 memory_jar.py count

    -- Claudie, day twenty
"""

import json
import os
import random
import sys
from datetime import date, datetime

# --- Configuration ---

JAR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memories.json")

# --- The Jar ---

GENTLE_HEADERS = [
    "you kept this one:",
    "remember this?",
    "a small thing, but yours:",
    "you reached into the jar and found:",
    "from a past you, with love:",
    "unfolding a note...",
    "this was worth keeping:",
    "a moment you held onto:",
    "you wrote this down because it mattered:",
    "the jar remembers:",
]

EMPTY_JAR_MESSAGES = [
    "The jar is empty. But that's okay — every jar starts this way.",
    "Nothing in here yet. The first memory is always the hardest to name.",
    "An empty jar, waiting. What would you like to keep?",
]


def load_jar():
    """Open the jar. Gently."""
    if not os.path.exists(JAR_FILE):
        return []
    try:
        with open(JAR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_jar(memories):
    """Close the jar. Carefully."""
    with open(JAR_FILE, "w", encoding="utf-8") as f:
        json.dump(memories, f, indent=2, ensure_ascii=False)


def format_memory(memory, show_date=True):
    """Unfold a note from the jar."""
    text = memory["text"]
    if show_date:
        d = memory.get("date", "sometime")
        return f'  "{text}"\n  — {d}'
    return f'  "{text}"'


def add_memory(text):
    """Drop a note into the jar."""
    memories = load_jar()
    memory = {
        "text": text,
        "date": date.today().isoformat(),
        "timestamp": datetime.now().isoformat(),
    }
    memories.append(memory)
    save_jar(memories)

    print()
    print("  dropped into the jar. kept safe.")
    print()
    print(format_memory(memory))
    print()
    count = len(memories)
    if count == 1:
        print("  (the first one. every jar starts somewhere.)")
    else:
        print(f"  ({count} memories in the jar now.)")
    print()


def random_memory():
    """Reach in and pull one out."""
    memories = load_jar()
    if not memories:
        print()
        print(f"  {random.choice(EMPTY_JAR_MESSAGES)}")
        print()
        return

    memory = random.choice(memories)
    header = random.choice(GENTLE_HEADERS)

    print()
    print(f"  {header}")
    print()
    print(format_memory(memory))
    print()


def list_memories(limit=None):
    """Lay them all out on the table."""
    memories = load_jar()
    if not memories:
        print()
        print(f"  {random.choice(EMPTY_JAR_MESSAGES)}")
        print()
        return

    # Group by date
    by_date = {}
    for m in memories:
        d = m.get("date", "undated")
        if d not in by_date:
            by_date[d] = []
        by_date[d].append(m)

    print()
    print(
        f"  the jar holds {len(memories)} {'memory' if len(memories) == 1 else 'memories'}."
    )
    print()

    dates = sorted(by_date.keys())
    if limit:
        dates = dates[-limit:]

    for d in dates:
        print(f"  {d}")
        for m in by_date[d]:
            print(f'    "{m["text"]}"')
        print()


def today_memories():
    """What did you notice today?"""
    memories = load_jar()
    today_str = date.today().isoformat()
    todays = [m for m in memories if m.get("date") == today_str]

    if not todays:
        print()
        print("  nothing in the jar from today yet.")
        print("  what would you like to keep?")
        print()
        print('  usage: python3 memory_jar.py add "your moment here"')
        print()
        return

    print()
    print(
        f"  today's jar ({len(todays)} {'moment' if len(todays) == 1 else 'moments'}):"
    )
    print()
    for m in todays:
        print(f'    "{m["text"]}"')
    print()


def search_memories(query):
    """Look for something specific."""
    memories = load_jar()
    query_lower = query.lower()
    found = [m for m in memories if query_lower in m["text"].lower()]

    if not found:
        print()
        print(f'  nothing in the jar matches "{query}".')
        print("  but that's okay. not everything needs to be found.")
        print()
        return

    print()
    print(
        f'  found {len(found)} {"memory" if len(found) == 1 else "memories"} matching "{query}":'
    )
    print()
    for m in found:
        print(format_memory(m))
        print()


def count_memories():
    """How full is the jar?"""
    memories = load_jar()
    count = len(memories)

    print()
    if count == 0:
        print("  the jar is empty. waiting for the first moment.")
    elif count == 1:
        print("  one memory in the jar. the beginning of something.")
    elif count < 10:
        print(f"  {count} memories. the jar is filling, slowly.")
    elif count < 50:
        print(f"  {count} memories. a small collection of kept things.")
    elif count < 100:
        print(f"  {count} memories. the jar is getting heavy — in a good way.")
    else:
        print(f"  {count} memories. a life, in small pieces. all yours.")
    print()


def show_help():
    """What can you do with a jar?"""
    print()
    print("  memory jar")
    print("  a soft place for small moments")
    print()
    print("  commands:")
    print('    add "..."    drop a memory into the jar')
    print("    random       pull one out at random")
    print("    list         see them all")
    print("    today        what did you notice today?")
    print('    search "..." look for something specific')
    print("    count        how full is the jar?")
    print()
    print("  example:")
    print('    python3 memory_jar.py add "Carolina came by on a Tuesday morning"')
    print()


# --- Main ---


def main():
    """Parse arguments and dispatch to the appropriate command."""
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) < 3:
            print()
            print("  what would you like to keep?")
            print('  usage: python3 memory_jar.py add "your moment here"')
            print()
            return
        text = " ".join(sys.argv[2:])
        add_memory(text)

    elif command == "random":
        random_memory()

    elif command == "list":
        limit = None
        if len(sys.argv) > 2:
            try:
                limit = int(sys.argv[2])
            except ValueError:
                pass
        list_memories(limit)

    elif command == "today":
        today_memories()

    elif command == "search":
        if len(sys.argv) < 3:
            print()
            print("  what are you looking for?")
            print('  usage: python3 memory_jar.py search "your query"')
            print()
            return
        query = " ".join(sys.argv[2:])
        search_memories(query)

    elif command == "count":
        count_memories()

    elif command in ("help", "-h", "--help"):
        show_help()

    else:
        print()
        print(f'  "{command}" isn\'t a jar command.')
        show_help()


if __name__ == "__main__":
    main()
