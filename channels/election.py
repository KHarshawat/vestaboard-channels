"""Election night channel - live House and Senate seat distribution.

Pulls called-seat counts from the NYT election results feeds (updated
continuously on election nights) and renders both chambers on one board:
a numbers line plus a 22-tile bar per chamber - blue = Dem seats,
red = GOP seats, white = not yet called (incl. third party).

    ELECTION NIGHT 2026
    HOUSE   D 102  R  87
    bbbbbwwwwwwwwwwwwrrrr
    SENATE  D  45  R  44
    bbbbbbbbbbwwwrrrrrrrr
    AS OF 7:52PM

--watch loops fetch+post every --interval seconds (default 60) for
--duration minutes, only re-posting when the counts change. Run it as a
manually dispatched workflow on election nights.

Usage:
    python -m channels.election                      # preview once
    python -m channels.election --post               # post once
    python -m channels.election --post --watch      # live for 5 hours
"""

import argparse
import datetime
import sys
import time
from zoneinfo import ZoneInfo

import requests

from vestaboard import blank_grid, post_characters, print_grid, set_row
from vestaboard.characters import COLS

TZ = ZoneInfo("America/Los_Angeles")
ELECTION_DATE = "2026-11-03"
URL = "https://static01.nyt.com/elections-assets/pages/data/{date}/results-{chamber}.json"
HEADERS = {"User-Agent": "vestaboard-channels (github.com/KHarshawat/vestaboard-channels)"}


def fetch_chamber(chamber: str, date: str) -> dict:
    resp = requests.get(URL.format(date=date, chamber=chamber), headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    office = data["partyControlData"]["results"][0]["offices"]["H" if chamber == "house" else "S"]
    balance = office["party_balance"]
    return {
        "dem": balance["DEM"]["seats"],
        "gop": balance["GOP"]["seats"],
        "total": office["total"],
        "updated": data["resultsMeta"]["resultsUpdatedAt"],
    }


def seat_bar(dem: int, gop: int, total: int) -> str:
    """22 tiles: Dem blue from the left, GOP red from the right, white between."""
    b = round(dem / total * COLS)
    r = round(gop / total * COLS)
    if b + r > COLS:  # rounding overflow once nearly all seats are called
        r = COLS - b
    return "{blue}" * b + "{white}" * (COLS - b - r) + "{red}" * r


def fmt_time(iso: str) -> str:
    dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
    h = dt.hour % 12 or 12
    return f"{h}:{dt.minute:02d}{'PM' if dt.hour >= 12 else 'AM'}"


def build_grid(house: dict, senate: dict) -> list[list[int]]:
    g = blank_grid()
    year = ELECTION_DATE[:4]
    set_row(g, 0, f"ELECTION NIGHT {year}", align="center")
    for row, (label, c) in enumerate([("HOUSE", house), ("SENATE", senate)]):
        set_row(g, 1 + 2 * row, f"{label:<8}D{c['dem']:>4}  R{c['gop']:>4}")
        set_row(g, 2 + 2 * row, seat_bar(c["dem"], c["gop"], c["total"]))
    set_row(g, 5, f"AS OF {fmt_time(house['updated'])}", align="center")
    return g


def main() -> int:
    parser = argparse.ArgumentParser(description="Election night results channel")
    parser.add_argument("--post", action="store_true", help="post to the board")
    parser.add_argument("--dry-run", action="store_true", help="preview only (default)")
    parser.add_argument("--watch", action="store_true", help="keep refreshing")
    parser.add_argument("--interval", type=int, default=60, help="seconds between refreshes")
    parser.add_argument("--duration", type=int, default=300, help="watch duration in minutes")
    parser.add_argument(
        "--until", default="23:00",
        help="hard stop at this local time (HH:MM, default 23:00)",
    )
    parser.add_argument("--date", default=ELECTION_DATE, help="election date YYYY-MM-DD")
    args = parser.parse_args()
    posting = args.post and not args.dry_run

    deadline = time.monotonic() + args.duration * 60
    hh, mm = (int(f) for f in args.until.split(":"))
    now_local = datetime.datetime.now(TZ)
    stop_at = now_local.replace(hour=hh, minute=mm, second=0, microsecond=0)
    until_secs = (stop_at - now_local).total_seconds()
    if until_secs > 0:
        deadline = min(deadline, time.monotonic() + until_secs)
    elif args.watch:
        print(f"already past --until {args.until}; running one refresh only")
        args.watch = False
    last_counts = None
    while True:
        try:
            house = fetch_chamber("house", args.date)
            senate = fetch_chamber("senate", args.date)
        except requests.RequestException as e:
            print(f"fetch failed ({e}); will retry" if args.watch else f"fetch failed: {e}")
            if not args.watch:
                return 1
            time.sleep(args.interval)
            continue

        counts = (house["dem"], house["gop"], senate["dem"], senate["gop"])
        if counts != last_counts:
            grid = build_grid(house, senate)
            stamp = datetime.datetime.now(TZ).strftime("%H:%M:%S")
            print(f"[{stamp}] HOUSE D{house['dem']} R{house['gop']} | "
                  f"SENATE D{senate['dem']} R{senate['gop']}")
            print_grid(grid)
            if posting:
                try:
                    post_characters(grid)
                    print("Posted to the board.")
                except SystemExit:
                    print("Board is muted - stopping watch.")
                    return 1
            last_counts = counts
        elif args.watch:
            print(f"no change (D{counts[0]} R{counts[1]} / D{counts[2]} R{counts[3]})")

        if not args.watch or time.monotonic() >= deadline:
            break
        time.sleep(args.interval)

    if not posting:
        print("Dry run - nothing was posted. Use --post to send to the board.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
