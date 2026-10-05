/** Map stored lead source codes to the leads.sources i18n catalog key. */

const KNOWN_SOURCE_KEYS = new Set([
  'website',
  'referral',
  'exhibition',
  'linkedin',
  'partner',
  'cold_outreach',
]);

const SOURCE_ALIASES: Record<string, string> = {
  website: 'website',
  web_site_form: 'website',
  website_form: 'website',
};

export function leadSourceCatalogKey(source: string | null | undefined): string | null {
  if (!source?.trim()) return null;
  const normalized = source.trim().toLowerCase().replace(/[\s-]+/g, '_');
  const aliased = SOURCE_ALIASES[normalized] ?? normalized;
  return KNOWN_SOURCE_KEYS.has(aliased) ? aliased : null;
}
