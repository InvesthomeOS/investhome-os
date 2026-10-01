'use client';

import type { CrmAgreementSummary } from '@/workspaces/crm/api/agreements';

import {
  displayAmount,
  initials,
  kanbanColumns,
  normalizeStage,
  ownerList,
  projectName,
} from './agreements-stage';

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
            <h2 title={column}>
              <span>{column}</span>
              <strong>{cards.length}</strong>
            </h2>
            <div className="crm-agreements-column__cards">
              {cards.map((row) => {
                const owners = ownerList(row);
                const amount = displayAmount(row);
                return (
                  <button
                    key={row.id}
                    type="button"
                    className="crm-agreements-card"
                    data-testid={`agreements-card-${row.id}`}
                    onClick={() => onOpen(row)}
                  >
                    <strong title={owners.map((item) => item.display_name).join(' + ')}>
                      {owners.map((item) => item.display_name).join(' + ')}
                    </strong>
                    <small>
                      {projectName(row)}
                      {row.project_group !== 'reit' && row.unit_number ? ` · ${row.unit_number}` : ''}
                    </small>
                    <b>{amount || '—'}</b>
                    <span className="crm-agreements-meta">{normalizeStage(row.stage_label)}</span>
                    {row.responsible_name ? (
                      <span className="crm-agreements-person" title={row.responsible_name}>
                        <em>{initials(row.responsible_name)}</em>
                        {row.responsible_name}
                      </span>
                    ) : null}
                    <div className="crm-agreements-tags">
                      {row.joint_owners ? <span className="crm-agreements-tag">Ortak</span> : null}
                      {row.has_unit_change ? <span className="crm-agreements-tag">Daire değişikliği</span> : null}
                      {row.hemen_kira ? <span className="crm-agreements-tag is-rent">Hemen Kira</span> : null}
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
