'use client';

import { useLocale, useTranslations } from 'next-intl';

import { ProgressBar, StatusChip } from '@investhome/ui';

import { formatMoney, formatShortDate, type SalesOpportunity } from '@/lib/api/sales';
import { useSalesLabels } from '@/lib/i18n/sales-labels';

import { isOpportunityOverdue, opportunityWeightedValue } from './opportunity-presentation';

type OpportunityCardProps = {
  opportunity: SalesOpportunity;
  assigneeName?: string;
  customerName?: string | null;
  projectName?: string | null;
  canViewSensitiveValues: boolean;
  draggable?: boolean;
  dragging?: boolean;
  selected?: boolean;
  onOpen: () => void;
  onDragStart?: () => void;
  onDragEnd?: () => void;
};

function priorityTone(priority: SalesOpportunity['priority']) {
  if (priority === 'urgent') return 'danger' as const;
  if (priority === 'high') return 'warning' as const;
  return 'default' as const;
}

export function OpportunityCard({
  opportunity,
  assigneeName,
  customerName,
  projectName,
  canViewSensitiveValues,
  draggable = false,
  dragging = false,
  selected = false,
  onOpen,
  onDragStart,
  onDragEnd,
}: OpportunityCardProps) {
  const locale = useLocale();
  const t = useTranslations('sales');
  const tPipeline = useTranslations('crm.g2.pipeline');
  const tCommon = useTranslations('common');
  const { getPriorityLabel, getNextActionLabel } = useSalesLabels();
  const weightedValue = opportunityWeightedValue(opportunity);
  const overdue = isOpportunityOverdue(opportunity);
  const title = opportunity.display_id ?? opportunity.opportunity_code;

  return (
    <article
      className={[
        'opportunity-card',
        dragging ? 'opportunity-card--dragging' : '',
        selected ? 'opportunity-card--selected' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      draggable={draggable}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onOpen();
        }
      }}
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      aria-label={`${title}, ${customerName ?? ''}`}
    >
      <div className="opportunity-card__heading">
        <strong>{title}</strong>
        <StatusChip tone={priorityTone(opportunity.priority)}>
          {getPriorityLabel(opportunity.priority)}
        </StatusChip>
      </div>

      <div className="opportunity-card__context">
        <strong>{customerName?.trim() || tCommon('noValue')}</strong>
        <span>{projectName?.trim() || tCommon('noValue')}</span>
      </div>

      <dl className="opportunity-card__metrics">
        <div>
          <dt>{t('table.value')}</dt>
          <dd>
            {canViewSensitiveValues
              ? formatMoney(opportunity.expected_revenue, opportunity.currency, locale)
              : '••••'}
          </dd>
        </div>
        <div>
          <dt>{tPipeline('weighted')}</dt>
          <dd>
            {canViewSensitiveValues && weightedValue !== null
              ? formatMoney(String(weightedValue), opportunity.currency, locale)
              : '••••'}
          </dd>
        </div>
      </dl>

      <div className="opportunity-card__probability">
        <span>{tPipeline('probability')}</span>
        <strong>{opportunity.probability}%</strong>
      </div>
      <ProgressBar value={opportunity.probability} />

      <div className="opportunity-card__meta">
        <span className="is-owner">{assigneeName ?? tCommon('noValue')}</span>
        <span>
          {opportunity.next_action
            ? getNextActionLabel(opportunity.next_action)
            : tCommon('noValue')}
        </span>
        <span className={overdue ? 'is-overdue' : undefined}>
          {opportunity.next_action_date
            ? formatShortDate(opportunity.next_action_date, locale)
            : tCommon('noValue')}
          {overdue ? ` · ${tPipeline('overdue')}` : ''}
        </span>
      </div>
    </article>
  );
}
