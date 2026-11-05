/** Duboce Triangle microclimate weather.
 *
 * Pages (each a full board):
 *   today, timeline, forecast           always
 *   rain                                only if >= 40% chance today
 *   heat                                only if NWS heat risk is moderate+
 *   alerts                              only if NWS has an active alert for CAZ006
 *   aqi                                 only if US AQI > 100
 *   tomorrow                            evening view
 *
 * Sequences: morning = today, timeline, forecast + conditionals;
 *            evening = tomorrow, alerts; all = everything.
 *
 * Data: NWS gridpoint MTR/84,105 (the 2.5 km square covering 53 Walter St),
 * AQI from Open-Meteo (keyless), sunset computed locally (NOAA equation).
 */

import type { Grid } from "../board/characters";
import { blankGrid, padL, padR, setRow, wrap } from "../board/render";
import {
  addDays, fmtHour, fmtTime, fmtWeekday, localDate, localParts, pyOrdinal, sameDate, zonedTime,
  type CivilDate,
} from "../time";
import { pyRound } from "../util";
import type { Channel, FetchJson, Page, RenderResult } from "./types";

const LAT = 37.7676, LON = -122.4308; // Duboce Triangle
const GRIDPOINT = "https://api.weather.gov/gridpoints/MTR/84,105";
const ALERTS_URL = "https://api.weather.gov/alerts/active?zone=CAZ006";
const AQI_URL = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${LAT}&longitude=${LON}&current=us_aqi`;
const NWS_HEADERS = { "User-Agent": "vestaboard-channels (github.com/KHarshawat/vestaboard-channels)", Accept: "application/geo+json" };
const AQI_THRESHOLD = 100;
const RAIN_THRESHOLD = 40; // percent chance that counts as "rain"
const HEAT_THRESHOLD = 2; // NWS heatRisk: 2=moderate, 3=major, 4=extreme
const HOUR_MS = 3_600_000;

export const SEQUENCES: Record<string, string[]> = {
  morning: ["today", "timeline", "forecast", "rain", "heat", "alerts", "aqi"],
  evening: ["tomorrow", "alerts"],
  all: ["today", "timeline", "forecast", "tomorrow", "rain", "heat", "alerts", "aqi"],
};
export const PAGES = SEQUENCES.all;

type Layer = { values?: { validTime: string; value: number | null }[] };

const cToF = (c: number) => pyRound((c * 9) / 5 + 32);

/** Expand a raw NWS grid layer (values with ISO durations) to hour-instant(ms) -> value. */
export function expandLayer(layer: Layer | undefined): Map<number, number | null> {
  const out = new Map<number, number | null>();
  for (const v of layer?.values ?? []) {
    const [startS, durS] = v.validTime.split("/");
    const start = new Date(startS).getTime();
    const m = /^P(?:(\d+)D)?(?:T(?:(\d+)H)?)?$/.exec(durS);
    const hours = m ? Number(m[1] ?? 0) * 24 + Number(m[2] ?? 0) : 1;
    for (let h = 0; h < Math.max(hours, 1); h++) out.set(start + h * HOUR_MS, v.value);
  }
  return out;
}

/** Current value of a raw NWS grid layer (step function over start times). */
export function layerNow(layer: Layer | undefined, now: Date): number | null {
  let current: number | null = null;
  for (const v of layer?.values ?? []) {
    if (new Date(v.validTime.split("/")[0]).getTime() <= now.getTime()) current = v.value;
    else break;
  }
  return current;
}

const rad = (deg: number) => (deg * Math.PI) / 180;
const deg = (r: number) => (r * 180) / Math.PI;
const fmod = (a: number, n: number) => ((a % n) + n) % n;

/** Sunset via the NOAA sunrise equation (accurate to ~1 min). */
export function sunset(day: CivilDate): Date {
  const n = pyOrdinal(day) + 1721425 - 2451545 + 0.0008; // days since J2000
  const jStar = n - LON / 360;
  const m = rad(fmod(357.5291 + 0.98560028 * jStar, 360));
  const c = 1.9148 * Math.sin(m) + 0.02 * Math.sin(2 * m) + 0.0003 * Math.sin(3 * m);
  const lam = rad(fmod(deg(m) + c + 180 + 102.9372, 360));
  const jTransit = 2451545.0 + jStar + 0.0053 * Math.sin(m) - 0.0069 * Math.sin(2 * lam);
  const decl = Math.asin(Math.sin(lam) * Math.sin(rad(23.4397)));
  const lat = rad(LAT);
  const cosH = (Math.sin(rad(-0.833)) - Math.sin(lat) * Math.sin(decl)) / (Math.cos(lat) * Math.cos(decl));
  const jSet = jTransit + deg(Math.acos(cosH)) / 360;
  return new Date(Date.UTC(2000, 0, 1, 12) + (jSet - 2451545.0) * 86_400_000);
}

export function fmtWind(speed: string, direction: string): string {
  const nums = speed.match(/\d+/g);
  const n = nums ? nums[nums.length - 1] : "?";
  const wind = `${direction}${n}MPH`;
  // cap at 7 so a space always separates it from the WIND label
  return wind.length <= 7 ? wind : `${n}MPH`;
}

const ABBREV: [string, string][] = [
  ["slight chance ", "chc "], ["chance ", "chc "], ["scattered ", "sct "], ["isolated ", "iso "],
  ["mostly ", "m "], ["partly ", "p "], ["patchy ", ""], ["areas of ", ""], ["light ", ""],
  ["rain showers", "showers"], ["thunderstorms", "tstorms"],
];

export function condense(shortForecast: string, width: number): string {
  let s = shortForecast.split(" then ")[0].toLowerCase();
  for (const [a, b] of ABBREV) s = s.split(a).join(b);
  return s.toUpperCase().slice(0, width).trim();
}

const FOGGY = ["fog", "cloudy", "overcast"];
const CLEAR = ["sunny", "clear"];

type Period = any;
type HourOn = { t: Date; p: Period };

function hoursOn(hourly: Period[], day: CivilDate): HourOn[] {
  const out: HourOn[] = [];
  for (const p of hourly) {
    const t = new Date(p.startTime);
    if (sameDate(localDate(t), day)) out.push({ t, p });
  }
  return out;
}

const popOf = (period: Period): number => period?.probabilityOfPrecipitation?.value || 0;

function conditionLine(hourly: Period[], today: CivilDate): string {
  const todays = hoursOn(hourly, today);
  if (todays.length === 0) return "";
  const nowFc = String(todays[0].p.shortForecast).toLowerCase();
  if (FOGGY.some((f) => nowFc.includes(f))) {
    for (const { t, p } of todays.slice(1)) {
      if (localParts(t).hour > 18) break;
      if (CLEAR.some((c) => String(p.shortForecast).toLowerCase().includes(c))) return `FOG CLEARING BY ${fmtHour(t)}`;
    }
  }
  return condense(todays[0].p.shortForecast, 22);
}

export interface Weather {
  daily: Period[];
  hourly: Period[];
  raw: Record<string, Layer>;
  now: Date;
  today: CivilDate;
  nowTemp: number;
  feels: number;
  high: number;
  low: number;
  rain: string;
  wind: string;
  sky: string;
  sunset: string;
  condition: string;
}

export async function getWeather(fetchJson: FetchJson, now: Date): Promise<Weather> {
  const init = { headers: NWS_HEADERS };
  const [dailyRes, hourlyRes, rawRes] = await Promise.all([
    fetchJson(`${GRIDPOINT}/forecast`, init),
    fetchJson(`${GRIDPOINT}/forecast/hourly`, init),
    fetchJson(GRIDPOINT, init),
  ]);
  const daily: Period[] = dailyRes.properties.periods;
  const hourly: Period[] = hourlyRes.properties.periods;
  const raw: Record<string, Layer> = rawRes.properties;
  const today = localDate(now);

  const high = daily.find((p) => p.isDaytime) ?? daily[0];
  const low = daily.find((p) => !p.isDaytime) ?? daily[0];
  const feelsC = layerNow(raw.apparentTemperature, now);
  const sky = layerNow(raw.skyCover, now);

  return {
    daily, hourly, raw, now, today,
    nowTemp: hourly[0].temperature,
    feels: feelsC !== null ? cToF(feelsC) : hourly[0].temperature,
    high: high.temperature,
    low: low.temperature,
    rain: `${popOf(high)}%`,
    wind: fmtWind(hourly[0].windSpeed, hourly[0].windDirection),
    sky: sky !== null ? `${pyRound(sky)}%` : "?",
    sunset: fmtTime(sunset(today)),
    condition: conditionLine(hourly, today),
  };
}

const statRow = (ll: string, lv: string | number, rl: string, rv: string | number) =>
  `${padR(ll, 5)}${padL(lv, 3)}° ${padR(rl, 4)}${padL(rv, 8)}`;

export function buildTodayGrid(w: Weather): Grid {
  const g = blankGrid();
  setRow(g, 0, "{white}{white} TODAY'S WEATHER {white}{white}", "center");
  setRow(g, 1, w.condition, "center");
  const rows: [string, string | number, string, string | number][] = [
    ["NOW", w.nowTemp, "RAIN", w.rain],
    ["LIKE", w.feels, "WIND", w.wind],
    ["HIGH", w.high, "SKY", w.sky],
    ["LOW", w.low, "SET", w.sunset],
  ];
  rows.forEach((r, i) => setRow(g, 2 + i, statRow(...r)));
  return g;
}

/** 7am-7pm as one colored tile per hour: sun, fog/cloud, or rain. */
export function buildTimelineGrid(w: Weather): Grid {
  const sky = expandLayer(w.raw.skyCover);
  const pops = new Map<number, number>();
  for (const { t, p } of hoursOn(w.hourly, w.today)) pops.set(t.getTime(), popOf(p));
  let tiles = "";
  for (let h = 7; h < 20; h++) {
    const t = zonedTime(w.today.year, w.today.month, w.today.day, h).getTime();
    const skyV = sky.get(t);
    if ((pops.get(t) ?? 0) >= RAIN_THRESHOLD) tiles += "{blue}";
    else if (skyV === undefined || skyV === null || skyV >= 60) tiles += "{white}";
    else tiles += "{yellow}";
  }
  const labels = new Array<string>(22).fill(" "); // 13 tiles centered start at col 4
  labels.splice(4, 2, "7", "A");
  labels.splice(8, 4, "N", "O", "O", "N");
  labels.splice(15, 2, "7", "P");

  const g = blankGrid();
  setRow(g, 0, "TODAY HOUR BY HOUR", "center");
  setRow(g, 1, labels.join(""));
  setRow(g, 2, tiles, "center");
  setRow(g, 4, w.condition, "center");
  setRow(g, 5, "{yellow} SUN {white} FOG {blue} RAIN", "center");
  return g;
}

export function buildForecastGrid(w: Weather): Grid {
  const g = blankGrid();
  setRow(g, 0, "{white} 5 DAY FORECAST {white}", "center");
  const periods = w.daily[0].isDaytime ? w.daily : w.daily.slice(1);
  for (let i = 0; i < 5; i++) {
    if (2 * i + 1 >= periods.length) break;
    const day = periods[2 * i], night = periods[2 * i + 1];
    const prefix = `${fmtWeekday(new Date(day.startTime))} ${padL(day.temperature, 2)}/${padR(night.temperature, 2)} `;
    setRow(g, 1 + i, prefix + condense(day.shortForecast, 22 - prefix.length));
  }
  return g;
}

export function buildTomorrowGrid(w: Weather): Grid {
  const tmrw = addDays(w.today, 1);
  const dailyTmrw = w.daily.filter((p) => sameDate(localDate(new Date(p.startTime)), tmrw));
  const day = dailyTmrw.find((p) => p.isDaytime);
  const night = dailyTmrw.find((p) => !p.isDaytime);
  if (!day || !night) throw new Error("NWS daily forecast has no periods for tomorrow");
  const am = hoursOn(w.hourly, tmrw).find(({ t }) => localParts(t).hour === 8)?.p;

  const g = blankGrid();
  setRow(g, 0, "{white}{white} TOMORROW {white}{white}", "center");
  setRow(g, 1, condense(day.shortForecast, 22), "center");
  const rows: [string, string | number, string, string | number][] = [
    ["AM", am ? am.temperature : night.temperature, "RAIN", `${popOf(day)}%`],
    ["HIGH", day.temperature, "WIND", fmtWind(day.windSpeed, day.windDirection)],
    ["LOW", night.temperature, "SET", fmtTime(sunset(tmrw))],
  ];
  rows.forEach((r, i) => setRow(g, 2 + i, statRow(...r)));
  return g;
}

export function buildRainGrid(w: Weather): Grid | null {
  const todays = hoursOn(w.hourly, w.today);
  const rainy = todays.filter(({ p }) => popOf(p) >= RAIN_THRESHOLD);
  if (rainy.length === 0) return null;
  let peak = todays[0];
  for (const hp of todays) if (popOf(hp.p) > popOf(peak.p)) peak = hp;
  let totalMm = 0;
  for (const v of w.raw.quantitativePrecipitation?.values ?? []) {
    if (sameDate(localDate(new Date(v.validTime.split("/")[0])), w.today)) totalMm += v.value || 0;
  }
  const totalIn = totalMm / 25.4;

  const g = blankGrid();
  setRow(g, 0, "{blue}{blue} RAIN TODAY {blue}{blue}", "center");
  const window = rainy.length >= 10 ? "ON & OFF ALL DAY" : `${fmtHour(rainy[0].t)} - ${fmtHour(rainy[rainy.length - 1].t)}`;
  setRow(g, 2, `RAIN ${window}`, "center");
  setRow(g, 3, `PEAK ${popOf(peak.p)}% AT ${fmtHour(peak.t)}`, "center");
  setRow(g, 4, `TOTAL ${totalIn < 0.05 ? "<0.1" : totalIn.toFixed(1)} IN`, "center");
  return g;
}

const HEAT_LABELS: Record<number, [string, string]> = { 2: ["MODERATE", "orange"], 3: ["MAJOR", "red"], 4: ["EXTREME", "violet"] };

export function buildHeatGrid(w: Weather): Grid | null {
  const todays: number[] = [];
  for (const [ms, v] of expandLayer(w.raw.heatRisk)) {
    if (v !== null && sameDate(localDate(new Date(ms)), w.today)) todays.push(v);
  }
  const risk = todays.length ? pyRound(Math.max(...todays)) : 0;
  if (risk < HEAT_THRESHOLD) return null;
  const [label, tileName] = HEAT_LABELS[Math.min(risk, 4)];
  const t = `{${tileName}}`;
  const g = blankGrid();
  setRow(g, 0, `${t}${t} HEAT ALERT ${t}${t}`, "center");
  setRow(g, 2, `HIGH ${w.high}° TODAY`, "center");
  setRow(g, 3, `HEAT RISK ${label}`, "center");
  setRow(g, 5, `${t} HYDRATE, STAY COOL ${t}`, "center");
  return g;
}

const SEVERITY: Record<string, number> = { Extreme: 0, Severe: 1, Moderate: 2, Minor: 3 };

export function buildAlertsGrid(alerts: any): Grid | null {
  const feats: any[] = alerts?.features ?? [];
  if (feats.length === 0) return null;
  const props = feats.map((f) => f.properties).sort((a, b) => (SEVERITY[a.severity] ?? 4) - (SEVERITY[b.severity] ?? 4));
  const top = props[0];
  const g = blankGrid();
  setRow(g, 0, "{red}{red} NWS ALERT {red}{red}", "center");
  wrap(String(top.event).toUpperCase(), 22, 2).forEach((line, i) => setRow(g, 2 + i, line, "center"));
  const endsS = top.ends || top.expires;
  if (endsS) {
    const ends = new Date(endsS);
    setRow(g, 4, `UNTIL ${fmtWeekday(ends)} ${fmtHour(ends)}`, "center");
  }
  if (props.length > 1) setRow(g, 5, `+${props.length - 1} MORE ALERTS`, "center");
  return g;
}

export function aqiCategory(aqi: number): [string, string, string] {
  if (aqi <= 150) return ["UNHEALTHY (SENSITIVE)", "LIMIT EXERTION", "orange"];
  if (aqi <= 200) return ["UNHEALTHY", "LIMIT OUTDOOR TIME", "red"];
  if (aqi <= 300) return ["VERY UNHEALTHY", "STAY INDOORS", "violet"];
  return ["HAZARDOUS", "STAY INDOORS", "violet"];
}

export function buildAqiGrid(aqi: number): Grid {
  const [category, advice, tile] = aqiCategory(aqi);
  const t = `{${tile}}`;
  const g = blankGrid();
  setRow(g, 0, `${t}${t} AIR QUALITY ${t}${t}`, "center");
  setRow(g, 2, `AQI ${aqi}`, "center");
  setRow(g, 3, category, "center");
  setRow(g, 5, `${t} ${advice} ${t}`, "center");
  return g;
}

const WEATHER_PAGES = new Set(["today", "timeline", "forecast", "tomorrow", "rain", "heat"]);

export async function renderPages(fetchJson: FetchJson, now: Date, names: string[]): Promise<RenderResult> {
  const pages: Page[] = [];
  const skipped: RenderResult["skipped"] = [];
  const w = names.some((n) => WEATHER_PAGES.has(n)) ? await getWeather(fetchJson, now) : null;
  for (const name of names) {
    let grid: Grid | null = null;
    let skip = "";
    switch (name) {
      case "today": grid = buildTodayGrid(w!); break;
      case "timeline": grid = buildTimelineGrid(w!); break;
      case "forecast": grid = buildForecastGrid(w!); break;
      case "tomorrow": grid = buildTomorrowGrid(w!); break;
      case "rain": grid = buildRainGrid(w!); skip = "no rain expected today"; break;
      case "heat": grid = buildHeatGrid(w!); skip = "heat risk is low"; break;
      case "alerts":
        try {
          grid = buildAlertsGrid(await fetchJson(ALERTS_URL, { headers: NWS_HEADERS }));
          skip = "no active NWS alerts for CAZ006";
        } catch (e) {
          skip = `alerts fetch failed (${(e as Error).message})`;
        }
        break;
      case "aqi":
        try {
          const aqi = pyRound((await fetchJson(AQI_URL)).current.us_aqi);
          if (aqi > AQI_THRESHOLD) grid = buildAqiGrid(aqi);
          else skip = `AQI is ${aqi} (<= ${AQI_THRESHOLD})`;
        } catch (e) {
          skip = `AQI fetch failed (${(e as Error).message})`;
        }
        break;
      default:
        throw new Error(`unknown weather page ${JSON.stringify(name)}; choose from ${[...Object.keys(SEQUENCES), ...PAGES].join(", ")}`);
    }
    if (grid) pages.push({ name, grid });
    else skipped.push({ name, reason: skip });
  }
  return { pages, skipped };
}

export const weather: Channel = {
  name: "weather",
  description: "Duboce Triangle weather (page=morning|evening|all|today|timeline|forecast|tomorrow|rain|heat|alerts|aqi)",
  async render(ctx, opts) {
    const page = opts.page ?? "morning";
    const names = SEQUENCES[page] ?? [page];
    return renderPages(ctx.fetchJson, ctx.now, names);
  },
};
