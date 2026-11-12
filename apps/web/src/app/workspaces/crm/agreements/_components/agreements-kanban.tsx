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

const ACTIVE_COLUMNS = [
  { stage: 'Kimlik Bilgileri', label: 'Kimlik Bilgileri Süreci' },
  { stage: 'Satış Sözleşmesi', label: 'Satış Sözleşmesi Süreci' },
  { stage: 'Docusign', label: 'DocuSign' },
  { stage: 'Para Transferi', label: 'Para Transfer Süreci' },
  { stage: 'Ev Teslim Süreci', label: 'Ev Teslim Süreci' },
] as const;

export function AgreementsKanban({
  columns,
  onOpen,
  onLoadMore,
}: {
  columns: AgreementsKanbanColumn[];
  onOpen: (row: CrmAgreementSummary) => void;
  onLoadMore: (stage: string) => void;
}) {
  const activeColumns = ACTIVE_COLUMNS.map((definition) => ({
    definition,
    column:
      columns.find((item) => item.stage === definition.stage) ?? {
        stage: definition.stage,
        total: 0,
        items: [],
        hasMore: false,
        loadingMore: false,
      },
  }));

  return (
    <div className="crm-agreements-kanban" data-testid="agreements-kanban">
      <div className="crm-agreements-kanban__inner">
        <div className="crm-agreements-kanban__header-row">
          {activeColumns.map(({ definition, column }) => (
            <div
              key={definition.stage}
              className="crm-agreements-kanban__header-cell"
              title={definition.label}
            >
              <span>{definition.label}</span>
              <strong data-testid={`agreements-column-total-${definition.stage}`}>
                {column.total}
              </strong>
            </div>
          ))}
        </div>

        <div className="crm-agreements-kanban__columns">
          {activeColumns.map(({ definition, column }) => (
            <section
              key={definition.stage}
              className="crm-agreements-column"
              data-testid={`agreements-column-${definition.stage}`}
            >
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
                        {row.project_group !== 'reit' && (row.phase_name || row.unit_number) ? ` · ${[row.phase_name, row.unit_number].filter(Boolean).join(' · ')}` : ''}
                      </small>

                      <b>{amount || '—'}</b>

                      <span className="crm-agreements-meta">
                        {normalizeStage(row.stage_label)}
                      </span>

                      {row.responsible_name ? (
                        <span className="crm-agreements-person" title={row.responsible_name}>
                          <em>{initials(row.responsible_name)}</em>
                          {row.responsible_name}
                        </span>
                      ) : null}

                      <div className="crm-agreements-tags">
                        {row.joint_owners ? <span className="crm-agreements-tag">Ortak</span> : null}
                        {row.has_unit_change ? (
                          <span className="crm-agreements-tag">Daire değişikliği</span>
                        ) : null}
                        {row.hemen_kira ? (
                          <span className="crm-agreements-tag is-rent">Hemen Kira</span>
                        ) : null}
                      </div>
                    </button>
                  );
                })}
              </div>

              {column.hasMore ? (
                <button
                  type="button"
                  className="crm-agreements-column__more"
                  data-testid={`agreements-column-more-${definition.stage}`}
                  disabled={column.loadingMore}
                  onClick={() => onLoadMore(definition.stage)}
                >
                  Daha fazla
                </button>
              ) : null}
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
