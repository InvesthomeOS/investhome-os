import { useTranslations } from 'next-intl';

import {
  LEAD_SOURCES,
  LEAD_STATUSES,
  type LeadSource,
  type LeadStatus,
} from '@/lib/api/leads';

const STATUS_KEYS: Record<LeadStatus, string> = {
  New: 'new',
  Contacted: 'contacted',
  Qualified: 'qualified',
  'Meeting Scheduled': 'meeting_scheduled',
  'Proposal Sent': 'proposal_sent',
  Negotiation: 'negotiation',
  Won: 'won',
  Lost: 'lost',
};

const SOURCE_KEYS: Record<LeadSource, string> = {
  Website: 'website',
  Referral: 'referral',
  Exhibition: 'exhibition',
  LinkedIn: 'linkedin',
  Partner: 'partner',
  'Cold Outreach': 'cold_outreach',
};

export function useLeadLabels() {
  const tStatus = useTranslations('leads.statuses');
  const tSource = useTranslations('leads.sources');

  const getStatusLabel = (status: LeadStatus | string): string => {
    const key = STATUS_KEYS[status as LeadStatus];
    return key ? tStatus(key) : status;
  };

  const getSourceLabel = (source: string | null | undefined): string => {
    if (!source) {
      return '—';
    }

    const key = SOURCE_KEYS[source as LeadSource];
    return key ? tSource(key) : source;
  };

  const statusOptions = LEAD_STATUSES.map((status) => ({
    value: status,
    label: tStatus(STATUS_KEYS[status]),
  }));

  const sourceOptions = LEAD_SOURCES.map((source) => ({
    value: source,
    label: tSource(SOURCE_KEYS[source]),
  }));

  return {
    getStatusLabel,
    getSourceLabel,
    statusOptions,
    sourceOptions,
  };
}
