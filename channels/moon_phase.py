"""Moon phase channel.

Phase math ported from the Tidbyt community moonphase app
(github.com/tidbyt/community/tree/main/apps/moonphase): position in the
lunar cycle from a reference new moon, no API needed.

Layout: phase name, a countdown to the cycle's full moon by its
traditional name (Wolf Moon, Beaver Moon, ... Blue Moon when it is the
second full moon of a month), and an illumination bar that fills with
white tiles left-to-right while waxing and drains right-to-left while
waning.

Usage:
    python -m channels.moon_phase                     # preview (default)
    python -m channels.moon_phase --date 2026-11-24   # preview another date
    python -m channels.moon_phase --post              # post to the board
"""

import argparse
import datetime
import math
import sys
from zoneinfo import ZoneInfo

from vestaboard import blank_grid, post_characters, print_grid, set_row

TZ = ZoneInfo("America/Los_Angeles")
LUNATION = 29.530588  # days; 29d 12h 44m 3s
REF_NEW_MOON = datetime.datetime(2022, 4, 30, 20, 28, tzinfo=datetime.UTC)
BAR_CELLS = 18  # tiles inside the ( ) illumination bar

PHASE_NAMES = [
    "NEW MOON",
    "WAXING CRESCENT",
    "FIRST QUARTER",
    "WAXING GIBBOUS",
    "FULL MOON",
    "WANING GIBBOUS",
    "LAST QUARTER",
    "WANING CRESCENT",
]

# Traditional full moon names by month (Farmers' Almanac).
MOON_NAMES = {
    1: "WOLF",
    2: "SNOW",
    3: "WORM",
    4: "PINK",
    5: "FLOWER",
    6: "STRAWBERRY",
    7: "BUCK",
    8: "STURGEON",
    9: "HARVEST",
    10: "HUNTER'S",
    11: "BEAVER",
    12: "COLD",
}


def name_of_full(full_dt: datetime.datetime) -> str:
    local = full_dt.astimezone(TZ)
    one_before = (full_dt - datetime.timedelta(days=LUNATION)).astimezone(TZ)
    if one_before.month == local.month:
        return "BLUE"  # second full moon of the calendar month
    return MOON_NAMES[local.month]


def phase_info(when: datetime.datetime) -> dict:
    age = ((when - REF_NEW_MOON).total_seconds() / 86400) % LUNATION
    frac = age / LUNATION
    days_to_full = ((0.5 - frac) % 1) * LUNATION
    next_full = when + datetime.timedelta(days=days_to_full)
    prev_full = next_full - datetime.timedelta(days=LUNATION)
    # Just past the exact full instant it is still "the Beaver Moon",
    # not next month's — name from the nearest full moon.
    nearest_full = prev_full if days_to_full > LUNATION / 2 else next_full
    return {
        "frac": frac,
        "name": PHASE_NAMES[int((frac * 8 + 0.5) % 8)],
        "illum": (1 - math.cos(2 * math.pi * frac)) / 2,
        "moon_name": name_of_full(nearest_full),
        "next_moon_name": name_of_full(next_full),
        "days_to_full": days_to_full,
    }


def countdown_line(moon_name: str, days: float, tonight: bool) -> str:
    if tonight:
        tails = ["MOON TONIGHT", "TONIGHT"]
    elif round(days) == 1:
        tails = ["MOON TOMORROW", "TOMORROW"]
    else:
        tails = [f"MOON IN {round(days)} DAYS", f"MOON {round(days)} DAYS", f"{round(days)} DAYS"]
    for tail in tails:
        line = f"{moon_name} {tail}"
        if len(line) <= 22:
            return line
    return f"{moon_name} {round(days)}D"


def illumination_bar(illum: float, waxing: bool) -> str:
    """( ) bar: white fills left-to-right waxing, drains to the right waning."""
    lit = round(illum * BAR_CELLS)
    white = "{white}" * lit
    dark = " " * (BAR_CELLS - lit)
    return f"({white}{dark})" if waxing else f"({dark}{white})"


def build_grid(when: datetime.datetime) -> list[list[int]]:
    p = phase_info(when)
    phase = f"{p['moon_name']} MOON" if p["name"] == "FULL MOON" else p["name"]
    g = blank_grid()
    set_row(g, 0, "{white}{white} MOON PHASE {white}{white}", align="center")
    set_row(g, 2, phase, align="center")
    # The simple lunation model drifts up to ~0.6 days from the true moon,
    # so treat "just past full" generously on the past side.
    tonight = p["days_to_full"] > LUNATION - 1.3 or p["days_to_full"] < 0.75
    countdown_name = p["moon_name"] if tonight else p["next_moon_name"]
    set_row(g, 3, countdown_line(countdown_name, p["days_to_full"], tonight), align="center")
    set_row(g, 5, illumination_bar(p["illum"], waxing=p["frac"] < 0.5), align="center")
    return g


def main() -> int:
    parser = argparse.ArgumentParser(description="Moon phase channel")
    parser.add_argument("--post", action="store_true", help="post to the board")
    parser.add_argument("--dry-run", action="store_true", help="preview only (default)")
    parser.add_argument("--date", help="override today's date (YYYY-MM-DD), for testing")
    args = parser.parse_args()

    if args.date:
        day = datetime.date.fromisoformat(args.date)
        when = datetime.datetime(day.year, day.month, day.day, 18, tzinfo=TZ)
    else:
        when = datetime.datetime.now(datetime.UTC)
    grid = build_grid(when)

    print(f"Moon phase for {when.astimezone(TZ):%Y-%m-%d}:")
    print_grid(grid)

    if args.post and not args.dry_run:
        post_characters(grid)
        print("Posted to the board.")
    else:
        print("Dry run - nothing was posted. Use --post to send to the board.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
