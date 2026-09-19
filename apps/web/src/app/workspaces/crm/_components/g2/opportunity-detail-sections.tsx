'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ProposalList } from '@/app/dashboard/sales/_components/proposals/proposal-list';
import { fetchInvestor } from '@/lib/api/investors';
import { fetchReservation, type InventoryReservation } from '@/lib/api/inventory';
import { fetchLead } from '@/lib/api/leads';
import {
  fetchOpportunityTimeline,
  formatMoney,
  formatShortDate,
  type OpportunityTimelineEntry,
  type SalesOpportunity,
} from '@/lib/api/sales';
import { fetchProposals, type SalesProposal } from '@/lib/api/sales-proposals';
import { useSalesLabels } from '@/lib/i18n/sales-labels';
import { fetchContact } from '@/workspaces/crm/api/contacts';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';

type OpportunityDetailMode =
  | 'timeline'
  | 'nextAction'
  | 'customer'
  | 'proposal'
  | 'reservation'
  | 'ai';

export type OpportunityDetailPreview = {
  timelines: Record<string, OpportunityTimelineEntry[]>;
  proposals: Record<string, SalesProposal[]>;
  reservations: Record<string, InventoryReservation>;
  customers: Record<string, { full_name: string; email?: string | null; phone?: string | null }>;
};

type OpportunityDetailSectionsProps = {
  opportunity: SalesOpportunity;
  mode: OpportunityDetailMode;
  canViewProposals: boolean;
  canViewReservations: boolean;
  canViewSensitiveValues: boolean;
  preview?: OpportunityDetailPreview;
};

type LoadState<T> =
  | { status: 'loading'; data: null }
  | { status: 'ready'; data: T }
  | { status: 'error'; data: null };

