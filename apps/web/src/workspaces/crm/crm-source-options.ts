/** Canonical Geliş Kaynağı values shared by Contact, Lead, Agreement, and Acente forms. */

export const CRM_SOURCE_OPTIONS = [
  { value: 'instagram', label: 'Instagram' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'website', label: 'Website' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'google_ads', label: 'Google Ads' },
  { value: 'agency', label: 'Acente' },
  { value: 'referral', label: 'Referans' },
  { value: 'phone', label: 'Telefon' },
  { value: 'event', label: 'Etkinlik' },
  { value: 'manual', label: 'Manuel' },
  { value: 'other', label: 'Diğer' },
  { value: 'bitrix', label: 'Bitrix' },
] as const;

export type CrmSourceValue = (typeof CRM_SOURCE_OPTIONS)[number]['value'];

const SOURCE_ALIASES: Record<string, CrmSourceValue> = {
  instagram: 'instagram',
  'instagram lead': 'instagram',
  facebook: 'facebook',
  'facebook lead': 'facebook',
  meta: 'facebook',
  website: 'website',
  web: 'website',
  'web sitesi': 'website',
  whatsapp: 'whatsapp',
  wa: 'whatsapp',
  'google ads': 'google_ads',
  google: 'google_ads',
  google_ads: 'google_ads',
  agency: 'agency',
  acente: 'agency',
  acenta: 'agency',
  referral: 'referral',
  referans: 'referral',
  phone: 'phone',
  telefon: 'phone',
  event: 'event',
  etkinlik: 'event',
  manual: 'manual',
  manuel: 'manual',
  other: 'other',
  diğer: 'other',
  diger: 'other',
  bitrix: 'bitrix',
};

export function canonicalCrmSource(value: string | null | undefined): string {
  const raw = (value || '').trim();
  if (!raw) return '';
  return SOURCE_ALIASES[raw.toLocaleLowerCase('tr')] || raw;
}

export function crmSourceLabel(value: string | null | undefined): string {
  const raw = (value || '').trim();
  if (!raw) return '';
  const canonical = canonicalCrmSource(raw);
  return CRM_SOURCE_OPTIONS.find((item) => item.value === canonical)?.label || raw;
}

export function crmSourceChoices(current?: string | null): Array<{ value: string; label: string }> {
  const options: Array<{ value: string; label: string }> = CRM_SOURCE_OPTIONS.map((item) => ({
    value: item.value,
    label: item.label,
  }));
  const raw = (current || '').trim();
  if (!raw) return options;
  const canonical = canonicalCrmSource(raw);
  if (!options.some((item) => item.value === canonical || item.value === raw)) {
    options.push({ value: raw, label: raw });
  }
  return options;
}

export const CRM_PRIMARY_ROLES = [
  { value: 'prospect', label: 'Aday' },
  { value: 'buyer', label: 'Alıcı' },
  { value: 'investor', label: 'Yatırımcı' },
  { value: 'broker', label: 'Acente' },
  { value: 'partner', label: 'İş Ortağı' },
  { value: 'internal_team', label: 'İç Ekip' },
] as const;

export const AGREEMENT_STAGE_OPTIONS = [
  { value: 'Kimlik Bilgileri', label: 'Kimlik Bilgileri Süreci' },
  { value: 'Satış Sözleşmesi', label: 'Satış Sözleşmesi Süreci' },
  { value: 'Docusign', label: 'DocuSign' },
  { value: 'Para Transferi', label: 'Para Transfer Süreci' },
  { value: 'Ev Teslim Süreci', label: 'Ev Teslim Süreci' },
] as const;

export function agreementStageLabel(stage: string | null | undefined): string {
  const raw = (stage || '').trim();
  if (!raw) return '—';
  return AGREEMENT_STAGE_OPTIONS.find((item) => item.value === raw || item.label === raw)?.label || raw;
}

export const CRM_PROJECT_OPTIONS = [
  { id: '1812_h_pl', label: '1812 H Place' },
  { id: 'uniloft', label: 'Uniloft' },
  { id: '1313_penn', label: '1313 Penn' },
  { id: '1307_k_st', label: '1307 K' },
  { id: '2319_ontario', label: '2319 Ontario' },
  { id: 'reit', label: 'REIT' },
  { id: 'the_temple', label: 'The Temple' },
] as const;
