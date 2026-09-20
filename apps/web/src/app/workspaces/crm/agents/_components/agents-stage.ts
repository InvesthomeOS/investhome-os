import type { CrmActivitySummary } from '@/workspaces/crm/types/activities';
import type { CrmContactSummary } from '@/workspaces/crm/types';

export const PREFERRED_COLUMNS = [
  'Acenta Adayı',
  'Ön Bilgi Verildi',
  'Sözleşme Aşaması',
  'Sözleşmeli Acenta',
  'İlk Satışını Yaptı',
] as const;

const STATUS_LABEL: Record<string, string> = {
  active: 'Aktif',
  inactive: 'Pasif',
  prospect: 'Aday',
  archived: 'Arşiv',
};

export function displayDate(value?: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return date.toLocaleDateString('tr-TR');
}

export function normalizeAgentStage(agent: CrmContactSummary): string {
  const raw = (agent.bitrix_original_stage || '').trim();
  if (raw) {
    const match = PREFERRED_COLUMNS.find((column) => column.toLocaleLowerCase('tr') === raw.toLocaleLowerCase('tr'));
    return match || raw;
  }
  return STATUS_LABEL[agent.status] || 'Aşamasız';
}

export function kanbanColumns(items: CrmContactSummary[]): string[] {
  const present = new Set(items.map(normalizeAgentStage));
  const preferred = PREFERRED_COLUMNS.filter((column) => present.has(column));
  const extras = [...present].filter(
    (column) => !PREFERRED_COLUMNS.includes(column as (typeof PREFERRED_COLUMNS)[number]),
  );
  extras.sort((a, b) => a.localeCompare(b, 'tr'));
  return [...preferred, ...extras];
}

export function agentFlags(agent: CrmContactSummary): string[] {
  const notes = String(agent.notes || '');
  const flags: string[] = [];
  if (/BILGI_EKSIK/i.test(notes) || (!agent.primary_phone && !agent.primary_email)) {
    flags.push('BILGI_EKSIK');
  }
  if (/INCELEME_GEREKLI/i.test(notes) || agent.review_required) {
    flags.push('INCELEME_GEREKLI');
  }
  return [...new Set(flags)];
}

export function plainNotes(value?: string | null): string {
  if (!value) return '';
  return value
    .replace(/BILGI_EKSIK:\s*/gi, '')
    .replace(/INCELEME_GEREKLI:\s*/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\[\/?[^\]]+\]/g, ' ')
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 80);
}

export function responsibleOf(agent: CrmContactSummary): string {
  return agent.bitrix_responsible || agent.owner_name || '';
}

export type AgentActivityIndex = {
  last: Record<string, CrmActivitySummary | undefined>;
  next: Record<string, CrmActivitySummary | undefined>;
  items: CrmActivitySummary[];
};

export function buildActivityIndex(
  agentIds: string[],
  activities: CrmActivitySummary[],
): AgentActivityIndex {
  const idSet = new Set(agentIds);
  const scoped = activities.filter((item) => idSet.has(item.entity_id));
  const last: AgentActivityIndex['last'] = {};
  const next: AgentActivityIndex['next'] = {};
  const now = Date.now();
  const sorted = [...scoped].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
  for (const item of sorted) {
    if (!last[item.entity_id]) last[item.entity_id] = item;
  }
  const upcoming = scoped
    .map((item) => ({ item, when: Date.parse(item.due_date || item.start_date || '') }))
    .filter((row) => !Number.isNaN(row.when) && row.when >= now)
    .sort((a, b) => a.when - b.when);
  for (const row of upcoming) {
    if (!next[row.item.entity_id]) next[row.item.entity_id] = row.item;
  }
  return { last, next, items: sorted };
}
