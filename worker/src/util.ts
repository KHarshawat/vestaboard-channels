/** Python's round(): half-to-even, so ported math matches the Python channels exactly. */
export function pyRound(x: number): number {
  const f = Math.floor(x);
  const diff = x - f;
  if (diff > 0.5) return f + 1;
  if (diff < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}

export const mod = (a: number, n: number) => ((a % n) + n) % n;
