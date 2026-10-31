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


def letter_for(day: datetime.date) -> str:
    """Cycle A-Z deterministically by date."""
    return chr(ord("A") + day.toordinal() % 26)


def build_grid(day: datetime.date) -> list[list[int]]:
    letter = letter_for(day)
    words = WORDS[letter][:4]
    grid = blank_grid()
    set_row(grid, 0, f"{{yellow}} {letter} {{yellow}}", align="center")
    for i, word in enumerate(words[:3]):
        set_row(grid, 2 + i, word, align="center")
    if len(words) > 3:
        set_row(grid, 5, f"{{green}} {words[3]} {{green}}", align="center")
    else:
        set_row(grid, 5, "{green}", align="center")
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
