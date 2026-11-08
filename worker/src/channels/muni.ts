/** SF Muni arrivals (N Judah at Duboce Park) from the 511.org StopMonitoring API. */

import type { Grid } from "../board/characters";
import { blankGrid, padL, padR, setRow } from "../board/render";
import { localParts } from "../time";
import { pyRound } from "../util";
import type { Channel, FetchJson } from "./types";

const STOPS: [string, string][] = [["EAST", "17318"], ["WEST", "17252"]];
const MAX_ARRIVALS = 3;

export type Arrivals = { line: string | null; mins: number[] };

async function fetchVisits(fetchJson: FetchJson, stop: string, key: string): Promise<any[]> {
  const url = `https://api.511.org/transit/StopMonitoring?format=json&agency=SF&stopCode=${stop}&api_key=${key}`;
  const data = await fetchJson(url);
  return data.ServiceDelivery.StopMonitoringDelivery.MonitoredStopVisit ?? [];
}

export function arrivals(visits: any[], now: Date): Arrivals {
  let line: string | null = null;
  const mins: number[] = [];
  for (const visit of visits) {
    const journey = visit.MonitoredVehicleJourney;
    if (line === null && journey.LineRef) {
      const name = String(journey.PublishedLineName ?? "").trim();
      line = `${journey.LineRef} ${name}`.trim().toUpperCase();
    }
    const call = journey.MonitoredCall ?? {};
    const whenS = call.ExpectedArrivalTime || call.AimedArrivalTime;
    if (!whenS) continue;
    const minutes = (new Date(whenS).getTime() - now.getTime()) / 60_000;
    if (minutes >= -1 && minutes < 90) mins.push(Math.max(0, pyRound(minutes)));
  }
  return { line, mins: mins.sort((a, b) => a - b).slice(0, MAX_ARRIVALS) };
}

export function timesText(mins: number[]): string {
  if (mins.length === 0) return "NO ARRIVALS";
  const parts = mins.map((m) => (m === 0 ? "DUE" : String(m)));
  return mins.some((m) => m > 0) ? `${parts.join(", ")} MIN` : "DUE";
}

/** Muni Metro line colors, by LineRef; buses and unknown lines get white. */
const LINE_COLORS: Record<string, string> = { J: "orange", K: "blue", L: "violet", M: "green", N: "blue", T: "red" };

export function lineColor(line: string | null): string {
  return LINE_COLORS[(line ?? "").split(" ")[0]] ?? "white";
}

export function buildGrid(east: Arrivals, west: Arrivals, now: Date): Grid {
  const line = east.line || west.line || "MUNI";
  const c = `{${lineColor(line)}}`;
  let header = `${c}${c} ${line} ${c}${c}`;
  if (line.length + 8 > 22) header = `${c} ${line} ${c}`;
  const g = blankGrid();
  setRow(g, 0, header, "center");
  setRow(g, 2, `${padR("EAST", 5)}${padL(timesText(east.mins), 17)}`);
  setRow(g, 3, `${padR("WEST", 5)}${padL(timesText(west.mins), 17)}`);
  const p = localParts(now);
  const h = p.hour % 12 || 12;
  setRow(g, 5, `AS OF ${h}:${String(p.minute).padStart(2, "0")}${p.hour >= 12 ? "PM" : "AM"}`, "center");
  return g;
}

export const muni: Channel = {
  name: "muni",
  description: "N Judah arrivals at Duboce Park",
  async render(ctx) {
    const key = ctx.env.TRANSIT_511_API_KEY;
    if (!key) throw new Error("TRANSIT_511_API_KEY secret is not set (get one at https://511.org/open-data/token)");
    const [east, west] = await Promise.all(
      STOPS.map(async ([, stop]) => arrivals(await fetchVisits(ctx.fetchJson, stop, key), ctx.now)),
    );
    const label = `EAST ${timesText(east.mins)} / WEST ${timesText(west.mins)}`;
    return { pages: [{ name: label, grid: buildGrid(east, west, ctx.now) }], skipped: [] };
  },
};
