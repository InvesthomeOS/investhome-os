/** Strip the marketing namespace prefix from API-provided label keys. */
export function marketingLabelKey(labelKey: string): string {
  return labelKey.startsWith('marketing.') ? labelKey.slice('marketing.'.length) : labelKey;
}

type TranslateFn = {
  (key: string): string;
  has?: (key: string) => boolean;
};

function hasKey(t: TranslateFn, key: string): boolean {
  if (typeof t.has === 'function') {
    return t.has(key);
  }
  try {
    const value = t(key);
    return typeof value === 'string' && value.length > 0 && value !== key;
  } catch {
    return false;
  }
}

/**
 * Resolve an API metric/stage/health key to a localized label.
 * Prefers `metricLabels.<key>` under the provided translator (typically `marketing.analytics`).
 * Never returns a raw English API label when a translation exists.
 */
export function resolveMarketingMetricLabel(
  t: TranslateFn,
  key: string | null | undefined,
  apiLabel?: string | null,
): string {
  if (!key) {
    return apiLabel?.trim() || '';
  }
  const metricKey = `metricLabels.${key}`;
  if (hasKey(t, metricKey)) {
    return t(metricKey);
  }
  const funnelKey = `funnelStages.${key}`;
  if (hasKey(t, funnelKey)) {
    return t(funnelKey);
  }
  // Last resort: humanize the key (not the English API label) so Turkish mode
  // does not surface backend English strings for unknown keys.
  return key.replace(/_/g, ' ');
}
