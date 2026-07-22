export type ChartNumberFormat = 'number' | 'currency' | 'percent' | 'compact';

export function resolveLocale(locale: string | undefined): string {
  if (!locale) return 'tr-TR';
  if (locale.startsWith('en')) return 'en-US';
  if (locale.startsWith('tr')) return 'tr-TR';
  return locale;
}

export function formatChartValue(
  value: number,
  format: ChartNumberFormat = 'number',
  locale = 'tr',
  currency = 'TRY',
): string {
  const resolved = resolveLocale(locale);
  switch (format) {
    case 'currency':
      return new Intl.NumberFormat(resolved, {
        style: 'currency',
        currency,
        maximumFractionDigits: 0,
      }).format(value);
    case 'percent':
      return new Intl.NumberFormat(resolved, {
        style: 'percent',
        maximumFractionDigits: 1,
      }).format(value > 1 ? value / 100 : value);
    case 'compact':
      return new Intl.NumberFormat(resolved, {
        notation: 'compact',
        maximumFractionDigits: 1,
      }).format(value);
    default:
      return new Intl.NumberFormat(resolved, { maximumFractionDigits: 1 }).format(value);
  }
}

export function formatChartDate(value: string | Date, locale = 'tr'): string {
  const date = typeof value === 'string' ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(resolveLocale(locale), {
    month: 'short',
    day: 'numeric',
  }).format(date);
}

/** Brand-aligned chart palette — no random colors */
export const DS_CHART_COLORS = [
  'var(--brand-primary)',
  'var(--brand-secondary)',
  'var(--brand-accent)',
  'var(--status-info)',
  'var(--status-success)',
  'var(--status-warning)',
  '#8B7355',
  '#5C6B73',
] as const;

export const DS_CHART_PRIMARY = 'var(--brand-primary)';

export function chartColorAt(index: number): string {
  return DS_CHART_COLORS[index % DS_CHART_COLORS.length] ?? DS_CHART_PRIMARY;
}
