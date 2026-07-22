'use client';

import { useState } from 'react';

import { BrandLogo } from '@/components/brand/brand-logo';

import { MarketingAnalyticsTab } from './MarketingAnalyticsTab';
import { ProjectOpsTab } from './ProjectOpsTab';
import { SalesPipelineTab } from './SalesPipelineTab';

type TabId = 'sales' | 'projects' | 'marketing';

const TABS: { id: TabId; label: string; testId: string }[] = [
  { id: 'sales', label: 'Satış Pipeline', testId: 'g1-tab-sales' },
  { id: 'projects', label: 'Proje Operasyonları', testId: 'g1-tab-projects' },
  { id: 'marketing', label: 'Pazarlama Analitiği', testId: 'g1-tab-marketing' },
];

export function GithubUiPreview() {
  const [tab, setTab] = useState<TabId>('sales');

  return (
    <div className="g1-preview" data-testid="github-ui-preview">
      <header className="g1-preview__top">
        <div className="g1-preview__brand">
          <BrandLogo layout="full" tone="color" />
          <div className="g1-preview__brand-text">
            <strong>Investhome OS</strong>
            <span>GitHub ürün UI önizlemesi · G1 (yalnızca demo)</span>
          </div>
          <span className="g1-preview__badge">Admin · salt okunur demo</span>
        </div>
        <nav className="g1-preview__tabs" aria-label="Önizleme sekmeleri">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`g1-preview__tab${tab === t.id ? ' g1-preview__tab--active' : ''}`}
              onClick={() => setTab(t.id)}
              data-testid={t.testId}
              aria-current={tab === t.id ? 'page' : undefined}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <div className="g1-preview__body">
        {tab === 'sales' ? <SalesPipelineTab /> : null}
        {tab === 'projects' ? <ProjectOpsTab /> : null}
        {tab === 'marketing' ? <MarketingAnalyticsTab /> : null}
      </div>
    </div>
  );
}
