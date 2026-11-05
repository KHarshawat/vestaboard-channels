/** Moon phase: lunation math from a reference new moon (no API), traditional
 * full-moon names, and a ( ) illumination bar. */

import { blankGrid, setRow } from "../board/render";
import type { Grid } from "../board/characters";
import { localParts, parseDateKey, zonedTime } from "../time";
import { mod, pyRound } from "../util";
import type { Channel } from "./types";

const LUNATION = 29.530588; // days
const REF_NEW_MOON = Date.UTC(2022, 3, 30, 20, 28);
const BAR_CELLS = 18;
const DAY_MS = 86_400_000;

const PHASE_NAMES = [
  "NEW MOON", "WAXING CRESCENT", "FIRST QUARTER", "WAXING GIBBOUS",
  "FULL MOON", "WANING GIBBOUS", "LAST QUARTER", "WANING CRESCENT",
];

const MOON_NAMES: Record<number, string> = {
  1: "WOLF", 2: "SNOW", 3: "WORM", 4: "PINK", 5: "FLOWER", 6: "STRAWBERRY",
  7: "BUCK", 8: "STURGEON", 9: "HARVEST", 10: "HUNTER'S", 11: "BEAVER", 12: "COLD",
};

function nameOfFull(fullMs: number): string {
  const local = localParts(new Date(fullMs));
  const oneBefore = localParts(new Date(fullMs - LUNATION * DAY_MS));
  if (oneBefore.month === local.month) return "BLUE"; // second full moon of the month
  return MOON_NAMES[local.month];
}

export interface PhaseInfo {
  frac: number;
  name: string;
  illum: number;
  moonName: string;
  nextMoonName: string;
  daysToFull: number;
}

export function phaseInfo(when: Date): PhaseInfo {
  const age = mod((when.getTime() - REF_NEW_MOON) / DAY_MS, LUNATION);
  const frac = age / LUNATION;
  const daysToFull = mod(0.5 - frac, 1) * LUNATION;
  const nextFull = when.getTime() + daysToFull * DAY_MS;
  const prevFull = nextFull - LUNATION * DAY_MS;
  const nearestFull = daysToFull > LUNATION / 2 ? prevFull : nextFull;
  return {
    frac,
    name: PHASE_NAMES[Math.floor(mod(frac * 8 + 0.5, 8))],
    illum: (1 - Math.cos(2 * Math.PI * frac)) / 2,
    moonName: nameOfFull(nearestFull),
    nextMoonName: nameOfFull(nextFull),
    daysToFull,
  };
}

export function countdownLine(moonName: string, days: number, tonight: boolean): string {
  const n = pyRound(days);
  let tails: string[];
  if (tonight) tails = ["MOON TONIGHT", "TONIGHT"];
  else if (n === 1) tails = ["MOON TOMORROW", "TOMORROW"];
  else tails = [`MOON IN ${n} DAYS`, `MOON ${n} DAYS`, `${n} DAYS`];
  for (const tail of tails) {
    const line = `${moonName} ${tail}`;
    if (line.length <= 22) return line;
  }
  return `${moonName} ${n}D`;
}

export function illuminationBar(illum: number, waxing: boolean): string {
  const lit = pyRound(illum * BAR_CELLS);
  const white = "{white}".repeat(lit);
  const dark = " ".repeat(BAR_CELLS - lit);
  return waxing ? `(${white}${dark})` : `(${dark}${white})`;
}

export function buildGrid(when: Date): Grid {
  const p = phaseInfo(when);
  const phase = p.name === "FULL MOON" ? `${p.moonName} MOON` : p.name;
  const g = blankGrid();
  setRow(g, 0, "{white}{white} MOON PHASE {white}{white}", "center");
  setRow(g, 2, phase, "center");
  // The simple lunation model drifts up to ~0.6 days from the true moon,
  // so treat "just past full" generously on the past side.
  const tonight = p.daysToFull > LUNATION - 1.3 || p.daysToFull < 0.75;
  const countdownName = tonight ? p.moonName : p.nextMoonName;
  setRow(g, 3, countdownLine(countdownName, p.daysToFull, tonight), "center");
  setRow(g, 5, illuminationBar(p.illum, p.frac < 0.5), "center");
  return g;
}

export const moon: Channel = {
  name: "moon",
  description: "Moon phase and next full moon",
  async render(ctx, opts) {
    let when = ctx.now;
    if (opts.date) {
      const d = parseDateKey(opts.date);
      when = zonedTime(d.year, d.month, d.day, 18, 0); // 6pm Pacific, like the Python preview
    }
    return { pages: [{ name: phaseInfo(when).name, grid: buildGrid(when) }], skipped: [] };
  },
};
