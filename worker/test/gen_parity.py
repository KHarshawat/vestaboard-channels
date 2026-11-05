"""Generate test/fixtures/parity.json: expected grids from the Python channels.

Run from the repo root:  python worker/test/gen_parity.py
The vitest suite replays the same inputs through the TypeScript port and
asserts identical grids, so the Worker is a faithful port.
"""

import datetime
import json
import pathlib
import random
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from channels import dinner_menu, fun_holidays, letter_of_the_day, moon_phase, muni, weather  # noqa: E402
from vestaboard.render import encode, wrap  # noqa: E402

TZ = weather.TZ
OUT = pathlib.Path(__file__).parent / "fixtures"
OUT.mkdir(exist_ok=True)

parity: dict = {}

# ---- render helpers ---------------------------------------------------------
parity["encode"] = {
    s: encode(s)
    for s in ["{white}{white} TODAY'S WEATHER {white}{white}", "NOW   52° RAIN      2%", "a-b/c?d!", "{RED}x{Blue}"]
}
parity["wrap"] = [
    {"text": t, "width": w, "max_lines": m, "lines": wrap(t, w, m)}
    for t, w, m in [
        ("Run It up the Flagpole and See If Anyone Salutes It Day", 20, 4),
        ("COCONUT LENTIL SOUP", 22, 3),
        ("SUPERCALIFRAGILISTICEXPIALIDOCIOUS WORD", 22, 3),
        ("", 22, 3),
    ]
]

# ---- letter ---------------------------------------------------------------
days = [datetime.date(2026, 1, 1) + datetime.timedelta(days=i) for i in range(0, 400, 7)]
parity["letter"] = [{"date": d.isoformat(), "letter": letter_of_the_day.letter_for(d),
                     "grid": letter_of_the_day.build_grid(d)} for d in days]

# ---- holidays (every day of 2026 + Easter-relative 2027 spot checks) -------
hol = []
d = datetime.date(2026, 1, 1)
while d.year == 2026:
    names = fun_holidays.holidays_for(d)
    hol.append({"date": d.isoformat(), "names": names, "grid": fun_holidays.build_grid(d) if names else None})
    d += datetime.timedelta(days=1)
for d in [datetime.date(2027, 2, 9), datetime.date(2027, 3, 24), datetime.date(2027, 11, 30), datetime.date(2028, 5, 28)]:
    names = fun_holidays.holidays_for(d)
    hol.append({"date": d.isoformat(), "names": names, "grid": fun_holidays.build_grid(d) if names else None})
parity["holidays"] = hol

# ---- moon -----------------------------------------------------------------
moon = []
d = datetime.date(2026, 1, 1)
while d < datetime.date(2027, 3, 1):
    when = datetime.datetime(d.year, d.month, d.day, 18, tzinfo=TZ)
    moon.append({"date": d.isoformat(), "grid": moon_phase.build_grid(when)})
    d += datetime.timedelta(days=2)
for iso in ["2026-11-24T22:30:00+00:00", "2026-05-31T08:45:00+00:00", "2026-12-04T23:14:00+00:00"]:
    when = datetime.datetime.fromisoformat(iso)
    moon.append({"instant": iso, "grid": moon_phase.build_grid(when)})
parity["moon"] = moon

# ---- dinner ---------------------------------------------------------------
parity["dinner"] = [
    {"meal": m, "grid": dinner_menu.build_grid(m)}
    for m in ["Coconut Lentil Soup", "Pizza", "Slow cooker pulled pork sandwiches with coleslaw and fries"]
]

# ---- muni -----------------------------------------------------------------
NOW = datetime.datetime(2026, 11, 5, 16, 0, tzinfo=datetime.UTC)  # 8:00am PST


def visit(mins: float, line="N", name="Judah"):
    when = NOW + datetime.timedelta(minutes=mins)
    return {"MonitoredVehicleJourney": {"LineRef": line, "PublishedLineName": name,
            "MonitoredCall": {"ExpectedArrivalTime": when.strftime("%Y-%m-%dT%H:%M:%SZ")}}}


