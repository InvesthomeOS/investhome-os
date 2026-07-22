'use client';

import { useMemo, useState } from 'react';

import type { Investor, InvestorStatus } from '@/lib/api/investors';
import { formatCurrency, formatShortDate } from '@/lib/api/investors';

import { getBoardMeta } from './board-meta';
import { stageProbability, toLifecycleStage, type InvestorLifecycleStage } from './lifecycle';

export type ListColumnId =
  | 'select'
  | 'name'
  | 'country'
  | 'type'
  | 'stage'
  | 'capacity'
  | 'model'
  | 'assigned'
  | 'probability'
  | 'lastContact'
  | 'nextFollowUp'
  | 'updated';

const DEFAULT_COLUMNS: ListColumnId[] = [
  'select',
  'name',
  'country',
  'type',
  'stage',
  'capacity',
  'assigned',
  'probability',
  'nextFollowUp',
  'updated',
];

interface ListViewProps {
  investors: Investor[];
  locale: string;
  selectedIds: Set<string>;
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: () => void;
  onOpen: (investor: Investor) => void;
  onSort: (sortBy: string) => void;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  stageLabel: (stage: InvestorLifecycleStage) => string;
  typeLabel: (type: string) => string;
  columnLabels: Record<ListColumnId, string>;
  visibleColumns?: ListColumnId[];
  onInlineAssign?: (investor: Investor, value: string) => void;
  metaVersion: number;
}

export function ListView({
  investors,
  locale,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onOpen,
  onSort,
  sortBy,
  sortOrder,
  stageLabel,
  typeLabel,
  columnLabels,
  visibleColumns = DEFAULT_COLUMNS,
  onInlineAssign,
  metaVersion,
}: ListViewProps) {
  const [editingAssign, setEditingAssign] = useState<string | null>(null);
  const cols = useMemo(
    () => DEFAULT_COLUMNS.filter((c) => visibleColumns.includes(c)),
    [visibleColumns],
  );

  const allSelected = investors.length > 0 && investors.every((i) => selectedIds.has(i.id));

  const sortMark = (key: string) => {
    if (sortBy !== key) return '';
    return sortOrder === 'asc' ? ' ↑' : ' ↓';
  };

  return (
    <div className="inv-g3__list-wrap" data-testid="inv-g3-list">
      <table className="inv-g3__table">
        <thead>
          <tr>
            {cols.map((col) => (
              <th key={col}>
                {col === 'select' ? (
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={onToggleSelectAll}
                    aria-label={columnLabels.select}
                  />
                ) : (
                  <button
                    type="button"
                    onClick={() => {
                      const map: Partial<Record<ListColumnId, string>> = {
                        name: 'full_name',
                        country: 'country',
                        type: 'investor_type',
                        stage: 'status',
                        capacity: 'investment_capacity',
                        assigned: 'assigned_to',
                        lastContact: 'last_contact_date',
                        nextFollowUp: 'next_follow_up_date',
                        updated: 'updated_at',
                      };
                      const key = map[col];
                      if (key) onSort(key);
                    }}
                  >
                    {columnLabels[col]}
                    {sortMark(
                      col === 'name'
                        ? 'full_name'
                        : col === 'stage'
                          ? 'status'
                          : col === 'capacity'
                            ? 'investment_capacity'
                            : col === 'assigned'
                              ? 'assigned_to'
                              : col === 'nextFollowUp'
                                ? 'next_follow_up_date'
                                : col === 'updated'
                                  ? 'updated_at'
                                  : col,
                    )}
                  </button>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {investors.map((investor) => {
            const stage = toLifecycleStage(investor.status);
            const meta = getBoardMeta(investor.id);
            void metaVersion;
            const probability = meta.probability ?? stageProbability(stage);
            return (
              <tr
                key={investor.id}
                className={selectedIds.has(investor.id) ? 'is-selected' : undefined}
                onClick={() => onOpen(investor)}
                data-testid={`inv-g3-row-${investor.id}`}
              >
                {cols.map((col) => {
                  if (col === 'select') {
                    return (
                      <td key={col} onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(investor.id)}
                          onChange={() => onToggleSelect(investor.id)}
                          aria-label={investor.full_name}
                        />
                      </td>
                    );
                  }
                  if (col === 'name') {
                    return (
                      <td key={col}>
                        <strong>{investor.full_name}</strong>
                        {investor.is_demo ? ' · demo' : ''}
                      </td>
                    );
                  }
                  if (col === 'country') return <td key={col}>{investor.country ?? '—'}</td>;
                  if (col === 'type') return <td key={col}>{typeLabel(investor.investor_type)}</td>;
                  if (col === 'stage') return <td key={col}>{stageLabel(stage)}</td>;
                  if (col === 'capacity') {
                    return (
                      <td key={col}>{formatCurrency(investor.investment_capacity, locale)}</td>
                    );
                  }
                  if (col === 'model') {
                    return <td key={col}>{investor.preferred_investment_model ?? '—'}</td>;
                  }
                  if (col === 'assigned') {
                    return (
                      <td key={col} onClick={(e) => e.stopPropagation()}>
                        {editingAssign === investor.id && onInlineAssign ? (
                          <input
                            className="inv-g3__inline"
                            defaultValue={investor.assigned_to ?? ''}
                            autoFocus
                            onBlur={(e) => {
                              onInlineAssign(investor, e.target.value);
                              setEditingAssign(null);
                            }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                onInlineAssign(investor, (e.target as HTMLInputElement).value);
                                setEditingAssign(null);
                              }
                              if (e.key === 'Escape') setEditingAssign(null);
                            }}
                          />
                        ) : (
                          <button
                            type="button"
                            className="inv-g3__link"
                            onClick={() => setEditingAssign(investor.id)}
                          >
                            {investor.assigned_to || '—'}
                          </button>
                        )}
                      </td>
                    );
                  }
                  if (col === 'probability') return <td key={col}>%{probability}</td>;
                  if (col === 'lastContact') {
                    return (
                      <td key={col}>
                        {formatShortDate(investor.last_contact_date, locale)}
                      </td>
                    );
                  }
                  if (col === 'nextFollowUp') {
                    return (
                      <td key={col}>
                        {formatShortDate(investor.next_follow_up_date, locale)}
                      </td>
                    );
                  }
                  if (col === 'updated') {
                    return (
                      <td key={col}>{formatShortDate(investor.updated_at.slice(0, 10), locale)}</td>
                    );
                  }
                  return <td key={col}>—</td>;
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export { DEFAULT_COLUMNS };
export type { InvestorStatus };