export function OpportunityDetailSections({
  opportunity,
  mode,
  canViewProposals,
  canViewReservations,
  canViewSensitiveValues,
  preview,
}: OpportunityDetailSectionsProps) {
  const locale = useLocale();
  const t = useTranslations('sales');
  const tCommon = useTranslations('common');
  const { getNextActionLabel } = useSalesLabels();
  const { openContact } = useContactCard();
  const [state, setState] = useState<LoadState<unknown>>({ status: 'loading', data: null });

  const load = useCallback(async () => {
    if (preview) {
      if (mode === 'timeline') {
        setState({ status: 'ready', data: preview.timelines[opportunity.id] ?? [] });
      } else if (mode === 'proposal') {
        setState({ status: 'ready', data: preview.proposals[opportunity.id] ?? [] });
      } else if (mode === 'reservation') {
        setState({
          status: 'ready',
          data: opportunity.reservation_id
            ? preview.reservations[opportunity.reservation_id] ?? null
            : null,
        });
      } else if (mode === 'customer') {
        setState({
          status: 'ready',
          data: preview.customers[opportunity.party_id] ?? {
            full_name: opportunity.party_id,
          },
        });
      } else {
        setState({ status: 'ready', data: null });
      }
      return;
    }
    if (mode === 'nextAction' || mode === 'ai') {
      setState({ status: 'ready', data: null });
      return;
    }
    if (mode === 'proposal' && !canViewProposals) {
      setState({ status: 'ready', data: [] });
      return;
    }
    if (mode === 'reservation' && (!canViewReservations || !opportunity.reservation_id)) {
      setState({ status: 'ready', data: null });
      return;
    }

    setState({ status: 'loading', data: null });
    try {
      if (mode === 'timeline') {
        setState({ status: 'ready', data: await fetchOpportunityTimeline(opportunity.id) });
      } else if (mode === 'proposal') {
        const response = await fetchProposals({ opportunity_id: opportunity.id, limit: 50 });
        setState({ status: 'ready', data: response.items });
      } else if (mode === 'reservation' && opportunity.reservation_id) {
        setState({ status: 'ready', data: await fetchReservation(opportunity.reservation_id) });
      } else if (mode === 'customer') {
        if (opportunity.party_type === 'lead') {
          setState({ status: 'ready', data: await fetchLead(opportunity.party_id) });
        } else if (opportunity.party_type === 'crm_contact') {
          const contact = await fetchContact(opportunity.crm_contact_id ?? opportunity.party_id);
          setState({
            status: 'ready',
            data: {
              full_name: contact.display_name,
              email: contact.primary_email,
              phone: contact.primary_phone,
              crm_contact_id: contact.id,
            },
          });
        } else {
          setState({ status: 'ready', data: await fetchInvestor(opportunity.party_id) });
        }
      }
    } catch {
      setState({ status: 'error', data: null });
    }
  }, [
    canViewProposals,
    canViewReservations,
    mode,
    opportunity.id,
    opportunity.party_id,
    opportunity.party_type,
    opportunity.crm_contact_id,
    opportunity.reservation_id,
    preview,
  ]);

  useEffect(() => {
    void load();
  }, [load]);

  if (state.status === 'loading') {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (state.status === 'error') {
    return (
      <ErrorState
        title={t('loadErrorTitle')}
        message={t('loadError')}
        action={<Button onClick={() => void load()}>{tCommon('retry')}</Button>}
      />
    );
  }

  if (mode === 'timeline') {
    const timeline = state.data as OpportunityTimelineEntry[];
    if (!timeline.length) return <EmptyState title={t('detail.noTimeline')} />;
    return (
      <ol className="opportunity-detail-list">
        {timeline.map((entry) => (
          <li key={entry.id}>
            <strong>{entry.event_type}</strong>
            <span>{formatShortDate(entry.created_at, locale)}</span>
            {entry.notes ? <p>{entry.notes}</p> : null}
          </li>
        ))}
      </ol>
    );
  }

  if (mode === 'proposal') {
    return <ProposalList proposals={state.data as SalesProposal[]} />;
  }

  if (mode === 'reservation') {
    const reservation = state.data as InventoryReservation | null;
    if (!canViewReservations) return <EmptyState title="Reservation access unavailable" />;
    if (!reservation) return <EmptyState title={t('detail.noReservation')} />;
    return (
      <dl className="crm-g2-drawer__grid">
        <div><dt>{t('reservation.status')}</dt><dd>{reservation.status}</dd></div>
        <div><dt>{t('reservation.type')}</dt><dd>{reservation.reservation_type}</dd></div>
        <div>
          <dt>{t('reservation.deposit')}</dt>
          <dd>
            {canViewSensitiveValues && reservation.deposit_amount
              ? formatMoney(
                  reservation.deposit_amount,
                  reservation.deposit_currency ?? opportunity.currency,
                  locale,
                )
              : reservation.deposit_amount
                ? '••••'
                : tCommon('noValue')}
          </dd>
        </div>
      </dl>
    );
  }

  if (mode === 'customer') {
    const customer = state.data as {
      full_name: string;
      email?: string | null;
      phone?: string | null;
      crm_contact_id?: string;
    };
    const contactHref = customer.crm_contact_id ?? (
      opportunity.party_type === 'crm_contact'
        ? opportunity.crm_contact_id ?? opportunity.party_id
        : null
    );
    return (
      <dl className="crm-g2-drawer__grid">
        <div><dt>{t('party.name')}</dt><dd>{customer.full_name}</dd></div>
        <div><dt>{t('party.email')}</dt><dd>{customer.email ?? '—'}</dd></div>
        <div><dt>{t('party.phone')}</dt><dd>{customer.phone ?? '—'}</dd></div>
        {contactHref ? (
          <div>
            <dt>CRM</dt>
            <dd>
              <Button type="button" size="sm" variant="secondary" onClick={() => openContact(contactHref)}>
                Kişi Kartı
              </Button>
            </dd>
          </div>
        ) : null}
      </dl>
    );
  }

  if (mode === 'nextAction') {
    return (
      <dl className="crm-g2-drawer__grid">
        <div>
          <dt>{t('nextAction.action')}</dt>
          <dd>
            {opportunity.next_action
              ? getNextActionLabel(opportunity.next_action)
              : tCommon('noValue')}
          </dd>
        </div>
        <div>
          <dt>{t('nextAction.date')}</dt>
          <dd>{formatShortDate(opportunity.next_action_date, locale)}</dd>
        </div>
      </dl>
    );
  }

  return (
    <div className="opportunity-ai-placeholder" aria-disabled="true">
      <StatusChip tone="default">Future</StatusChip>
      <strong>Opportunity AI unavailable</strong>
      <p>No AI service or processing is connected to this workspace.</p>
    </div>
  );
}
