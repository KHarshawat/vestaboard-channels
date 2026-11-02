"""Dinner menu channel.

Shows tonight's planned dinner from menu.json (repo root), a simple map
of ISO dates to meal names:

    { "2026-11-02": "Coconut Lentil Soup" }

Update it anytime by editing the file and pushing (or asking Claude to).
Days with no entry are skipped - nothing posts and the run exits cleanly.

Usage:
    python -m channels.dinner_menu                     # preview (default)
    python -m channels.dinner_menu --date 2026-11-02   # preview another date
    python -m channels.dinner_menu --post              # post to the board
"""

import argparse
import datetime
import json
import pathlib
import sys
from zoneinfo import ZoneInfo

from vestaboard import blank_grid, post_characters, print_grid, set_row, wrap

TZ = ZoneInfo("America/Los_Angeles")
MENU_PATH = pathlib.Path(__file__).resolve().parent.parent / "menu.json"


def meal_for(day: datetime.date) -> str | None:
    menu = json.loads(MENU_PATH.read_text())
    return menu.get(day.isoformat())


def build_grid(meal: str) -> list[list[int]]:
    g = blank_grid()
    set_row(g, 0, "{orange}{orange} TONIGHT'S DINNER {orange}{orange}")
    lines = wrap(meal.upper(), max_lines=3)
    first = 3 - (len(lines) - 1) // 2  # 1 line -> row 3, 2 -> 3-4, 3 -> 2-4
    for i, line in enumerate(lines):
        set_row(g, first + i, line, align="center")
    return g


def main() -> int:
    parser = argparse.ArgumentParser(description="Dinner menu channel")
    parser.add_argument("--post", action="store_true", help="post to the board")
    parser.add_argument("--dry-run", action="store_true", help="preview only (default)")
    parser.add_argument("--date", help="override today's date (YYYY-MM-DD), for testing")
    args = parser.parse_args()

    day = (
        datetime.date.fromisoformat(args.date)
        if args.date
        else datetime.datetime.now(TZ).date()
    )
    meal = meal_for(day)
    if meal is None:
        print(f"No menu set for {day} - skipping (nothing posted).")
        return 0

    print(f"Dinner for {day}: {meal}")
    grid = build_grid(meal)
    print_grid(grid)

    if args.post and not args.dry_run:
        post_characters(grid)
        print("Posted to the board.")
    else:
        print("Dry run - nothing was posted. Use --post to send to the board.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
