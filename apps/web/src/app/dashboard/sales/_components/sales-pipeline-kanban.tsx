'use client';

import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { StatusChip } from '@investhome/ui';

import {
  PIPELINE_COLUMNS,
  canTransitionStage,
  formatMoney,
  formatShortDate,
  stageRequiresModal,
  type SalesOpportunity,
  type OpportunityStage,
} from '@/lib/api/sales';
import { useSalesLabels } from '@/lib/i18n/sales-labels';

interface SalesPipelineKanbanProps {
  opportunities: SalesOpportunity[];
  partyNames: Record<string, string>;
  userNames: Record<string, string>;
  projectNames: Record<string, string>;
  inventoryLabels: Record<string, string>;
  primaryProjectByOpp: Record<string, string>;
  primaryInventoryByOpp: Record<string, string>;
  canChangeStage: boolean;
  onOpen: (opportunity: SalesOpportunity) => void;
  onStageChange: (opportunity: SalesOpportunity, stage: OpportunityStage) => void;
  onStageChangeError: (message: string) => void;
}

export function SalesPipelineKanban({
  opportunities,
  partyNames,
  userNames,
  projectNames,
  inventoryLabels,
  primaryProjectByOpp,
  primaryInventoryByOpp,
  canChangeStage,
  onOpen,
  onStageChange,
  onStageChangeError,
}: SalesPipelineKanbanProps) {
  const t = useTranslations('sales');
  const locale = useLocale();
  const { getStageLabel, getNextActionLabel, getPriorityLabel } = useSalesLabels();
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);

  const byColumn = useMemo(() => {
    const map: Record<string, SalesOpportunity[]> = {};
    for (const column of PIPELINE_COLUMNS) {
      map[column.id] = opportunities.filter((o) => column.stages.includes(o.stage));
    }
    return map;
  }, [opportunities]);

  const handleDrop = (columnId: string) => {
    setDragOverColumn(null);
    setDraggingId(null);
    if (!canChangeStage || !draggingId) return;

    const column = PIPELINE_COLUMNS.find((c) => c.id === columnId);
    const opportunity = opportunities.find((o) => o.id === draggingId);
    if (!column || !opportunity) return;

    const targetStage = column.dropStage;
    if (opportunity.stage === targetStage) return;

    if (!canTransitionStage(opportunity.stage, targetStage)) {
      onStageChangeError(t('errors.invalidStageTransition'));
      return;
    }

    if (stageRequiresModal(targetStage)) {
      onStageChange(opportunity, targetStage);
      return;
    }

    onStageChange(opportunity, targetStage);
  };

  return (
    <div className="sales__kanban" role="list">
      {PIPELINE_COLUMNS.map((column) => (
        <section
          key={column.id}
          className={`sales__kanban-column${dragOverColumn === column.id ? ' sales__kanban-column--active' : ''}`}
          onDragOver={(e) => {
            if (!canChangeStage) return;
            e.preventDefault();
            setDragOverColumn(column.id);
          }}
          onDragLeave={() => setDragOverColumn(null)}
          onDrop={(e) => {
            e.preventDefault();
            handleDrop(column.id);
          }}
        >
          <header className="sales__kanban-column-header">
            <h3>{getStageLabel(column.dropStage)}</h3>
            <span>{byColumn[column.id]?.length ?? 0}</span>
          </header>
          <div className="sales__kanban-cards">
            {(byColumn[column.id] ?? []).map((opportunity) => (
              <article
                key={opportunity.id}
                className={`sales__kanban-card${draggingId === opportunity.id ? ' sales__kanban-card--dragging' : ''}`}
                draggable={canChangeStage}
                onDragStart={() => setDraggingId(opportunity.id)}
                onDragEnd={() => {
                  setDraggingId(null);
                  setDragOverColumn(null);
                }}
                onClick={() => onOpen(opportunity)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onOpen(opportunity);
                  }
                }}
              >
                <div className="sales__kanban-card-top">
                  <strong>{opportunity.display_id ?? opportunity.opportunity_code}</strong>
                  <StatusChip tone="default">{getPriorityLabel(opportunity.priority)}</StatusChip>
                </div>
                <p className="sales__kanban-party">
                  {partyNames[opportunity.party_id] ?? t('unknownParty')}
                </p>
                {opportunity.expected_revenue && (
                  <p className="sales__kanban-value">
                    {formatMoney(opportunity.expected_revenue, opportunity.currency, locale)}
                    <span> · {opportunity.probability}%</span>
                  </p>
                )}
                {opportunity.assigned_sales_user_id && (
                  <p className="sales__kanban-meta">
                    {userNames[opportunity.assigned_sales_user_id] ?? '—'}
                  </p>
                )}
                {opportunity.next_action && (
                  <p className="sales__kanban-next">
                    {getNextActionLabel(opportunity.next_action)}
                    {opportunity.next_action_date
                      ? ` · ${formatShortDate(opportunity.next_action_date, locale)}`
                      : ''}
                  </p>
                )}
                {primaryProjectByOpp[opportunity.id] && projectNames[primaryProjectByOpp[opportunity.id]!] && (
                  <p className="sales__kanban-chip">
                    {projectNames[primaryProjectByOpp[opportunity.id]!]}
                  </p>
                )}
                {primaryInventoryByOpp[opportunity.id] && inventoryLabels[primaryInventoryByOpp[opportunity.id]!] && (
                  <p className="sales__kanban-chip">
                    {inventoryLabels[primaryInventoryByOpp[opportunity.id]!]}
                  </p>
                )}
                {opportunity.expected_close_date && (
                  <p className="sales__kanban-meta">
                    {t('table.expectedClose')}:{' '}
                    {formatShortDate(opportunity.expected_close_date, locale)}
                  </p>
                )}
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
