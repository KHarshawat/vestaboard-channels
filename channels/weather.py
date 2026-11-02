"""Duboce Triangle microclimate weather channel.

Two scheduled sequences, pages posted a few minutes apart:

  morning: today, timeline, forecast, then conditional pages - rain
           (only if >= 40% chance today), heat (only if NWS heat risk is
           moderate+), alerts (only if NWS has an active alert for CAZ006),
           aqi (only if US AQI > 100)
  evening: tomorrow, plus alerts if any are active

Data: NWS gridpoint forecasts for the 2.5km square covering 53 Walter St
(office MTR, grid 84,105), tuned by the Monterey/Bay Area office. AQI from
Open-Meteo (keyless). Sunset is computed locally (NOAA sunrise equation).

Usage:
    python -m channels.weather                     # preview morning sequence
    python -m channels.weather --view evening      # preview evening sequence
    python -m channels.weather --view timeline     # preview a single page
    python -m channels.weather --view all          # preview every page
    python -m channels.weather --post              # post (morning sequence)
"""

import argparse
import datetime
import math
import re
import sys
import time
from zoneinfo import ZoneInfo

import requests

from vestaboard import blank_grid, post_characters, print_grid, set_row

LAT, LON = 37.7676, -122.4308  # Duboce Triangle
GRIDPOINT = "https://api.weather.gov/gridpoints/MTR/84,105"
ALERTS_URL = "https://api.weather.gov/alerts/active?zone=CAZ006"
AQI_URL = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
    f"?latitude={LAT}&longitude={LON}&current=us_aqi"
)
HEADERS = {"User-Agent": "vestaboard-channels (github.com/KHarshawat/vestaboard-channels)"}
TZ = ZoneInfo("America/Los_Angeles")
AQI_THRESHOLD = 100
RAIN_THRESHOLD = 40  # percent chance that counts as "rain"
HEAT_THRESHOLD = 2  # NWS heatRisk: 2=moderate, 3=major, 4=extreme

SEQUENCES = {
    "morning": ["today", "timeline", "forecast", "rain", "heat", "alerts", "aqi"],
    "evening": ["tomorrow", "alerts"],
    "all": ["today", "timeline", "forecast", "tomorrow", "rain", "heat", "alerts", "aqi"],
}


