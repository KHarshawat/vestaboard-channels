/** Fun Holidays: funny, random & weird holidays, every day. Data lives in
 * holidays-data.json (exported from the Python channel). */

import { CHAR_TO_CODE } from "../board/characters";
import type { Grid } from "../board/characters";
import { blankGrid, setRow, wrap } from "../board/render";
import {
  addDays, dayOfYear, epochDays, localDate, mmdd, parseDateKey, pyWeekday, sameDate, type CivilDate,
} from "../time";
import DATA from "./holidays-data.json";
import { mod } from "../util";
import type { Channel } from "./types";

const FIXED = DATA.fixed as Record<string, string[]>;
// [month, weekday (Mon=0), n (negative = from end), name]
const FLOATING = DATA.floating as [number, number, number, string][];
const PALETTE = ["red", "orange", "yellow", "green", "blue", "violet"];

/** Gregorian Easter (anonymous computus). */
export function easter(year: number): CivilDate {
  const a = year % 19, b = Math.floor(year / 100), c = year % 100;
  const d = Math.floor(b / 4), e = b % 4;
  const g = Math.floor((8 * b + 13) / 25);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4), k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 19 * l) / 433);
  const month = Math.floor((h + l - 7 * m + 90) / 25);
  const day = (h + l - 7 * m + 33 * month + 19) % 32;
  return { year, month, day };
}

export function nthWeekday(year: number, month: number, weekday: number, n: number): CivilDate {
  if (n > 0) {
    const first = { year, month, day: 1 };
    return addDays(first, mod(weekday - pyWeekday(first), 7) + 7 * (n - 1));
  }
  const next = { year: year + (month === 12 ? 1 : 0), month: (month % 12) + 1, day: 1 };
  const last = addDays(next, -1);
  return addDays(last, -mod(pyWeekday(last) - weekday, 7));
}

export function floatingFor(day: CivilDate): string[] {
  const names: string[] = [];
  for (const [month, weekday, n, name] of FLOATING) {
    if (day.month === month && sameDate(day, nthWeekday(day.year, month, weekday, n))) names.push(name);
  }
  const memorial = nthWeekday(day.year, 5, 0, -1); // last Monday in May
  if (sameDate(day, addDays(memorial, -1))) names.push("National Family Fun Day");
  const thanksgiving = nthWeekday(day.year, 11, 3, 4); // 4th Thursday in November
  if (sameDate(day, addDays(thanksgiving, 5))) names.push("Giving Tuesday");
  if (sameDate(day, addDays(thanksgiving, 1))) names.push("Sinkie Day");
  const delta = epochDays(easter(day.year)) - epochDays(day);
  if (delta === 52) names.push("Fat Thursday");
  else if (delta === 47) names.push("Shrove Tuesday (Pancake Day)");
  else if (delta === 44) names.push("Friday Fish Fry Day"); // first Friday of Lent
  return names;
}

/** Fold accents and smart quotes down to the board's character set. */
export function clean(text: string): string {
  const folded = text.replace(/[’‘]/g, "'").normalize("NFKD").replace(/\p{M}/gu, "");
  return [...folded.toUpperCase()].filter((c) => CHAR_TO_CODE.has(c)).join("");
}

export function holidaysFor(day: CivilDate): string[] {
  return [...(FIXED[mmdd(day)] ?? []), ...floatingFor(day)];
}

export function buildGrid(day: CivilDate): Grid {
  const doy = dayOfYear(day);
  const c1 = `{${PALETTE[doy % 6]}}`;
  const c2 = `{${PALETTE[(doy + 3) % 6]}}`;
  const g = blankGrid();
  setRow(g, 0, `${c1}${c2} TODAY IS ${c1}${c2}`, "center");
  const options = holidaysFor(day);
  const confetti = `${c1} ${c2} ${c1} ${c2} ${c1} ${c2}`;

  if (options.length === 1) {
    const lines = wrap(clean(options[0]), 22, 3);
    const first = 3 - Math.floor((lines.length - 1) / 2);
    lines.forEach((line, i) => setRow(g, first + i, line, "center"));
    setRow(g, 5, confetti, "center");
    return g;
  }

  // Several holidays: list as many as fully fit (shortest first packs the
  // most in), each bulleted with an alternating color tile.
  const entries = options.map((h) => wrap(clean(h), 20, 4)).sort((a, b) => a.length - b.length);
  const packed: string[][] = [];
  let rowsLeft = 5;
  for (const lines of entries) {
    if (lines.length <= rowsLeft) {
      packed.push(lines);
      rowsLeft -= lines.length;
    }
  }
  const used = 5 - rowsLeft;
  let row = used === 5 ? 1 : 1 + Math.floor((4 - used) / 2);
  packed.forEach((lines, i) => {
    const bullet = i % 2 === 0 ? c1 : c2;
    lines.forEach((line, j) => {
      setRow(g, row, j === 0 ? `${bullet} ${line}` : line, "center");
      row += 1;
    });
  });
  if (used <= 4) setRow(g, 5, confetti, "center");
  return g;
}

export const holidays: Channel = {
  name: "holidays",
  description: "Today's fun holidays",
  async render(ctx, opts) {
    const day = opts.date ? parseDateKey(opts.date) : localDate(ctx.now);
    const list = holidaysFor(day);
    if (list.length === 0) return { pages: [], skipped: [{ name: "holidays", reason: `no fun holiday listed for ${mmdd(day)}` }] };
    return { pages: [{ name: list.join(", "), grid: buildGrid(day) }], skipped: [] };
  },
};
