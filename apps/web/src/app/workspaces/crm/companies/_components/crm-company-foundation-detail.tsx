'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { EmptyState, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import { makeCompaniesPreview } from '../companies-demo-data';
import type { CompanyRow } from '../companies-model';
import {
  CrmDetailMetaGrid,
  CrmDetailPanel,
  CrmEntityDetailShell,
} from '../../_components/crm-entity-detail-shell';
import '../../_components/crm-entity-detail.css';
import '../companies.css';

const COMPANY_TABS = ['overview', 'contact', 'activity', 'notes'] as const;
type CompanyTab = (typeof COMPANY_TABS)[number];

export function findFoundationCompany(id: string): CompanyRow | null {
  return makeCompaniesPreview().companies.find((row) => row.id === id) ?? null;
}

export function CrmCompanyFoundationDetail({
  companyId,
  listHref = '/workspaces/crm/companies',
}: {
  companyId: string;
  listHref?: string;
}) {
  const t = useTranslations('crm.companies');
  const tDetail = useTranslations('crm.companyFoundationDetail');
  const [tab, setTab] = useState<CompanyTab>('overview');
  const company = useMemo(() => findFoundationCompany(companyId), [companyId]);

  if (!company) {
    return (
      <EmptyState title={tDetail('notFoundTitle')} description={tDetail('notFoundDescription')} />
    );
  }

  return (
    <CrmEntityDetailShell
      testId="crm-company-foundation-detail"
      backHref={listHref}
      backLabel={tDetail('back')}
      title={company.name}
      subtitle={t(`subtitles.${company.subtitleKey}`)}
      eyebrow={tDetail('eyebrow')}
      avatar={
        <span className={`crm-companies__logo is-${company.logoTone} is-md`} aria-hidden="true">
          {company.initials}
        </span>
      }
      tabs={COMPANY_TABS.map((id) => ({ id, label: tDetail(`tabs.${id}`) }))}
      activeTab={tab}
      onTabChange={(id) => setTab(id as CompanyTab)}
    >
      {tab === 'overview' ? (
        <CrmDetailPanel title={tDetail('tabs.overview')}>
          <CrmDetailMetaGrid
            items={[
              { label: t('table.category'), value: t(`category.${company.category}`) },
              { label: t('table.country'), value: t(`country.${company.country}`) },
              { label: t('table.openProjects'), value: String(company.openProjects) },
              { label: t('table.health'), value: `${company.healthScore} · ${t(`health.${company.health}`)}` },
              { label: t('filters.owner'), value: company.owner },
              { label: t('filters.status'), value: t(`status.${company.status}`) },
              { label: t('filters.relation'), value: t(`relation.${company.relation}`) },
            ]}
          />
          <p style={{ marginTop: 14 }}>{t(`aiSummaries.${company.aiSummaryKey}`)}</p>
        </CrmDetailPanel>
      ) : null}

      {tab === 'contact' ? (
        <CrmDetailPanel title={tDetail('tabs.contact')}>
          <div className="crm-companies__contact">
            <span className="crm-companies__avatar" aria-hidden="true">
              {company.contactInitials}
            </span>
            <div>
              <strong>{company.contactName}</strong>
              <span>{t(`roles.${company.contactRoleKey}`)}</span>
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <StatusChip tone="info">{t(`category.${company.category}`)}</StatusChip>
          </div>
        </CrmDetailPanel>
      ) : null}

      {tab === 'activity' ? (
        <CrmDetailPanel title={tDetail('tabs.activity')}>
          <ul className="crm-entity-detail__list">
            <li>
              <IhIcon name="activity" size={14} />
              <div>
                <strong>{t(`lastActivity.${company.lastActivityKey}`)}</strong>
                <time>{company.lastActivityDate}</time>
              </div>
            </li>
          </ul>
        </CrmDetailPanel>
      ) : null}

      {tab === 'notes' ? (
        <CrmDetailPanel title={tDetail('tabs.notes')}>
          <p>{t(`aiSummaries.${company.aiSummaryKey}`)}</p>
        </CrmDetailPanel>
      ) : null}
    </CrmEntityDetailShell>
  );
}
