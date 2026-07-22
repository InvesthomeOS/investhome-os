/**
 * Localized CRM enum / activity label helpers.
 * Backend values stay unchanged; UI always resolves through next-intl catalogs.
 */

type TranslateFn = {
  (key: string): string;
  has?: (key: string) => boolean;
};

/** Resolve a leaf key under a translator namespace, with safe fallback. */
export function crmLabel(t: TranslateFn, value: string | null | undefined, fallback?: string): string {
  if (!value) return fallback ?? '';
  if (typeof t.has === 'function' && t.has(value)) {
    return t(value);
  }
  try {
    const label = t(value);
    // next-intl may return the key path when missing depending on config
    if (!label || label === value || label.endsWith(`.${value}`)) {
      return fallback ?? humanizeEnum(value);
    }
    return label;
  } catch {
    return fallback ?? humanizeEnum(value);
  }
}

/** Localize activity.description_key values such as activity.lead.created */
export function crmActivityEventLabel(
  tEvents: TranslateFn,
  descriptionKey: string | null | undefined,
): string {
  if (!descriptionKey) return crmLabel(tEvents, 'unknown');
  const normalized = descriptionKey.startsWith('activity.')
    ? descriptionKey.slice('activity.'.length)
    : descriptionKey;
  const dotted = normalized.replace(/\//g, '.');
  if (typeof tEvents.has === 'function') {
    if (tEvents.has(dotted)) return tEvents(dotted);
    if (tEvents.has(normalized)) return tEvents(normalized);
    return tEvents('unknown');
  }
  try {
    return tEvents(dotted);
  } catch {
    try {
      return tEvents('unknown');
    } catch {
      return humanizeEnum(dotted);
    }
  }
}

function humanizeEnum(value: string): string {
  return value
    .replace(/^activity\./, '')
    .split(/[._]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}