muni_cases = {
    "normal": ([visit(3.4), visit(11), visit(0.2), visit(25), visit(95)], [visit(7), visit(-0.5)]),
    "none": ([], [visit(2)]),
    "due": ([visit(0.1)], [visit(0.4), visit(0.3)]),
}
parity["muni"] = []
for name, (ev, wv) in muni_cases.items():
    east, west = muni.arrivals(ev, NOW), muni.arrivals(wv, NOW)
    parity["muni"].append({"name": name, "east_visits": ev, "west_visits": wv, "now": NOW.isoformat(),
                           "east": list(east), "west": list(west), "grid": muni.build_grid(east, west, NOW)})

# ---- weather --------------------------------------------------------------


def make_fixture(seed: int, scenario: str, now_utc: datetime.datetime) -> dict:
    rnd = random.Random(seed)
    now_local = now_utc.astimezone(TZ)
    day0 = now_local.date()
    hour0 = now_local.replace(minute=0, second=0, microsecond=0)

    def iso(dt):
        return dt.isoformat()

    hourly = []
    for i in range(156):
        t = hour0 + datetime.timedelta(hours=i)
        lt = t.astimezone(TZ)
        if scenario == "storm":
            pop = 70 if 9 <= lt.hour <= 16 and (lt.date() - day0).days == 0 else 20
            fc = "Rain Showers" if pop >= 40 else "Mostly Cloudy"
            temp = 58 + (lt.hour - 12) // 3
        else:
            pop = 2 if i % 7 else 5
            if lt.hour < 10:
                fc = "Patchy Fog"
            elif lt.hour < 11:
                fc = "Partly Sunny then Sunny"
            else:
                fc = "Sunny"
            temp = 52 + max(0, 14 - abs(lt.hour - 15))
        hourly.append({"startTime": iso(lt), "endTime": iso(lt + datetime.timedelta(hours=1)), "isDaytime": 6 <= lt.hour < 18,
                       "temperature": temp, "temperatureUnit": "F", "probabilityOfPrecipitation": {"value": pop},
                       "windSpeed": f"{rnd.choice([3, 7, 12, 15])} mph", "windDirection": rnd.choice(["W", "NNW", "ENE", "SW"]),
                       "shortForecast": fc})

    daily = []
    start = datetime.datetime(day0.year, day0.month, day0.day, 6, tzinfo=TZ)
    names = ["Today", "Tonight"]
    for i in range(14):
        t = start + datetime.timedelta(hours=12 * i)
        is_day = i % 2 == 0
        if scenario == "storm":
            fc = "Rain Showers Likely" if i < 2 else rnd.choice(["Chance Rain Showers", "Mostly Cloudy", "Partly Sunny"])
            pop = 70 if i < 2 else rnd.choice([30, 50, 20])
            temp = 61 if is_day else 50
        else:
            fc = "Patchy Fog then Sunny" if i == 0 else rnd.choice(["Sunny", "Mostly Sunny", "Partly Cloudy", "Areas of Fog then Mostly Sunny"])
            pop = 0 if i < 4 else rnd.choice([0, 10, 20])
            temp = (64 + rnd.randint(-3, 4)) if is_day else (50 + rnd.randint(-2, 3))
        daily.append({"number": i + 1, "name": names[i] if i < 2 else t.strftime("%A") + ("" if is_day else " Night"),
                      "startTime": iso(t), "endTime": iso(t + datetime.timedelta(hours=12)), "isDaytime": is_day,
                      "temperature": temp, "temperatureUnit": "F", "probabilityOfPrecipitation": {"value": pop or None},
                      "windSpeed": f"{rnd.choice([5, 8])} to {rnd.choice([10, 14, 18])} mph", "windDirection": rnd.choice(["W", "NW", "SW"]),
                      "shortForecast": fc})

    def layer(values):
        return {"uom": "x", "values": values}

    base_utc = hour0.astimezone(datetime.UTC) - datetime.timedelta(hours=3)
    app = [{"validTime": f"{iso(base_utc + datetime.timedelta(hours=3*i))}/PT3H", "value": 9.5 + i * 0.7} for i in range(40)]
    sky = [{"validTime": f"{iso(base_utc + datetime.timedelta(hours=i))}/PT1H",
            "value": (85 if (base_utc + datetime.timedelta(hours=i)).astimezone(TZ).hour < 11 else 10) if scenario != "storm" else 95}
           for i in range(96)]
    qpf = [{"validTime": f"{iso(base_utc + datetime.timedelta(hours=6*i))}/PT6H", "value": (3.2 if scenario == "storm" else 0)} for i in range(16)]
    heat = [{"validTime": f"{iso(base_utc + datetime.timedelta(hours=24*i))}/P1D", "value": (3 if scenario == "storm" and i == 0 else 0)} for i in range(4)]
    raw = {"apparentTemperature": layer(app), "skyCover": layer(sky), "quantitativePrecipitation": layer(qpf), "heatRisk": layer(heat)}

    if scenario == "storm":
        alerts = {"features": [
            {"properties": {"event": "Wind Advisory", "severity": "Moderate", "ends": iso(now_local + datetime.timedelta(hours=10)), "expires": None}},
            {"properties": {"event": "High Surf Warning", "severity": "Severe", "ends": None, "expires": iso(now_local + datetime.timedelta(hours=30))}},
        ]}
        aqi = {"current": {"us_aqi": 163.4}}
    else:
        alerts = {"features": []}
        aqi = {"current": {"us_aqi": 51.6}}

    return {
        "now": now_utc.isoformat(),
        "responses": {
            f"{weather.GRIDPOINT}/forecast": {"properties": {"periods": daily}},
            f"{weather.GRIDPOINT}/forecast/hourly": {"properties": {"periods": hourly}},
            weather.GRIDPOINT: {"properties": raw},
            weather.ALERTS_URL: alerts,
            weather.AQI_URL: aqi,
        },
    }


