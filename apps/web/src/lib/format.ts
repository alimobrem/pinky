import { formatDistanceToNow, format, isValid, differenceInHours } from "date-fns";

export function relativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  if (!isValid(date)) return dateStr;
  if (differenceInHours(new Date(), date) < 24) {
    return formatDistanceToNow(date, { addSuffix: true });
  }
  return format(date, "MMM d, yyyy HH:mm");
}

export function shortTime(dateStr: string): string {
  const date = new Date(dateStr);
  if (!isValid(date)) return dateStr;
  return format(date, "HH:mm:ss");
}

export function fullDateTime(dateStr: string): string {
  const date = new Date(dateStr);
  if (!isValid(date)) return dateStr;
  return format(date, "MMM d, yyyy 'at' HH:mm:ss");
}

export function compactNumber(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

export function percentLabel(n: number): string {
  return `${Math.round(n * 100)}%`;
}
