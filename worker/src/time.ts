/** Pacific-time helpers. Workers run in UTC; everything user-facing here is
 * America/Los_Angeles, resolved through Intl so DST is handled correctly. */

export const TZ = "America/Los_Angeles";

export interface LocalParts {
  year: number;
  month: number; // 1-12
  day: number;
  hour: number; // 0-23
  minute: number;
  weekday: number; // 0=Sun .. 6=Sat (JS convention)
  dateKey: string; // "YYYY-MM-DD"
  hhmm: string; // "07:15"
}

const fmtCache = new Map<string, Intl.DateTimeFormat>();
function formatter(tz: string): Intl.DateTimeFormat {
  let f = fmtCache.get(tz);
  if (!f) {
    f = new Intl.DateTimeFormat("en-US", {
      timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", weekday: "short",
    });
    fmtCache.set(tz, f);
  }
  return f;
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function localParts(d: Date, tz: string = TZ): LocalParts {
  const parts: Record<string, string> = {};
  for (const p of formatter(tz).formatToParts(d)) parts[p.type] = p.value;
  const year = Number(parts.year), month = Number(parts.month), day = Number(parts.day);
  const hour = Number(parts.hour) % 24, minute = Number(parts.minute);
  const two = (n: number) => String(n).padStart(2, "0");
  return {
    year, month, day, hour, minute,
    weekday: WEEKDAYS.indexOf(parts.weekday),
    dateKey: `${year}-${two(month)}-${two(day)}`,
    hhmm: `${two(hour)}:${two(minute)}`,
  };
}

/** The instant corresponding to a wall-clock time in tz. */
export function zonedTime(year: number, month: number, day: number, hour = 0, minute = 0, tz: string = TZ): Date {
  const want = Date.UTC(year, month - 1, day, hour, minute);
  let guess = want;
  for (let i = 0; i < 2; i++) {
    const p = localParts(new Date(guess), tz);
    const asUtc = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute);
    guess += want - asUtc;
  }
  return new Date(guess);
}

// ---- civil dates (no time of day) ----------------------------------------

export interface CivilDate { year: number; month: number; day: number }

const DAY_MS = 86_400_000;

export function parseDateKey(key: string): CivilDate {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key);
  if (!m) throw new Error(`bad date ${JSON.stringify(key)}; want YYYY-MM-DD`);
  return { year: Number(m[1]), month: Number(m[2]), day: Number(m[3]) };
}

export function dateKey(d: CivilDate): string {
  const two = (n: number) => String(n).padStart(2, "0");
  return `${d.year}-${two(d.month)}-${two(d.day)}`;
}

export function mmdd(d: CivilDate): string {
  const two = (n: number) => String(n).padStart(2, "0");
  return `${two(d.month)}-${two(d.day)}`;
}

/** Days since 1970-01-01. */
export function epochDays(d: CivilDate): number {
  return Math.round(Date.UTC(d.year, d.month - 1, d.day) / DAY_MS);
}

export function fromEpochDays(n: number): CivilDate {
  const dt = new Date(n * DAY_MS);
  return { year: dt.getUTCFullYear(), month: dt.getUTCMonth() + 1, day: dt.getUTCDate() };
}

export function addDays(d: CivilDate, n: number): CivilDate {
  return fromEpochDays(epochDays(d) + n);
}

/** Python's date.toordinal(): 0001-01-01 is day 1. */
export function pyOrdinal(d: CivilDate): number {
  return epochDays(d) + 719_163;
}

/** Python's date.weekday(): Monday=0 .. Sunday=6. */
export function pyWeekday(d: CivilDate): number {
  return (new Date(Date.UTC(d.year, d.month - 1, d.day)).getUTCDay() + 6) % 7;
}

export function dayOfYear(d: CivilDate): number {
  return epochDays(d) - epochDays({ year: d.year, month: 1, day: 1 }) + 1;
}

export function sameDate(a: CivilDate, b: CivilDate): boolean {
  return a.year === b.year && a.month === b.month && a.day === b.day;
}

export function localDate(d: Date, tz: string = TZ): CivilDate {
  const p = localParts(d, tz);
  return { year: p.year, month: p.month, day: p.day };
}

// ---- formatting -----------------------------------------------------------

const SHORT_DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

/** "5:09PM" in Pacific time. */
export function fmtTime(d: Date, tz: string = TZ): string {
  const p = localParts(d, tz);
  const h = p.hour % 12 || 12;
  return `${h}:${String(p.minute).padStart(2, "0")}${p.hour >= 12 ? "PM" : "AM"}`;
}

/** "5PM" in Pacific time. */
export function fmtHour(d: Date, tz: string = TZ): string {
  const p = localParts(d, tz);
  const h = p.hour % 12 || 12;
  return `${h}${p.hour >= 12 ? "PM" : "AM"}`;
}

/** "WED" in Pacific time (Python strftime('%a').upper()). */
export function fmtWeekday(d: Date, tz: string = TZ): string {
  return SHORT_DAYS[localParts(d, tz).weekday];
}
