import type { CrmAgreementSummary } from '@/workspaces/crm/api/agreements';

export const PROJECT_SELECTOR = [
  { id: '1812_h_pl', label: '1812 H Place' },
  { id: 'uniloft', label: 'Uniloft' },
  { id: '1313_penn', label: '1313 Penn' },
  { id: '1307_k_st', label: '1307 K' },
  { id: '2319_ontario', label: '2319 Ontario' },
  { id: 'reit', label: 'REIT' },
  { id: 'the_temple', label: 'The Temple' },
] as const;

const PREFERRED_COLUMNS = [
  'Kimlik Bilgileri',
  'Satış Sözleşmesi',
  'Docusign',
  'Para Transferi',
  'Ev Teslim Süreci',
  'Tapu Teslim Süreci',
  'Kazanıldı',
  'Kapital Kazançlar',
] as const;

export type StageBucket = 'all' | 'won' | 'progress' | 'capital' | 'unstaged';

export function projectLabel(group: string, fallback?: string | null): string {
  return PROJECT_SELECTOR.find((item) => item.id === group)?.label || fallback || group;
}

export function isUnusableLabel(value?: string | null): boolean {
  const text = (value || '').trim();
  if (!text) return true;
  if (/^(unknown|null|undefined|n\/a|none)$/i.test(text)) return true;
  if (/^[A-Z0-9_:]+$/.test(text) && text.length <= 24) return true;
  return false;
}

export function normalizeStage(label?: string | null): string {
  const value = (label || '').trim();
  if (isUnusableLabel(value)) return 'Aşamasız';
  if (/kimlik/i.test(value)) return 'Kimlik Bilgileri';
  if (/^(deal won|won|kazanıldı|satın alındı)$/i.test(value)) return 'Kazanıldı';
  if (/kapital kazanç|kapatılan kazanç/i.test(value)) return 'Kapital Kazançlar';
  return value;
}

export function stageBucket(label?: string | null): Exclude<StageBucket, 'all'> {
  const stage = normalizeStage(label);
  if (stage === 'Aşamasız') return 'unstaged';
  if (stage === 'Kapital Kazançlar') return 'capital';
  if (stage === 'Kazanıldı') return 'won';
  return 'progress';
}

export function kanbanColumns(items: CrmAgreementSummary[]): string[] {
  const present = new Set(items.map((item) => normalizeStage(item.stage_label)));
  const columns = PREFERRED_COLUMNS.filter((column) => present.has(column));
  const extras = [...present].filter(
    (column) => !PREFERRED_COLUMNS.includes(column as (typeof PREFERRED_COLUMNS)[number]) && column !== 'Aşamasız',
  );
  extras.sort((a, b) => a.localeCompare(b, 'tr'));
  if (present.has('Aşamasız')) extras.push('Aşamasız');
  return [...columns, ...extras];
}

export function displayDate(value?: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return date.toLocaleDateString('tr-TR');
}

export function displayAmount(row: CrmAgreementSummary): string | null {
  const label = (row.amount_label || '').trim();
  const raw = (row.investment_amount || '').trim();
  if (label) return label;
  if (raw) return raw;
  return null;
}

export function paymentLabel(value?: string | null): string | null {
  const text = (value || '').trim();
  if (isUnusableLabel(text)) return null;
  return text;
}

export function unitLine(row: CrmAgreementSummary): string {
  if (row.project_group === 'reit') return projectLabel(row.project_group, row.project_group_label);
  return [projectLabel(row.project_group, row.project_group_label), row.unit_number].filter(Boolean).join(' · ');
}

export function projectName(row: CrmAgreementSummary): string {
  return projectLabel(row.project_group, row.project_group_label);
}

export function unitAddress(row: CrmAgreementSummary): string | null {
  const fromOwners = (row.participants || []).map((item) => item.address).find((item) => item?.trim());
  return fromOwners?.trim() || null;
}

export function ownerList(row: CrmAgreementSummary): Array<{ contact_id: string; display_name: string }> {
  if (row.participants?.length) {
    return row.participants.map((item) => ({ contact_id: item.contact_id, display_name: item.display_name }));
  }
  return [{ contact_id: row.contact_id, display_name: row.owners_label || row.contact_name || row.contact_id }];
}

export function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '•';
  return ((parts[0][0] || '') + (parts.length > 1 ? parts[parts.length - 1][0] || '' : '')).toUpperCase();
}

export function matchesQuery(row: CrmAgreementSummary, query: string): boolean {
  const needle = query.trim().toLocaleLowerCase('tr');
  if (!needle) return true;
  const haystack = [
    row.owners_label,
    row.contact_name,
    projectName(row),
    row.unit_number,
    row.responsible_name,
    ...(row.participants || []).map((item) => item.display_name),
  ]
    .filter(Boolean)
    .join(' ')
    .toLocaleLowerCase('tr');
  return haystack.includes(needle);
}

export function amountSortValue(row: CrmAgreementSummary): number {
  const raw = (row.amount_label || row.investment_amount || '').replace(/[^\d.,-]/g, '').replace(/,/g, '');
  const parsed = Number.parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : -1;
}