def fetch(url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def c_to_f(c: float) -> int:
    return round(c * 9 / 5 + 32)


def from_iso(s: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(s)


_DURATION = re.compile(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?)?")


def expand_layer(layer: dict) -> dict[datetime.datetime, float]:
    """Expand a raw NWS grid layer (values with ISO durations) to hour -> value."""
    out: dict[datetime.datetime, float] = {}
    for v in layer.get("values", []):
        start_s, dur_s = v["validTime"].split("/")
        start = from_iso(start_s)
        m = _DURATION.fullmatch(dur_s)
        hours = (int(m.group(1) or 0) * 24 + int(m.group(2) or 0)) if m else 1
        for h in range(max(hours, 1)):
            out[start + datetime.timedelta(hours=h)] = v["value"]
    return out


def layer_now(layer: dict, now_utc: datetime.datetime) -> float | None:
    """Current value of a raw NWS grid layer (step function over start times)."""
    current = None
    for v in layer.get("values", []):
        if from_iso(v["validTime"].split("/")[0]) <= now_utc:
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


def fmt_wind(speed: str, direction: str) -> str:
    nums = re.findall(r"\d+", speed)
    n = nums[-1] if nums else "?"
    wind = f"{direction}{n}MPH"
    return wind if len(wind) <= 8 else f"{n}MPH"


def wrap(text: str, width: int = 22, max_lines: int = 2) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        if len(cur) + bool(cur) + len(word) <= width:
            cur = f"{cur} {word}".strip()
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines[:max_lines]


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


def hours_on(hourly: list[dict], day: datetime.date) -> list[tuple[datetime.datetime, dict]]:
    out = []
    for p in hourly:
        t = from_iso(p["startTime"]).astimezone(TZ)
        if t.date() == day:
            out.append((t, p))
    return out


def pop_of(period: dict) -> int:
    return period.get("probabilityOfPrecipitation", {}).get("value") or 0


def condition_line(hourly: list[dict], now_local: datetime.datetime) -> str:
    """One-line story for today; calls out the marine layer burning off."""
    todays = hours_on(hourly, now_local.date())
    if not todays:
        return ""
    now_fc = todays[0][1]["shortForecast"].lower()
    if any(t in now_fc for t in FOGGY):
        for t, p in todays[1:]:
            if t.hour > 18:
                break
            if any(c in p["shortForecast"].lower() for c in CLEAR):
                return f"FOG CLEARING BY {fmt_hour(t)}"
    return condense(todays[0][1]["shortForecast"], 22)


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

    return {
        "daily": daily,
        "hourly": hourly,
        "raw": raw,
        "now_local": now_local,
        "now": hourly[0]["temperature"],
        "feels": c_to_f(feels_c) if feels_c is not None else hourly[0]["temperature"],
        "high": high["temperature"],
        "low": low["temperature"],
        "rain": f"{pop_of(high)}%",
        "wind": fmt_wind(hourly[0]["windSpeed"], hourly[0]["windDirection"]),
        "sky": f"{round(sky)}%" if sky is not None else "?",
        "sunset": fmt_time(sunset_local(now_local.date())),
        "condition": condition_line(hourly, now_local),
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


def build_timeline_grid(w: dict) -> list[list[int]]:
    """7am-7pm as one colored tile per hour: sun, fog/cloud, or rain."""
    sky = expand_layer(w["raw"]["skyCover"])
    pops = {t: pop_of(p) for t, p in hours_on(w["hourly"], w["now_local"].date())}
    tiles = ""
    base = w["now_local"].replace(minute=0, second=0, microsecond=0)
    for h in range(7, 20):
        t = base.replace(hour=h)
        sky_v = sky.get(t)
        if pops.get(t, 0) >= RAIN_THRESHOLD:
            tiles += "{blue}"
        elif sky_v is None or sky_v >= 60:
            tiles += "{white}"
        else:
            tiles += "{yellow}"

    labels = [" "] * 22  # 13 tiles centered start at col 4; mark 7am/noon/7pm
    labels[4:6] = "7A"
    labels[8:12] = "NOON"
    labels[15:17] = "7P"

    g = blank_grid()
    set_row(g, 0, "TODAY HOUR BY HOUR", align="center")
    set_row(g, 1, "".join(labels))
    set_row(g, 2, tiles, align="center")
    set_row(g, 4, w["condition"], align="center")
    set_row(g, 5, "{yellow} SUN {white} FOG {blue} RAIN", align="center")
    return g


def build_forecast_grid(w: dict) -> list[list[int]]:
    g = blank_grid()
    set_row(g, 0, "{white} 5 DAY FORECAST {white}", align="center")
    daily = w["daily"]
    periods = daily if daily[0]["isDaytime"] else daily[1:]
    for i in range(5):
        if 2 * i + 1 >= len(periods):
            break
        day, night = periods[2 * i], periods[2 * i + 1]
        start = from_iso(day["startTime"])
        prefix = f"{start.strftime('%a').upper()} {day['temperature']:>2}/{night['temperature']:<2} "
        set_row(g, 1 + i, prefix + condense(day["shortForecast"], 22 - len(prefix)))
    return g


def build_tomorrow_grid(w: dict) -> list[list[int]]:
    tmrw = w["now_local"].date() + datetime.timedelta(days=1)
    daily_tmrw = [
        p for p in w["daily"] if from_iso(p["startTime"]).astimezone(TZ).date() == tmrw
    ]
    day = next(p for p in daily_tmrw if p["isDaytime"])
    night = next(p for p in daily_tmrw if not p["isDaytime"])
    am = next((p for t, p in hours_on(w["hourly"], tmrw) if t.hour == 8), None)

    g = blank_grid()
    set_row(g, 0, "{white}{white} TOMORROW {white}{white}", align="center")
    set_row(g, 1, condense(day["shortForecast"], 22), align="center")
    rows = [
        ("AM", am["temperature"] if am else night["temperature"], "RAIN", f"{pop_of(day)}%"),
        ("HIGH", day["temperature"], "WIND", fmt_wind(day["windSpeed"], day["windDirection"])),
        ("LOW", night["temperature"], "SET", fmt_time(sunset_local(tmrw))),
    ]
    for i, (ll, lv, rl, rv) in enumerate(rows):
        set_row(g, 2 + i, f"{ll:<5}{lv:>3}° {rl:<4}{rv:>8}")
    return g


def build_rain_grid(w: dict) -> list[list[int]] | None:
    todays = hours_on(w["hourly"], w["now_local"].date())
    rainy = [(t, p) for t, p in todays if pop_of(p) >= RAIN_THRESHOLD]
    if not rainy:
        return None
    peak_t, peak_p = max(todays, key=lambda tp: pop_of(tp[1]))
    total_mm = sum(
        v["value"] or 0
        for v in w["raw"]["quantitativePrecipitation"]["values"]
        if from_iso(v["validTime"].split("/")[0]).astimezone(TZ).date()
        == w["now_local"].date()
    )
    total_in = total_mm / 25.4

    g = blank_grid()
    set_row(g, 0, "{blue}{blue} RAIN TODAY {blue}{blue}", align="center")
    if len(rainy) >= 10:
        window = "ON & OFF ALL DAY"
    else:
        window = f"{fmt_hour(rainy[0][0])} - {fmt_hour(rainy[-1][0])}"
    set_row(g, 2, f"RAIN {window}", align="center")
    set_row(g, 3, f"PEAK {pop_of(peak_p)}% AT {fmt_hour(peak_t)}", align="center")
    set_row(g, 4, f"TOTAL {'<0.1' if total_in < 0.05 else f'{total_in:.1f}'} IN", align="center")
    return g


HEAT_LABELS = {2: ("MODERATE", "orange"), 3: ("MAJOR", "red"), 4: ("EXTREME", "violet")}


def build_heat_grid(w: dict) -> list[list[int]] | None:
    risk_by_hour = expand_layer(w["raw"].get("heatRisk", {}))
    today = w["now_local"].date()
    todays = [
        v
        for t, v in risk_by_hour.items()
        if t.astimezone(TZ).date() == today and v is not None
    ]
    risk = round(max(todays)) if todays else 0
    if risk < HEAT_THRESHOLD:
        return None
    label, tile_name = HEAT_LABELS[min(risk, 4)]
    t = "{%s}" % tile_name
    g = blank_grid()
    set_row(g, 0, f"{t}{t} HEAT ALERT {t}{t}", align="center")
    set_row(g, 2, f"HIGH {w['high']}° TODAY", align="center")
    set_row(g, 3, f"HEAT RISK {label}", align="center")
    set_row(g, 5, f"{t} HYDRATE, STAY COOL {t}", align="center")
    return g


_SEVERITY = {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3}


def build_alerts_grid(alerts: dict) -> list[list[int]] | None:
    feats = alerts.get("features", [])
    if not feats:
        return None
    props = sorted(
        (f["properties"] for f in feats),
        key=lambda p: _SEVERITY.get(p.get("severity"), 4),
    )
    top = props[0]
    g = blank_grid()
    set_row(g, 0, "{red}{red} NWS ALERT {red}{red}", align="center")
    for i, line in enumerate(wrap(top["event"].upper())):
        set_row(g, 2 + i, line, align="center")
    ends_s = top.get("ends") or top.get("expires")
    if ends_s:
        ends = from_iso(ends_s).astimezone(TZ)
        set_row(g, 4, f"UNTIL {ends.strftime('%a').upper()} {fmt_hour(ends)}", align="center")
    if len(props) > 1:
        set_row(g, 5, f"+{len(props) - 1} MORE ALERTS", align="center")
    return g


def main() -> int:
    parser = argparse.ArgumentParser(description="Duboce Triangle weather channel")
    parser.add_argument("--post", action="store_true", help="post to the board")
    parser.add_argument("--dry-run", action="store_true", help="preview only (default)")
    parser.add_argument(
        "--view",
        default="morning",
        choices=list(SEQUENCES) + SEQUENCES["all"],
        help="a sequence (morning/evening/all) or a single page",
    )
    parser.add_argument(
        "--gap", type=int, default=180, help="seconds between posts (default 180)"
    )
    args = parser.parse_args()
    posting = args.post and not args.dry_run
    pages = SEQUENCES.get(args.view, [args.view])

    w = get_weather() if set(pages) - {"alerts", "aqi"} else None
    grids: list[tuple[str, list[list[int]]]] = []
    for name in pages:
        grid = None
        skip = None
        if name in ("today", "timeline", "forecast", "tomorrow", "rain", "heat"):
            grid = {
                "today": build_today_grid,
                "timeline": build_timeline_grid,
                "forecast": build_forecast_grid,
                "tomorrow": build_tomorrow_grid,
                "rain": build_rain_grid,
                "heat": build_heat_grid,
            }[name](w)
            skip = {"rain": "no rain expected today", "heat": "heat risk is low"}.get(name)
        elif name == "alerts":
            try:
                grid = build_alerts_grid(fetch(ALERTS_URL))
                skip = "no active NWS alerts for CAZ006"
            except requests.RequestException as e:
                skip = f"alerts fetch failed ({e})"
        elif name == "aqi":
            try:
                aqi = round(fetch(AQI_URL)["current"]["us_aqi"])
                if aqi > AQI_THRESHOLD:
                    grid = build_aqi_grid(aqi)
                else:
                    skip = f"AQI is {aqi} (<= {AQI_THRESHOLD})"
            except requests.RequestException as e:
                skip = f"AQI fetch failed ({e})"
        if grid is None:
            print(f"[{name}] skipped - {skip}")
        else:
            grids.append((name, grid))

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


if __name__ == "__main__":
    sys.exit(main())
