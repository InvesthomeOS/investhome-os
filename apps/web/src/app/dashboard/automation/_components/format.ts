export function formatDateTime(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export function formatSuccessRate(
  rate: number | null | undefined,
  available: boolean,
  unavailableLabel: string,
): string {
  if (!available || rate == null) return unavailableLabel;
  return `${rate}%`;
}
