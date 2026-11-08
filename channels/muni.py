"""SF Muni arrivals channel (N Judah at Duboce Park).

Next arrivals for the eastbound and westbound stops, from the 511.org
StopMonitoring API (SIRI). Requires a free API key from
https://511.org/open-data/token in the TRANSIT_511_API_KEY env var
(repo secret of the same name in CI).

Inspired by the Tidbyt sfnextmuni app, which uses the same 511.org data.

Usage:
    python -m channels.muni            # preview (default)
    python -m channels.muni --post     # post to the board
"""

import argparse
import datetime
import json
import os
import sys
from zoneinfo import ZoneInfo

import requests

from vestaboard import blank_grid, post_characters, print_grid, set_row

TZ = ZoneInfo("America/Los_Angeles")
STOPS = [("EAST", "17318"), ("WEST", "17252")]
URL = "https://api.511.org/transit/StopMonitoring?format=json&agency=SF&stopCode={stop}&api_key={key}"
MAX_ARRIVALS = 3


def api_key() -> str:
    key = os.environ.get("TRANSIT_511_API_KEY")
    if not key:
        raise RuntimeError(
            "TRANSIT_511_API_KEY is not set. Get a free key at "
            "https://511.org/open-data/token and export it (or add it as a "
            "repo secret)."
        )
    return key


def fetch_visits(stop: str) -> list[dict]:
    resp = requests.get(URL.format(stop=stop, key=api_key()), timeout=30)
    resp.raise_for_status()
    # 511.org responses start with a UTF-8 BOM
    data = json.loads(resp.content.decode("utf-8-sig"))
    delivery = data["ServiceDelivery"]["StopMonitoringDelivery"]
    return delivery.get("MonitoredStopVisit", [])


def arrivals(visits: list[dict], now: datetime.datetime) -> tuple[str | None, list[int]]:
    """Return (line label, minutes-away list) from StopMonitoring visits."""
    line = None
    mins: list[int] = []
    for visit in visits:
        journey = visit["MonitoredVehicleJourney"]
        if line is None and journey.get("LineRef"):
            name = (journey.get("PublishedLineName") or "").strip()
            line = f"{journey['LineRef']} {name}".strip().upper()
        call = journey.get("MonitoredCall") or {}
        when_s = call.get("ExpectedArrivalTime") or call.get("AimedArrivalTime")
        if not when_s:
            continue
        minutes = (datetime.datetime.fromisoformat(when_s) - now).total_seconds() / 60
        if -1 <= minutes < 90:
            mins.append(max(0, round(minutes)))
    return line, sorted(mins)[:MAX_ARRIVALS]


def times_text(mins: list[int]) -> str:
    if not mins:
        return "NO ARRIVALS"
    parts = ["DUE" if m == 0 else str(m) for m in mins]
    return f"{', '.join(parts)} MIN" if any(m > 0 for m in mins) else "DUE"


# Muni Metro line colors, by LineRef; buses and unknown lines get white.
LINE_COLORS = {"J": "orange", "K": "blue", "L": "violet", "M": "green", "N": "blue", "T": "red"}


def line_color(line: str | None) -> str:
    return LINE_COLORS.get((line or "").split(" ")[0], "white")


def build_grid(
    east: tuple[str | None, list[int]],
    west: tuple[str | None, list[int]],
    now: datetime.datetime,
) -> list[list[int]]:
    line = east[0] or west[0] or "MUNI"
    c = "{%s}" % line_color(line)
    header = f"{c}{c} {line} {c}{c}"
    if len(line) + 8 > 22:
        header = f"{c} {line} {c}"
    g = blank_grid()
    set_row(g, 0, header, align="center")
    set_row(g, 2, f"{'EAST':<5}{times_text(east[1]):>17}")
    set_row(g, 3, f"{'WEST':<5}{times_text(west[1]):>17}")
    local = now.astimezone(TZ)
    h = local.hour % 12 or 12
    set_row(g, 5, f"AS OF {h}:{local.minute:02d}{'PM' if local.hour >= 12 else 'AM'}", align="center")
    return g


def main() -> int:
    parser = argparse.ArgumentParser(description="SF Muni arrivals channel")
    parser.add_argument("--post", action="store_true", help="post to the board")
    parser.add_argument("--dry-run", action="store_true", help="preview only (default)")
    args = parser.parse_args()

    now = datetime.datetime.now(datetime.UTC)
    east, west = (arrivals(fetch_visits(stop), now) for _, stop in STOPS)
    grid = build_grid(east, west, now)

    print(f"Muni arrivals - EAST {east}, WEST {west}")
    print_grid(grid)

    if args.post and not args.dry_run:
        post_characters(grid)
        print("Posted to the board.")
    else:
        print("Dry run - nothing was posted. Use --post to send to the board.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
