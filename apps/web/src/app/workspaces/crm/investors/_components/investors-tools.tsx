'use client';

import Link from 'next/link';
import { useLocale } from 'next-intl';

import { Button } from '@investhome/ui';

import { CrmInvestorsWorkspace } from './crm-investors-workspace';

import '../../contacts/_components/people-workspace.css';

export function InvestorsToolsPage() {
  const tr = useLocale().startsWith('tr');
  return (
    <div className="crm-people-tools-page" style={{ maxWidth: '100%' }} data-testid="crm-investors-tools">
      <Link href="/workspaces/crm/investors">{tr ? 'Yatırımcılara dön' : 'Back to investors'}</Link>
      <h1>{tr ? 'Yatırımcı araçları' : 'Investor tools'}</h1>
      <p>
        {tr
          ? 'AI Analizi, benzer kişiler ve klasik Yatırımcılar paneli birincil listeden ayrıldı. Müşteri verisini değiştirmez.'
          : 'AI analysis, similar people and the classic Investors panels were moved off the primary list.'}
      </p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Button type="button" variant="secondary" size="sm" disabled>
          {tr ? 'AI Analizi (ikincil)' : 'AI analysis (secondary)'}
        </Button>
        <Button type="button" variant="secondary" size="sm" disabled>
          {tr ? 'Benzer Kişiler (ikincil)' : 'Similar people (secondary)'}
        </Button>
      </div>
      <CrmInvestorsWorkspace />
    </div>
  );
}
