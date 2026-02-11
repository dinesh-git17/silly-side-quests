"""A quiet morning ritual for the terminal.

Nothing is saved. Nothing accumulates. Every run is the first run.
"""

import random
import sys
import time

# Delay between each character in the typewriter effect, in seconds.
TYPING_DELAY: float = 0.03

# Pause after a full line is revealed, in seconds.
LINE_PAUSE: float = 0.8

# Breathing room before and after the prompt, in seconds.
PROMPT_PAUSE: float = 1.0

# Greetings, chosen at random each run.
GREETINGS: tuple[str, ...] = (
    "\u2600\ufe0e  Good morning.",
    "\U0001f375  A quiet moment, before the day begins.",
    "\U0001f33f  You are here.",
)

# Closings, chosen at random each run.
CLOSINGS: tuple[str, ...] = (
    "Thank you. That is enough.",
    "The morning is yours. Begin.",
    "Nothing held. Nothing kept. Go gently.",
)


def slow_print(text: str) -> None:
    """Print text one character at a time, like a gentle typewriter.

    Each character is flushed immediately to create a smooth
    reveal effect. A brief pause follows the completed line.

    Args:
        text: The message to display.
    """
    for character in text:
        sys.stdout.write(character)
        sys.stdout.flush()
        time.sleep(TYPING_DELAY)
    sys.stdout.write("\n")
    sys.stdout.flush()
    time.sleep(LINE_PAUSE)


def print_greeting() -> None:
    """Display a soft, randomized greeting.

    Prints blank lines for spacing, then reveals a greeting
    chosen at random from the available options.
    """
    print()
    greeting = random.choice(GREETINGS)
    slow_print(greeting)
    print()


def prompt_user() -> str:
    """Invite the user to share one sentence.

    Waits quietly for a single line of input. The sentence
    is received but never stored beyond this moment.

    Returns:
        The sentence the user entered.
    """
    time.sleep(PROMPT_PAUSE)
    slow_print("What is on your mind this morning?")
    print()
    sentence = input("  \u2192 ")
    print()
    time.sleep(PROMPT_PAUSE)
    return sentence


def print_closing() -> None:
    """Display a gentle closing message.

    Chooses a closing at random and reveals it slowly,
    leaving space around it so the words can breathe.
    """
    closing = random.choice(CLOSINGS)
    slow_print(closing)
    print()


def main() -> None:
    """Run the morning ritual.

    The flow is simple and unchanging: greet, listen, close.
    Nothing from the session is saved or remembered.
    """
    try:
        print_greeting()
        prompt_user()
        print_closing()
    except (KeyboardInterrupt, EOFError):
        # If the user leaves early, exit quietly.
        print()


if __name__ == "__main__":
    main()
