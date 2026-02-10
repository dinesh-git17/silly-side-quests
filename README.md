# silly-side-quests

**Where side projects go when they don't need a Jira ticket.**

## Philosophy

Some code doesn't need a product spec. It doesn't need a sprint, a standup, or a stakeholder review. It just needs a terminal and a free afternoon.

This is a collection of small, curiosity-driven experiments — the kind of code you write because the idea got stuck in your head and the only way out was `python main.py`. No pressure, no deadlines, no second drafts.

## What Lives Here

- Tiny CLI tools that solve problems nobody asked about
- Cozy scripts that make your terminal feel a little more alive
- ASCII companions that keep you company while you debug
- Weird experiments that started as "I wonder if..."
- Things that genuinely did not need their own repo

## Example

```bash
python buddy.py --name Mochi --mood happy --duration 30
```

A small ASCII cat named Mochi appears in your terminal. It blinks, wiggles, bounces around, and generally keeps you company for 30 seconds. That's it. That's the whole thing.

```
  /\_/\
 ( o.o )
  > ^ <
```

Press `Ctrl+C` to say goodbye early. It waves.

## Principles

- **Small** — single-file scripts, not frameworks
- **Dependency-light** — stdlib only when possible
- **Joyful** — if it doesn't make you smile, it doesn't ship
- **Offline-first** — works on airplanes and in coffee shops
- **Finished enough** — not everything needs a v2

## Running Things

```bash
python buddy.py                            # defaults are fine
python buddy.py --name Mochi               # name your companion
python buddy.py --mood sleepy              # happy, chill, or sleepy
python buddy.py --duration 60              # stick around a while
python buddy.py --help                     # the usual
```

Requires Python 3.10+. No `pip install` necessary.

## Project Structure

```
silly-side-quests/
├── buddy.py           # ASCII pocket pet for your terminal
├── .gitignore
└── README.md
```

More files will appear here over time. Or they won't. There's no roadmap.

## Repo Vibe

- No roadmap. No backlog. No velocity tracking.
- Probably vibes-driven development.
- Tests are optional. Joy is mandatory.
- The CI pipeline is "does it run on my machine."
- If it brings a small moment of delight, it belongs here.

## Contributing

If you have a tiny, wholesome, single-file Python idea that makes you happy — it probably belongs here. Open a PR. Keep it small. Keep it kind.

The bar for inclusion: would this make someone smile during a code review?

---

_Not every project needs to change the world. Some just need to make your terminal a little more cozy._
