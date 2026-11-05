/** Every grid here was produced by the Python channels (gen_parity.py);
 * the TypeScript port must match them cell for cell. */

import { describe, expect, it } from "vitest";
import { encode, wrap } from "../src/board/render";
import * as letter from "../src/channels/letter";
import * as holidays from "../src/channels/holidays";
import * as moon from "../src/channels/moon";
import * as dinner from "../src/channels/dinner";
import * as muni from "../src/channels/muni";
import * as weather from "../src/channels/weather";
import { parseDateKey, zonedTime } from "../src/time";
import parity from "./fixtures/parity.json";

describe("render helpers", () => {
  it("encode matches Python", () => {
    for (const [text, codes] of Object.entries(parity.encode)) expect(encode(text)).toEqual(codes);
  });
  it("wrap matches Python", () => {
    for (const c of parity.wrap) expect(wrap(c.text, c.width, c.max_lines)).toEqual(c.lines);
  });
});

describe("letter of the day", () => {
  it("matches Python for 58 dates", () => {
    for (const c of parity.letter) {
      const d = parseDateKey(c.date);
      expect(letter.letterFor(d), c.date).toBe(c.letter);
      expect(letter.buildGrid(d), c.date).toEqual(c.grid);
    }
  });
});

describe("fun holidays", () => {
  it("matches Python for every day of 2026 plus floating spot checks", () => {
    for (const c of parity.holidays) {
      const d = parseDateKey(c.date);
      expect(holidays.holidaysFor(d), c.date).toEqual(c.names);
      if (c.grid) expect(holidays.buildGrid(d), c.date).toEqual(c.grid);
    }
  });
});

describe("moon phase", () => {
  it("matches Python every 2 days through Feb 2027 and at exact instants", () => {
    for (const c of parity.moon) {
      const when = "date" in c && c.date
        ? (() => { const d = parseDateKey(c.date); return zonedTime(d.year, d.month, d.day, 18); })()
        : new Date((c as { instant: string }).instant);
      expect(moon.buildGrid(when), JSON.stringify(c)).toEqual(c.grid);
    }
  });
});

describe("dinner", () => {
  it("matches Python layouts", () => {
    for (const c of parity.dinner) expect(dinner.buildGrid(c.meal), c.meal).toEqual(c.grid);
  });
});

describe("muni", () => {
  it("matches Python arrivals and grid", () => {
    for (const c of parity.muni) {
      const now = new Date(c.now);
      const east = muni.arrivals(c.east_visits, now);
      const west = muni.arrivals(c.west_visits, now);
      expect([east.line, east.mins], c.name).toEqual(c.east);
      expect([west.line, west.mins], c.name).toEqual(c.west);
      expect(muni.buildGrid(east, west, now), c.name).toEqual(c.grid);
    }
  });
});

describe("weather", () => {
  it("sunset matches the Python NOAA port to the minute", () => {
    for (const c of parity.sunset) {
      const got = weather.sunset(parseDateKey(c.date)).getTime();
      expect(Math.abs(got - new Date(c.iso).getTime()), c.date).toBeLessThan(1500);
    }
  });

  for (const scenario of parity.weather) {
    it(`${scenario.name}: every page matches Python`, async () => {
      const responses = scenario.fixture.responses as Record<string, unknown>;
      const fetchJson = async (url: string) => {
        if (!(url in responses)) throw new Error(`unexpected fetch ${url}`);
        return JSON.parse(JSON.stringify(responses[url]));
      };
      const now = new Date(scenario.fixture.now);
      const result = await weather.renderPages(fetchJson, now, weather.PAGES);
      const got: Record<string, unknown> = {};
      for (const p of result.pages) got[p.name] = p.grid;
      for (const s of result.skipped) got[s.name] = null;
      expect(got).toEqual(scenario.pages);
    });
  }

  it("morning sequence skips conditional pages cleanly on a calm day", async () => {
    const scenario = parity.weather[0];
    const responses = scenario.fixture.responses as Record<string, unknown>;
    const result = await weather.renderPages(async (u) => responses[u], new Date(scenario.fixture.now), weather.SEQUENCES.morning);
    expect(result.pages.map((p) => p.name)).toEqual(["today", "timeline", "forecast"]);
    expect(result.skipped.map((s) => s.name)).toEqual(["rain", "heat", "alerts", "aqi"]);
  });
});
