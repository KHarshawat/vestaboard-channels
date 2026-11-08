import { describe, expect, it } from "vitest";
import { SCHEDULE, slotAt } from "../src/schedule";
import { localParts, zonedTime } from "../src/time";

describe("schedule", () => {
  it("posts the letter at 7:00 and nothing at 7:01", () => {
    expect(slotAt("07:00")?.slot.channel).toBe("letter");
    expect(slotAt("07:01")).toBeNull();
  });

  it("refreshes muni every minute from 8:00 until holidays at 8:15", () => {
    expect(slotAt("08:00")?.slot.channel).toBe("muni");
    expect(slotAt("08:14")?.slot.channel).toBe("muni");
    expect(slotAt("08:15")?.slot.channel).toBe("holidays");
  });

  it("cycles weather pages every 5 minutes from 7:15 until 7:45", () => {
    expect(slotAt("07:14")).toBeNull();
    expect(slotAt("07:15")).toEqual({ slot: SCHEDULE[1], offset: 0, step: 0 });
    expect(slotAt("07:16")).toBeNull(); // between posts
    expect(slotAt("07:20")).toEqual({ slot: SCHEDULE[1], offset: 5, step: 1 });
    expect(slotAt("07:40")?.step).toBe(5);
    expect(slotAt("07:44")).toBeNull();
    expect(slotAt("07:45")).toBeNull();
  });

  it("has no overlapping slots across the whole day", () => {
    const seen = new Map<string, string>();
    for (let m = 0; m < 24 * 60; m++) {
      const hhmm = `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
      const hits = SCHEDULE.filter((s) =>
        s.at === hhmm || (s.from && s.until && hhmm >= s.from && hhmm < s.until));
      expect(hits.length, hhmm).toBeLessThanOrEqual(1);
      if (slotAt(hhmm)) seen.set(hhmm, hits[0].channel);
    }
    expect(seen.size).toBe(7 + 6 + 15); // 7 single posts + 6 weather posts + 15 muni minutes
  });
});

describe("Pacific time", () => {
  it("maps the cron's UTC instant to Pacific wall-clock in both PST and PDT", () => {
    expect(localParts(new Date("2026-11-05T15:00:00Z")).hhmm).toBe("07:00"); // PST
    expect(localParts(new Date("2026-07-14T14:00:00Z")).hhmm).toBe("07:00"); // PDT
    expect(localParts(new Date("2026-11-05T08:00:00Z")).dateKey).toBe("2026-11-05");
    expect(localParts(new Date("2026-11-05T07:59:00Z")).dateKey).toBe("2026-11-04");
  });

  it("zonedTime round-trips across the DST change", () => {
    expect(zonedTime(2026, 3, 8, 7, 0).toISOString()).toBe("2026-03-08T14:00:00.000Z"); // DST started at 2am
    expect(zonedTime(2026, 3, 7, 7, 0).toISOString()).toBe("2026-03-07T15:00:00.000Z");
    expect(zonedTime(2026, 11, 1, 7, 0).toISOString()).toBe("2026-11-01T15:00:00.000Z"); // day DST ends
  });
});
