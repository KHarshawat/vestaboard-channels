/** The daily schedule, in Pacific wall-clock time (DST-correct).
 *
 * The cron fires every minute; `slotAt` says what that minute should post.
 * A slot with `at` posts once. A slot with `from`/`until` is a block: the
 * channel's pages are cycled one per minute for the whole block, so the
 * weather block shows every page several times over the half hour.
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
}

export const SCHEDULE: Slot[] = [
  { at: "07:00", channel: "letter" },
  { from: "07:15", until: "07:45", channel: "weather", page: "morning" },
  { at: "08:00", channel: "muni" },
  { at: "08:15", channel: "holidays" },
  { at: "12:00", channel: "holidays" },
  { at: "16:30", channel: "dinner" },
  { at: "17:00", channel: "moon" },
  { at: "20:30", channel: "weather", page: "tomorrow" },
  { at: "20:33", channel: "weather", page: "alerts" },
];

export const toMinutes = (hhmm: string): number => {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
};

export interface Match {
  slot: Slot;
  /** minutes since the block started (0 for `at` slots) */
  offset: number;
}

export function slotAt(hhmm: string, schedule: Slot[] = SCHEDULE): Match | null {
  const t = toMinutes(hhmm);
  for (const slot of schedule) {
    if (slot.at !== undefined && toMinutes(slot.at) === t) return { slot, offset: 0 };
    if (slot.from !== undefined && slot.until !== undefined) {
      const from = toMinutes(slot.from);
      if (t >= from && t < toMinutes(slot.until)) return { slot, offset: t - from };
    }
  }
  return null;
}

export function describe(slot: Slot): string {
  const what = slot.page ? `${slot.channel} (${slot.page})` : slot.channel;
  return slot.at ? `${slot.at}        ${what}` : `${slot.from}-${slot.until}  ${what}, one page per minute`;
}
