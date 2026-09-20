'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import type { CrmContactSummary } from '@/workspaces/crm/types';

import {
  agentFlags,
  displayDate,
  normalizeAgentStage,
  plainNotes,
  responsibleOf,
  type AgentActivityIndex,
} from './agents-stage';

const STORAGE_KEY = 'crm.agents.listColumns.v1';

const DEFAULT_COLUMNS = [
  'acenta',
  'ofis',
  'durum',
  'telefon',
  'eposta',
  'sorumlu',
  'sonEtkinlik',
  'sonrakiEtkinlik',
  'tarih',
] as const;

const OPTIONAL_COLUMNS = ['sehir', 'adres', 'kaynak', 'unvan', 'notlar'] as const;

type ColumnId = (typeof DEFAULT_COLUMNS)[number] | (typeof OPTIONAL_COLUMNS)[number];

function loadColumns(): ColumnId[] {
  if (typeof window === 'undefined') return [...DEFAULT_COLUMNS];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as string[]) : null;
    if (!Array.isArray(parsed) || !parsed.length) return [...DEFAULT_COLUMNS];
    const allowed = new Set<string>([...DEFAULT_COLUMNS, ...OPTIONAL_COLUMNS]);
    const next = parsed.filter((item): item is ColumnId => allowed.has(item));
    return next.length ? next : [...DEFAULT_COLUMNS];
  } catch {
    return [...DEFAULT_COLUMNS];
  }
}

export function AgentsList({
  items,
  activity,
  onOpen,
}: {
  items: CrmContactSummary[];
  activity: AgentActivityIndex;
  onOpen: (agent: CrmContactSummary) => void;
}) {
  const t = useTranslations('crm.agents');
  const [open, setOpen] = useState(false);
  const [columns, setColumns] = useState<ColumnId[]>([...DEFAULT_COLUMNS]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setColumns(loadColumns());
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready || typeof window === 'undefined') return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(columns));
  }, [columns, ready]);

  const allColumns = useMemo(() => [...DEFAULT_COLUMNS, ...OPTIONAL_COLUMNS], []);

  const cell = (agent: CrmContactSummary, column: ColumnId): string => {
    const last = activity.last[agent.id];
    const next = activity.next[agent.id];
    switch (column) {
      case 'acenta':
        return agent.display_name;
      case 'ofis':
        return agent.organization_name || agent.company_name || '';
      case 'durum':
        return normalizeAgentStage(agent);
      case 'telefon':
        return agent.primary_phone || '';
      case 'eposta':
        return agent.primary_email || '';
      case 'sorumlu':
        return responsibleOf(agent);
      case 'sonEtkinlik':
        return last ? [last.title, displayDate(last.created_at)].filter(Boolean).join(' · ') : '';
      case 'sonrakiEtkinlik':
        return next
          ? [next.title, displayDate(next.due_date || next.start_date)].filter(Boolean).join(' · ')
          : '';
      case 'tarih':
        return displayDate(agent.last_contact_at || agent.updated_at || agent.created_at);
      case 'sehir':
        return agent.city || '';
      case 'adres':
        return agent.address_line1 || '';
      case 'kaynak':
        return agent.source || '';
      case 'unvan':
        return agent.job_title || '';
      case 'notlar':
        return plainNotes(agent.notes);
      default:
        return '';
    }
  };

  return (
    <section className="ctc-ds__table-section" data-testid="agents-list">
      <div className="crm-agreements-list-tools">
        <div className="crm-agreements-columns">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            data-testid="agents-column-picker-toggle"
            onClick={() => setOpen((value) => !value)}
          >
            {t('columnPicker')}
          </Button>
          {open ? (
            <div className="crm-agreements-columns__panel" data-testid="agents-column-picker">
              {allColumns.map((id) => (
                <label key={id}>
                  <input
                    type="checkbox"
                    checked={columns.includes(id)}
                    onChange={() =>
                      setColumns((current) =>
                        current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
                      )
                    }
                  />
                  {t(`listColumns.${id}`)}
                </label>
              ))}
            </div>
          ) : null}
        </div>
      </div>
      <div className="ctc-ds__table-wrap">
        <table className="ctc-ds__table crm-agreements-table" aria-label={t('tableAria')}>
          <thead>
            <tr>
              {columns.map((id) => (
                <th key={id} scope="col">
                  {t(`listColumns.${id}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((agent) => (
              <tr
                key={agent.id}
                className="ctc-ds__row"
                data-testid={`agents-row-${agent.id}`}
                onClick={() => onOpen(agent)}
              >
                {columns.map((id) => (
                  <td key={`${agent.id}:${id}`}>
                    {id === 'durum' ? (
                      <div>
                        <StatusChip tone={agent.status === 'active' ? 'success' : 'default'}>
                          {cell(agent, id)}
                        </StatusChip>
                        <div className="crm-agreements-tags">
                          {agentFlags(agent).map((flag) => (
                            <span key={flag} className="crm-agreements-tag">
                              {flag}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : (
                      cell(agent, id)
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
