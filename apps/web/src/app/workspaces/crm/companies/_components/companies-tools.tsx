'use client';

import Link from 'next/link';
import { useLocale } from 'next-intl';

import { Button } from '@investhome/ui';

import { CrmCompaniesWorkspace } from './crm-companies-workspace';

import '../../contacts/_components/people-workspace.css';

export function CompaniesToolsPage() {
  const tr = useLocale().startsWith('tr');
  return (
    <div className="crm-people-tools-page" data-testid="crm-companies-tools">
      <Link href="/workspaces/crm/companies">{tr ? 'Şirketlere dön' : 'Back to companies'}</Link>
      <h1>{tr ? 'Şirket araçları' : 'Company tools'}</h1>
      <p>
        {tr
          ? 'AI Analizi, benzer şirketler ve klasik Şirketler paneli birincil listeden ayrıldı. Müşteri verisini değiştirmez.'
          : 'AI analysis, similar companies and the classic Companies panels were moved off the primary list.'}
      </p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Link href="/workspaces/crm/companies/new" className="ih-btn ih-btn--secondary">
          {tr ? 'Yeni şirket' : 'New company'}
        </Link>
        <Link href="/workspaces/crm/companies/import" className="ih-btn ih-btn--secondary">
          {tr ? 'İçe aktar' : 'Import'}
        </Link>
        <Button type="button" variant="secondary" size="sm" disabled>
          {tr ? 'AI Analizi (ikincil)' : 'AI analysis (secondary)'}
        </Button>
      </div>
      <CrmCompaniesWorkspace />
    </div>
  );
}
