export function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function defaultRange(): { from: string; to: string } {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 29);
  return { from: isoDate(from), to: isoDate(to) };
}

export function parseRange(searchParams: URLSearchParams): {
  from: string;
  to: string;
} {
  const fallback = defaultRange();
  const from = searchParams.get("from") ?? fallback.from;
  const to = searchParams.get("to") ?? fallback.to;
  return { from, to };
}
