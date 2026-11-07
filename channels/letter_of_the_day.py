"""Letter of the Day channel.

Picks a letter deterministically from today's date (cycling A-Z) and shows
3-4 kid-friendly words that start with it.

Usage:
    python -m channels.letter_of_the_day            # preview only (default)
    python -m channels.letter_of_the_day --dry-run  # preview only, explicit
    python -m channels.letter_of_the_day --post     # actually post to the board
"""

import argparse
import datetime
import sys

from vestaboard import blank_grid, post_characters, print_grid, set_row

WORDS: dict[str, list[str]] = {
    "A": ["APPLE", "ANT", "ARM", "AXE"],
    "B": ["BALL", "BEAR", "BUS", "BEE"],
    "C": ["CAT", "CAKE", "CAR", "COW"],
    "D": ["DOG", "DUCK", "DOOR", "DRUM"],
    "E": ["EGG", "EAR", "ELF", "EEL"],
    "F": ["FISH", "FROG", "FAN", "FOX"],
    "G": ["GOAT", "GAME", "GUM", "GIFT"],
    "H": ["HAT", "HEN", "HAND", "HOME"],
    "I": ["ICE", "INK", "INCH", "IGLOO"],
    "J": ["JAM", "JET", "JUMP", "JAR"],
    "K": ["KITE", "KEY", "KING", "KOALA"],
    "L": ["LION", "LEG", "LAMP", "LEAF"],
    "M": ["MOON", "MAP", "MILK", "MOUSE"],
    "N": ["NEST", "NOSE", "NET", "NAP"],
    "O": ["OWL", "OAK", "OTTER", "OVEN"],
    "P": ["PIG", "PEN", "PARK", "PLUM"],
    "Q": ["QUEEN", "QUILT", "QUIZ"],
    "R": ["RAIN", "RUG", "ROCK", "ROSE"],
    "S": ["SUN", "STAR", "SOCK", "SHIP"],
    "T": ["TREE", "TOY", "TENT", "TIGER"],
    "U": ["UP", "UNDER", "UNCLE"],
    "V": ["VAN", "VEST", "VINE"],
    "W": ["WAVE", "WORM", "WEB", "WING"],
    "X": ["X-RAY", "XYLOPHONE", "BOX"],
    "Y": ["YAK", "YARN", "YO-YO", "YES"],
    "Z": ["ZOO", "ZEBRA", "ZERO", "ZIP"],
}


CYCLE = 26  # days per block; every letter appears once per block


def _mulberry32(seed: int):
    """Tiny seeded PRNG, implemented identically in worker/src/channels/letter.ts."""
    state = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def block_order(block: int) -> list[str]:
    """A shuffled A-Z for the given 26-day block (Fisher-Yates, seeded by block)."""
    rand = _mulberry32(((block * 2654435761) & 0xFFFFFFFF) + 42)
    letters = [chr(ord("A") + i) for i in range(26)]
    for i in range(25, 0, -1):
        j = int(rand() * (i + 1))
        letters[i], letters[j] = letters[j], letters[i]
    return letters


def letter_for(day: datetime.date) -> str:
    """Random-looking but deterministic: each 26-day block is a shuffled A-Z,
    so no letter repeats within a block and the order differs every block."""
    block, index = divmod(day.toordinal(), CYCLE)
    order = block_order(block)
    if index == 0 and block_order(block - 1)[-1] == order[0]:
        order[0], order[1] = order[1], order[0]  # no same letter two days running
    return order[index]


def build_grid(day: datetime.date) -> list[list[int]]:
    letter = letter_for(day)
    words = sorted(WORDS[letter], key=lambda w: (len(w), w))
    grid = blank_grid()
    set_row(grid, 1, "THE LETTER OF THE", align="center")
    set_row(grid, 2, f"DAY IS {{blue}}{letter}{{blue}}", align="center")
    word_row = "{yellow}" + "{yellow}".join(words) + "{yellow}"
    set_row(grid, 4, word_row, align="center")
    return grid


def main() -> int:
    parser = argparse.ArgumentParser(description="Letter of the Day channel")
    parser.add_argument("--post", action="store_true", help="post to the board")
    parser.add_argument("--dry-run", action="store_true", help="preview only (default)")
    parser.add_argument("--date", help="override today's date (YYYY-MM-DD), for testing")
    args = parser.parse_args()

    day = datetime.date.fromisoformat(args.date) if args.date else datetime.date.today()
    grid = build_grid(day)

    print(f"Letter of the day for {day}: {letter_for(day)}")
    print_grid(grid)

    if args.post and not args.dry_run:
        post_characters(grid)
        print("Posted to the board.")
    else:
        print("Dry run - nothing was posted. Use --post to send to the board.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
