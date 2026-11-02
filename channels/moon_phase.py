"""Moon phase channel.

Phase math ported from the Tidbyt community moonphase app
(github.com/tidbyt/community/tree/main/apps/moonphase): position in the
lunar cycle from a reference new moon, no API needed. Illumination is
(1 - cos(phase angle)) / 2.

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


def phase_info(when: datetime.datetime) -> dict:
    age = ((when - REF_NEW_MOON).total_seconds() / 86400) % LUNATION
    frac = age / LUNATION
    name = PHASE_NAMES[int((frac * 8 + 0.5) % 8)]
    illum = round((1 - math.cos(2 * math.pi * frac)) / 2 * 100)
    days_to_full = ((0.5 - frac) % 1) * LUNATION
    days_to_new = ((1 - frac) % 1) * LUNATION
    event, days = min(
        (("FULL MOON", days_to_full), ("NEW MOON", days_to_new)), key=lambda e: e[1]
    )
    return {"name": name, "illum": illum, "event": event, "days": days}


def event_line(event: str, days: float) -> str:
    if days < 0.75:
        return f"{event} TONIGHT"
    if round(days) == 1:
        return f"{event} TOMORROW"
    return f"{event} IN {round(days)} DAYS"


def build_grid(when: datetime.datetime) -> list[list[int]]:
    p = phase_info(when)
    g = blank_grid()
    set_row(g, 0, "{white}{white} MOON PHASE {white}{white}", align="center")
    set_row(g, 2, p["name"], align="center")
    set_row(g, 3, f"{p['illum']}% ILLUMINATED", align="center")
    set_row(g, 5, event_line(p["event"], p["days"]), align="center")
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
