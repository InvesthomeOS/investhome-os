'use client';

import { useTranslations } from 'next-intl';

import { InvestorKpiCard } from '../kpi-card';
import type { MessagesSummaryKpis } from '../../_data/messaging-types';

interface MessagesKpiRowProps {
  summary: MessagesSummaryKpis;
}

export function MessagesKpiRow({ summary }: MessagesKpiRowProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <section className="inv-msg-kpi-row" aria-label={tChrome('ke0a08d98d0')}>
      <InvestorKpiCard label="Unread Messages" value={summary.unreadMessages} />
      <InvestorKpiCard label={tChrome('k07c59b4412')} value={summary.totalConversations} />
      <InvestorKpiCard label={tChrome('ke61561a80e')} value={summary.starredConversations} />
      <InvestorKpiCard label="Pending Responses" value={summary.pendingResponses} />
      <InvestorKpiCard label="Announcements" value={summary.unreadAnnouncements} meta="unread" />
      <InvestorKpiCard label="Notifications" value={summary.unreadNotifications} meta="unread" />
    </section>
  );
}
