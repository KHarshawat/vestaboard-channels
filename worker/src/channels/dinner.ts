/** Dinner menu: tonight's meal from menu.json (repo root, ISO date -> meal). */

import { blankGrid, setRow, wrap } from "../board/render";
import type { Grid } from "../board/characters";
import { dateKey, localDate, parseDateKey } from "../time";
import MENU from "../../../menu.json";
import type { Channel } from "./types";

export function mealFor(key: string): string | undefined {
  return (MENU as Record<string, string>)[key];
}

export function buildGrid(meal: string): Grid {
  const g = blankGrid();
  setRow(g, 0, "{orange}{orange} TONIGHT'S DINNER {orange}{orange}");
  const lines = wrap(meal.toUpperCase(), 22, 3);
  const first = 3 - Math.floor((lines.length - 1) / 2); // 1 line -> row 3, 2 -> 3-4, 3 -> 2-4
  lines.forEach((line, i) => setRow(g, first + i, line, "center"));
  return g;
}

export const dinner: Channel = {
  name: "dinner",
  description: "Tonight's dinner from menu.json",
  async render(ctx, opts) {
    const key = opts.date ? dateKey(parseDateKey(opts.date)) : dateKey(localDate(ctx.now));
    const meal = mealFor(key);
    if (!meal) return { pages: [], skipped: [{ name: "dinner", reason: `no menu set for ${key}` }] };
    return { pages: [{ name: meal, grid: buildGrid(meal) }], skipped: [] };
  },
};
