'use client';

import type { CrmAgreementSummary } from '@/workspaces/crm/api/agreements';

import { displayAmount, initials, normalizeStage, ownerList, projectName } from './agreements-stage';

export type AgreementsKanbanColumn = {
  stage: string;
  total: number;
  items: CrmAgreementSummary[];
  hasMore: boolean;
  loadingMore: boolean;
};

export function AgreementsKanban({
  columns,
  onOpen,
  onLoadMore,
}: {
  columns: AgreementsKanbanColumn[];
  onOpen: (row: CrmAgreementSummary) => void;
  onLoadMore: (stage: string) => void;
}) {
  return (
    <div className="crm-agreements-kanban" data-testid="agreements-kanban">
      {columns.map((column) => {
        return (
          <section key={column.stage} className="crm-agreements-column" data-testid={`agreements-column-${column.stage}`}>
            <h2 title={column.stage}>
              <span>{column.stage}</span>
              <strong data-testid={`agreements-column-total-${column.stage}`}>{column.total}</strong>
            </h2>
            <div className="crm-agreements-column__cards">
              {column.items.map((row) => {
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
            {column.hasMore ? (
              <button
                type="button"
                className="crm-agreements-column__more"
                data-testid={`agreements-column-more-${column.stage}`}
                disabled={column.loadingMore}
                onClick={() => onLoadMore(column.stage)}
              >
                Daha fazla
              </button>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}
