"""Duboce Triangle microclimate weather channel.

Posts up to three views in sequence (a few minutes apart):
  1. today   - current conditions, high/low, rain, wind, sky cover, sunset
  2. forecast - 5-day outlook
  3. aqi     - air quality alert, only posted when US AQI > 100

Data: NWS gridpoint forecasts for the 2.5km square covering 53 Walter St
(office MTR, grid 84,105), tuned by the Monterey/Bay Area office. AQI from
Open-Meteo (keyless). Sunset is computed locally (NOAA sunrise equation).

Usage:
    python -m channels.weather                    # preview all views
    python -m channels.weather --view today       # preview one view
    python -m channels.weather --post             # post the sequence
"""

import argparse
import datetime
import math
import sys
import time
from zoneinfo import ZoneInfo

import requests

from vestaboard import blank_grid, post_characters, print_grid, set_row

LAT, LON = 37.7676, -122.4308  # Duboce Triangle
GRIDPOINT = "https://api.weather.gov/gridpoints/MTR/84,105"
AQI_URL = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
    f"?latitude={LAT}&longitude={LON}&current=us_aqi"
)
HEADERS = {"User-Agent": "vestaboard-channels (github.com/KHarshawat/vestaboard-channels)"}
TZ = ZoneInfo("America/Los_Angeles")
AQI_THRESHOLD = 100


