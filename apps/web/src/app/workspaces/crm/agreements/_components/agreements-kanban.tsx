'use client';

import type { CrmAgreementSummary } from '@/workspaces/crm/api/agreements';

import { displayDate, kanbanColumns, normalizeStage, unitLine } from './agreements-stage';

export function AgreementsKanban({
  items,
  onOpen,
}: {
  items: CrmAgreementSummary[];
  onOpen: (row: CrmAgreementSummary) => void;
}) {
  const columns = kanbanColumns(items);

  return (
    <div className="crm-agreements-kanban" data-testid="agreements-kanban">
      {columns.map((column) => {
        const cards = items.filter((item) => normalizeStage(item.stage_label) === column);
        return (
          <section key={column} className="crm-agreements-column" data-testid={`agreements-column-${column}`}>
            <h2>
              {column}
              <span>{cards.length}</span>
            </h2>
            {cards.map((row) => (
              <button
                key={row.id}
                type="button"
                className="crm-agreements-card"
                data-testid={`agreements-card-${row.id}`}
                onClick={() => onOpen(row)}
              >
                <strong>{row.owners_label || row.contact_name || '—'}</strong>
                <small>{unitLine(row)}</small>
                <small>{row.amount_label || row.investment_amount || '—'}</small>
                <span className="crm-agreements-meta">{normalizeStage(row.stage_label)}</span>
                {row.next_activity_title ? (
                  <span className="crm-agreements-meta">
                    {row.next_activity_title}
                    {row.next_activity_at ? ` · ${displayDate(row.next_activity_at)}` : ''}
                  </span>
                ) : null}
                {row.responsible_name ? <span className="crm-agreements-meta">{row.responsible_name}</span> : null}
                <div className="crm-agreements-tags">
                  {row.joint_owners ? <span className="crm-agreements-tag">Ortak</span> : null}
                  {row.hemen_kira ? <span className="crm-agreements-tag is-rent">Hemen Kira</span> : null}
                </div>
              </button>
            ))}
          </section>
        );
      })}
    </div>
  );
}
