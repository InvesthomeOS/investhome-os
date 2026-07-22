'use client';

import { InvestorKpiCard } from '../kpi-card';
import type { MessagesSummaryKpis } from '../../_data/messaging-types';

interface MessagesKpiRowProps {
  summary: MessagesSummaryKpis;
}

export function MessagesKpiRow({ summary }: MessagesKpiRowProps) {
  return (
    <section className="inv-msg-kpi-row" aria-label="Message summary">
      <InvestorKpiCard label="Unread Messages" value={summary.unreadMessages} />
      <InvestorKpiCard label="Conversations" value={summary.totalConversations} />
      <InvestorKpiCard label="Starred" value={summary.starredConversations} />
      <InvestorKpiCard label="Pending Responses" value={summary.pendingResponses} />
      <InvestorKpiCard label="Announcements" value={summary.unreadAnnouncements} meta="unread" />
      <InvestorKpiCard label="Notifications" value={summary.unreadNotifications} meta="unread" />
    </section>
  );
}