def fetch(url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def c_to_f(c: float) -> int:
    return round(c * 9 / 5 + 32)


def layer_now(layer: dict, now_utc: datetime.datetime) -> float | None:
    """Current value of a raw NWS grid layer (step function over start times)."""
    current = None
    for v in layer.get("values", []):
        start = datetime.datetime.fromisoformat(v["validTime"].split("/")[0])
        if start <= now_utc:
            current = v["value"]
        else:
            break
    return current


def sunset_local(day: datetime.date) -> datetime.datetime:
    """Sunset time via the NOAA sunrise equation (accurate to ~1 min)."""
    n = day.toordinal() + 1721425 - 2451545 + 0.0008  # days since J2000 epoch
    j_star = n - LON / 360
    m = math.radians((357.5291 + 0.98560028 * j_star) % 360)
    c = 1.9148 * math.sin(m) + 0.02 * math.sin(2 * m) + 0.0003 * math.sin(3 * m)
    lam = math.radians((math.degrees(m) + c + 180 + 102.9372) % 360)
    j_transit = 2451545.0 + j_star + 0.0053 * math.sin(m) - 0.0069 * math.sin(2 * lam)
    decl = math.asin(math.sin(lam) * math.sin(math.radians(23.4397)))
    lat = math.radians(LAT)
    cos_h = (math.sin(math.radians(-0.833)) - math.sin(lat) * math.sin(decl)) / (
        math.cos(lat) * math.cos(decl)
    )
    j_set = j_transit + math.degrees(math.acos(cos_h)) / 360
    utc = datetime.datetime(2000, 1, 1, 12, tzinfo=datetime.UTC) + datetime.timedelta(
        days=j_set - 2451545.0
    )
    return utc.astimezone(TZ)


def fmt_time(dt: datetime.datetime) -> str:
    h = dt.hour % 12 or 12
    return f"{h}:{dt.minute:02d}{'PM' if dt.hour >= 12 else 'AM'}"


def fmt_hour(dt: datetime.datetime) -> str:
    h = dt.hour % 12 or 12
    return f"{h}{'PM' if dt.hour >= 12 else 'AM'}"


_ABBREV = [
    ("slight chance ", "chc "),
    ("chance ", "chc "),
    ("scattered ", "sct "),
    ("isolated ", "iso "),
    ("mostly ", "m "),
    ("partly ", "p "),
    ("patchy ", ""),
    ("areas of ", ""),
    ("light ", ""),
    ("rain showers", "showers"),
    ("thunderstorms", "tstorms"),
]


def condense(short_forecast: str, width: int) -> str:
    s = short_forecast.split(" then ")[0].lower()
    for a, b in _ABBREV:
        s = s.replace(a, b)
    return s.upper()[:width].strip()


FOGGY = ("fog", "cloudy", "overcast")
CLEAR = ("sunny", "clear")


def condition_line(hourly_periods: list[dict], now_local: datetime.datetime) -> str:
    """One-line story for today; calls out the marine layer burning off."""
    today = now_local.date()
    todays = [
        p
        for p in hourly_periods
        if datetime.datetime.fromisoformat(p["startTime"]).astimezone(TZ).date() == today
    ]
    if not todays:
        return ""
    now_fc = todays[0]["shortForecast"].lower()
    if any(t in now_fc for t in FOGGY):
        for p in todays[1:]:
            start = datetime.datetime.fromisoformat(p["startTime"]).astimezone(TZ)
            if start.hour > 18:
                break
            if any(t in p["shortForecast"].lower() for t in CLEAR):
                return f"FOG CLEARING BY {fmt_hour(start)}"
    return condense(todays[0]["shortForecast"], 22)


def get_weather() -> dict:
    daily = fetch(f"{GRIDPOINT}/forecast")["properties"]["periods"]
    hourly = fetch(f"{GRIDPOINT}/forecast/hourly")["properties"]["periods"]
    raw = fetch(GRIDPOINT)["properties"]
    now_utc = datetime.datetime.now(datetime.UTC)
    now_local = now_utc.astimezone(TZ)

    high = next((p for p in daily if p["isDaytime"]), daily[0])
    low = next((p for p in daily if not p["isDaytime"]), daily[0])
    feels_c = layer_now(raw["apparentTemperature"], now_utc)
    sky = layer_now(raw["skyCover"], now_utc)
    wind_num = hourly[0]["windSpeed"].split()[0]
    wind = f"{hourly[0]['windDirection']}{wind_num}MPH"
    if len(wind) > 8:
        wind = f"{wind_num}MPH"

    return {
        "now": hourly[0]["temperature"],
        "feels": c_to_f(feels_c) if feels_c is not None else hourly[0]["temperature"],
        "high": high["temperature"],
        "low": low["temperature"],
        "rain": f"{high.get('probabilityOfPrecipitation', {}).get('value') or 0}%",
        "wind": wind,
        "sky": f"{round(sky)}%" if sky is not None else "?",
        "sunset": fmt_time(sunset_local(now_local.date())),
        "condition": condition_line(hourly, now_local),
        "daily": daily,
    }


def build_today_grid(w: dict) -> list[list[int]]:
    g = blank_grid()
    set_row(g, 0, "{white}{white} TODAY'S WEATHER {white}{white}", align="center")
    set_row(g, 1, w["condition"], align="center")
    rows = [
        ("NOW", w["now"], "RAIN", w["rain"]),
        ("LIKE", w["feels"], "WIND", w["wind"]),
        ("HIGH", w["high"], "SKY", w["sky"]),
        ("LOW", w["low"], "SET", w["sunset"]),
    ]
    for i, (ll, lv, rl, rv) in enumerate(rows):
        set_row(g, 2 + i, f"{ll:<5}{lv:>3}° {rl:<4}{rv:>8}")
    return g


def build_forecast_grid(daily: list[dict]) -> list[list[int]]:
    g = blank_grid()
    set_row(g, 0, "{white} 5 DAY FORECAST {white}", align="center")
    periods = daily if daily[0]["isDaytime"] else daily[1:]
    for i in range(5):
        if 2 * i + 1 >= len(periods):
            break
        day, night = periods[2 * i], periods[2 * i + 1]
        start = datetime.datetime.fromisoformat(day["startTime"])
        prefix = f"{start.strftime('%a').upper()} {day['temperature']:>2}/{night['temperature']:<2} "
        set_row(g, 1 + i, prefix + condense(day["shortForecast"], 22 - len(prefix)))
    return g


def aqi_category(aqi: int) -> tuple[str, str, str]:
    if aqi <= 150:
        return "UNHEALTHY (SENSITIVE)", "LIMIT EXERTION", "orange"
    if aqi <= 200:
        return "UNHEALTHY", "LIMIT OUTDOOR TIME", "red"
    if aqi <= 300:
        return "VERY UNHEALTHY", "STAY INDOORS", "violet"
    return "HAZARDOUS", "STAY INDOORS", "violet"


def build_aqi_grid(aqi: int) -> list[list[int]]:
    category, advice, tile = aqi_category(aqi)
    t = "{%s}" % tile
    g = blank_grid()
    set_row(g, 0, f"{t}{t} AIR QUALITY {t}{t}", align="center")
    set_row(g, 2, f"AQI {aqi}", align="center")
    set_row(g, 3, category, align="center")
    set_row(g, 5, f"{t} {advice} {t}", align="center")
    return g


def main() -> int:
    parser = argparse.ArgumentParser(description="Duboce Triangle weather channel")
    parser.add_argument("--post", action="store_true", help="post to the board")
    parser.add_argument("--dry-run", action="store_true", help="preview only (default)")
    parser.add_argument(
        "--view", choices=["all", "today", "forecast", "aqi"], default="all"
    )
    parser.add_argument(
        "--gap", type=int, default=180, help="seconds between posts (default 180)"
    )
    args = parser.parse_args()
    posting = args.post and not args.dry_run

    grids: list[tuple[str, list[list[int]]]] = []
    if args.view in ("all", "today", "forecast"):
        w = get_weather()
        if args.view in ("all", "today"):
            grids.append(("today", build_today_grid(w)))
        if args.view in ("all", "forecast"):
            grids.append(("forecast", build_forecast_grid(w["daily"])))
    if args.view in ("all", "aqi"):
        aqi = round(fetch(AQI_URL)["current"]["us_aqi"])
        if aqi > AQI_THRESHOLD:
            grids.append(("aqi", build_aqi_grid(aqi)))
        else:
            print(f"AQI is {aqi} (<= {AQI_THRESHOLD}) - no air quality page.")
            if args.view == "aqi" and not posting:
                print("Preview of what it would look like when bad:")
                grids.append(("aqi", build_aqi_grid(135)))

    for i, (name, grid) in enumerate(grids):
        print(f"[{name}]")
        print_grid(grid)
        if posting:
            if i > 0:
                time.sleep(args.gap)
            post_characters(grid)
            print(f"Posted {name} to the board.")
    if not posting:
        print("Dry run - nothing was posted. Use --post to send to the board.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