class FakeDateTime(datetime.datetime):
    fixed: datetime.datetime

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return cls.fixed.astimezone(tz) if tz else cls.fixed.replace(tzinfo=None)


def run_python_weather(fixture: dict) -> dict:
    FakeDateTime.fixed = datetime.datetime.fromisoformat(fixture["now"])
    weather.datetime = types.SimpleNamespace(datetime=FakeDateTime, timedelta=datetime.timedelta,
                                             date=datetime.date, UTC=datetime.UTC)
    weather.fetch = lambda url: json.loads(json.dumps(fixture["responses"][url]))
    w = weather.get_weather()
    pages = {
        "today": weather.build_today_grid(w),
        "timeline": weather.build_timeline_grid(w),
        "forecast": weather.build_forecast_grid(w),
        "tomorrow": weather.build_tomorrow_grid(w),
        "rain": weather.build_rain_grid(w),
        "heat": weather.build_heat_grid(w),
        "alerts": weather.build_alerts_grid(weather.fetch(weather.ALERTS_URL)),
    }
    aqi = round(weather.fetch(weather.AQI_URL)["current"]["us_aqi"])
    pages["aqi"] = weather.build_aqi_grid(aqi) if aqi > weather.AQI_THRESHOLD else None
    return pages


parity["weather"] = []
for name, seed, scenario, now in [
    ("fog-morning", 1, "fog", datetime.datetime(2026, 11, 5, 15, 20, tzinfo=datetime.UTC)),   # 7:20am PST
    ("fog-evening", 2, "fog", datetime.datetime(2026, 11, 6, 4, 30, tzinfo=datetime.UTC)),    # 8:30pm PST
    ("storm-morning", 3, "storm", datetime.datetime(2026, 7, 14, 14, 30, tzinfo=datetime.UTC)),  # 7:30am PDT
]:
    fx = make_fixture(seed, scenario, now)
    parity["weather"].append({"name": name, "fixture": fx, "pages": run_python_weather(fx)})

parity["sunset"] = [
    {"date": d.isoformat(), "iso": weather.sunset_local(d).isoformat()}
    for d in [datetime.date(2026, 1, 1), datetime.date(2026, 3, 8), datetime.date(2026, 6, 21), datetime.date(2026, 11, 5), datetime.date(2026, 12, 21)]
]

(OUT / "parity.json").write_text(json.dumps(parity, ensure_ascii=False))
print("wrote", OUT / "parity.json",
      f"({len(parity['holidays'])} holiday days, {len(parity['moon'])} moon dates, {len(parity['weather'])} weather scenarios)")
