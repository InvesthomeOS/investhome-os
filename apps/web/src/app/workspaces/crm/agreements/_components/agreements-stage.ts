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
  'Kapatılan Kazançlar',
] as const;

export function projectLabel(group: string, fallback?: string | null): string {
  return PROJECT_SELECTOR.find((item) => item.id === group)?.label || fallback || group;
}

export function normalizeStage(label?: string | null): string {
  const value = (label || '').trim();
  if (!value) return 'Aşamasız';
  if (/kimlik/i.test(value)) return 'Kimlik Bilgileri';
  if (/^(deal won|won|kazanıldı)$/i.test(value)) return 'Kazanıldı';
  return value;
}

export function kanbanColumns(items: CrmAgreementSummary[]): string[] {
  const present = new Set(items.map((item) => normalizeStage(item.stage_label)));
  const columns = PREFERRED_COLUMNS.filter((column) => present.has(column));
  const extras = [...present].filter((column) => !PREFERRED_COLUMNS.includes(column as (typeof PREFERRED_COLUMNS)[number]) && column !== 'Aşamasız');
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

export function unitLine(row: CrmAgreementSummary): string {
  if (row.project_group === 'reit') return projectLabel(row.project_group, row.project_group_label);
  return [projectLabel(row.project_group, row.project_group_label), row.unit_number].filter(Boolean).join(' · ');
}
