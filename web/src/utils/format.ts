export function formatNumber(value: number | null | undefined): string {
  return typeof value === "number" ? new Intl.NumberFormat("de-DE").format(value) : "0";
}

export function formatBoolean(value: boolean | null | undefined): string {
  return value ? "Ja" : "Nein";
}

export function summarizeObject(value: Record<string, unknown>): string {
  const entries = Object.entries(value);
  if (entries.length === 0) {
    return "Keine Daten";
  }
  return entries
    .slice(0, 6)
    .map(([key, item]) => `${key}: ${String(item)}`)
    .join("\n");
}
