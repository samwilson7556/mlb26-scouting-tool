export function parseGameDate(value: string | null | undefined): Date | null {
  if (!value) {
    return null;
  }

  const trimmed = value.trim();

  if (!trimmed) {
    return null;
  }

  const normalized = trimmed.includes("T")
    ? trimmed
    : trimmed.replace(" ", "T");

  const alreadyHasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(normalized);

  const date = new Date(alreadyHasTimezone ? normalized : `${normalized}Z`);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date;
}

export function getGameDateSortValue(value: string | null | undefined): number {
  const date = parseGameDate(value);
  return date ? date.getTime() : 0;
}

export function formatGameDateTime(value: string | null | undefined): string {
  const date = parseGameDate(value);

  if (!date) {
    return value || "N/A";
  }

  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

export function formatGameDateOnly(value: string | null | undefined): string {
  const date = parseGameDate(value);

  if (!date) {
    return value || "N/A";
  }

  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}