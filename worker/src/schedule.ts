/** The daily schedule, in Pacific wall-clock time (DST-correct).
 *
 * The cron fires every minute; `slotAt` says what that minute should post.
 * A slot with `at` posts once. A slot with `from`/`until` is a block: the
 * channel is re-rendered every `every` minutes (default 1) and its pages
 * cycled one per step, so the weather block shows every page a few times
 * over the half hour and the muni block keeps its arrival times live.
 */

export interface Slot {
  channel: string;
  page?: string;
  /** post once at this time ("HH:MM") */
  at?: string;
  /** block start, inclusive ("HH:MM") */
  from?: string;
  /** block end, exclusive ("HH:MM") */
  until?: string;
  /** minutes between posts within a block (default 1) */
  every?: number;
}

export const SCHEDULE: Slot[] = [
  { at: "07:00", channel: "letter" },
  { from: "07:15", until: "07:45", channel: "weather", page: "morning", every: 5 },
  { from: "08:00", until: "08:15", channel: "muni" },
  { at: "08:15", channel: "holidays" },
  { at: "12:00", channel: "holidays" },
  { at: "16:30", channel: "dinner" },
  { at: "17:30", channel: "moon" },
  { at: "20:00", channel: "weather", page: "tomorrow" },
  { at: "20:03", channel: "weather", page: "alerts" },
];

export const toMinutes = (hhmm: string): number => {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
};

export interface Match {
  slot: Slot;
  /** minutes since the block started (0 for `at` slots) */
  offset: number;
  /** which post of the block this is: offset / every (0 for `at` slots) */
  step: number;
}

export function slotAt(hhmm: string, schedule: Slot[] = SCHEDULE): Match | null {
  const t = toMinutes(hhmm);
  for (const slot of schedule) {
    if (slot.at !== undefined && toMinutes(slot.at) === t) return { slot, offset: 0, step: 0 };
    if (slot.from !== undefined && slot.until !== undefined) {
      const from = toMinutes(slot.from);
      const every = slot.every ?? 1;
      if (t >= from && t < toMinutes(slot.until)) {
        const offset = t - from;
        if (offset % every !== 0) return null; // between posts of this block
        return { slot, offset, step: offset / every };
      }
    }
  }
  return null;
}

export function describe(slot: Slot): string {
  const what = slot.page ? `${slot.channel} (${slot.page})` : slot.channel;
  const every = slot.every ?? 1;
  const cadence = every === 1 ? "every minute" : `every ${every} min`;
  return slot.at ? `${slot.at}        ${what}` : `${slot.from}-${slot.until}  ${what}, ${cadence}`;
}
