export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let v = bytes / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v < 10 ? 1 : 0)} ${units[i]}`;
}

const nf = new Intl.NumberFormat("en-US");
export const formatNumber = (n: number | null | undefined): string =>
  n === null || n === undefined ? "—" : nf.format(n);

export function formatStat(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  if (Number.isInteger(n)) return nf.format(n);
  const abs = Math.abs(n);
  return abs >= 1000
    ? nf.format(Math.round(n))
    : n.toPrecision(abs < 1 ? 3 : 4).replace(/\.?0+$/, "");
}

export function formatPct(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined) return "—";
  return `${n.toFixed(digits).replace(/\.0+$/, "")}%`;
}

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
export function timeAgo(iso: string, now: number = Date.now()): string {
  const diff = (new Date(iso).getTime() - now) / 1000;
  const steps: [number, Intl.RelativeTimeFormatUnit][] = [
    [60, "second"],
    [60, "minute"],
    [24, "hour"],
    [7, "day"],
    [4.35, "week"],
    [12, "month"],
    [Infinity, "year"],
  ];
  let value = diff;
  for (const [size, unit] of steps) {
    if (Math.abs(value) < size) return rtf.format(Math.round(value), unit);
    value /= size;
  }
  return "";
}

export function duration(start: string | null, end: string | null): string {
  if (!start || !end) return "—";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms} ms`;
  const s = ms / 1000;
  return s < 60 ? `${s.toFixed(1)} s` : `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

export function cellText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** Score -> tone used for badges/rings. */
export function scoreTone(score: number | null | undefined): "good" | "warn" | "bad" | "none" {
  if (score === null || score === undefined) return "none";
  if (score >= 95) return "good";
  if (score >= 80) return "warn";
  return "bad";
}
