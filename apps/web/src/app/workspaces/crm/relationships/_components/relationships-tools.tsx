'use client';

import Link from 'next/link';
import { useLocale } from 'next-intl';

import { RelationshipIntelligenceDashboard } from './relationship-intelligence-dashboard';

import '../../contacts/_components/people-workspace.css';

export function RelationshipsToolsPage() {
  const tr = useLocale().startsWith('tr');
  return (
    <div className="crm-people-tools-page" style={{ maxWidth: '100%' }} data-testid="crm-relationships-tools">
      <Link href="/workspaces/crm/relationships">{tr ? 'İlişkilere dön' : 'Back to relationships'}</Link>
      <h1>{tr ? 'İlişki araçları' : 'Relationship tools'}</h1>
      <p>
        {tr
          ? 'Zeka, skor ve ilişki analizi birincil listeden ayrıldı. Müşteri verisini değiştirmez.'
          : 'Intelligence, scores and relationship analysis were moved off the primary list. Does not change customer data.'}
      </p>
      <RelationshipIntelligenceDashboard />
    </div>
  );
}
