'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import { makeMatchesPreview } from '../matches-demo-data';
import type { MatchCard } from '../matches-model';
import {
  CrmDetailMetaGrid,
  CrmDetailPanel,
  CrmEntityDetailShell,
} from '../../_components/crm-entity-detail-shell';
import '../../_components/crm-entity-detail.css';
import '../matches.css';

const MATCH_TABS = [
  'overview',
  'customer',
  'project',
  'score',
  'documents',
  'timeline',
  'activities',
  'notes',
  'ai',
] as const;

type MatchTab = (typeof MATCH_TABS)[number];

function findMatch(id: string): { match: MatchCard; preview: ReturnType<typeof makeMatchesPreview> } | null {
  const preview = makeMatchesPreview();
  const match = preview.matches.find((item) => item.id === id);
  if (!match) return null;
  return { match, preview };
}

export function CrmMatchDetailView({
  matchId,
  listHref = '/workspaces/crm/matches',
}: {
  matchId: string;
  listHref?: string;
}) {
  const t = useTranslations('crm.matches');
  const tDetail = useTranslations('crm.matchDetail');
  const [tab, setTab] = useState<MatchTab>('overview');

  const resolved = useMemo(() => findMatch(matchId), [matchId]);

  if (!resolved) {
    return (
      <EmptyState
        title={tDetail('notFoundTitle')}
        description={tDetail('notFoundDescription')}
      />
    );
  }

  const { match, preview } = resolved;
  const { customer } = preview;

  const tabs = MATCH_TABS.map((id) => ({
    id,
    label: tDetail(`tabs.${id}`),
  }));

  return (
    <CrmEntityDetailShell
      testId="crm-match-detail"
      backHref={listHref}
      backLabel={tDetail('back')}
      title={match.projectName}
      subtitle={`${match.location} · ${match.developer}`}
      eyebrow={tDetail('eyebrow')}
      avatar={
        <span
          className="crm-entity-detail__score"
          style={{ ['--score' as string]: match.matchScore }}
          aria-label={`${t('scoreLabel')} ${match.matchScore}%`}
        >
          <span>{match.matchScore}%</span>
        </span>
      }
      tabs={tabs}
      activeTab={tab}
      onTabChange={(id) => setTab(id as MatchTab)}
    >
      {tab === 'overview' ? (
        <CrmDetailPanel title={tDetail('tabs.overview')}>
          <CrmDetailMetaGrid
            items={[
              { label: t('table.price'), value: match.price },
              { label: t('metrics.roi'), value: match.roi },
              { label: t('metrics.monthlyRent'), value: match.monthlyRent },
              { label: t('metrics.cashFlow'), value: match.monthlyCashFlow },
              { label: t('metrics.delivery'), value: match.deliveryDate },
              { label: t('statusLabel'), value: t(`status.${match.status}`) },
              { label: t('table.score'), value: `${match.matchScore}%` },
              { label: tDetail('unitType'), value: `${match.unitType} · ${match.area}` },
            ]}
          />
          <section style={{ marginTop: 16 }}>
            <h3 style={{ margin: '0 0 8px', fontSize: 13.2 }}>{t('whyTitle')}</h3>
            <ul className="crm-entity-detail__list">
              {match.whyKeys.map((key) => (
                <li key={key}>
                  <IhIcon name="check" size={14} />
                  <div>
                    <strong>{t(`why.${key}`)}</strong>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </CrmDetailPanel>
      ) : null}

      {tab === 'customer' ? (
        <CrmDetailPanel title={tDetail('tabs.customer')}>
          <CrmDetailMetaGrid
            items={[
              { label: tDetail('customerName'), value: customer.displayName },
              { label: tDetail('email'), value: customer.email },
              { label: tDetail('phone'), value: customer.phone },
              { label: t('customer.budget'), value: customer.budget },
              {
                label: t('customer.investmentGoal'),
                value: t(`customer.goals.${customer.investmentGoalKey}`),
              },
              { label: t('customer.preferredAreas'), value: customer.preferredAreas },
              {
                label: t('customer.riskProfile'),
                value: t(`customer.risk.${customer.riskProfileKey}`),
              },
              { label: t('customer.roiTarget'), value: customer.roiTarget },
            ]}
          />
        </CrmDetailPanel>
      ) : null}

      {tab === 'project' ? (
        <CrmDetailPanel title={tDetail('tabs.project')}>
          <CrmDetailMetaGrid
            items={[
              { label: t('table.project'), value: match.projectName },
              { label: tDetail('location'), value: match.location },
              { label: tDetail('developer'), value: match.developer },
              { label: tDetail('unitType'), value: match.unitType },
              { label: tDetail('area'), value: match.area },
              { label: t('metrics.delivery'), value: match.deliveryDate },
              { label: t('statusLabel'), value: t(`status.${match.status}`) },
            ]}
          />
        </CrmDetailPanel>
      ) : null}

      {tab === 'score' ? (
        <CrmDetailPanel title={tDetail('tabs.score')}>
          <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
            <span
              className="crm-entity-detail__score"
              style={{ ['--score' as string]: match.matchScore }}
            >
              <span>{match.matchScore}%</span>
            </span>
            <div>
              <p style={{ margin: 0, fontWeight: 650 }}>{t('scoreLabel')}</p>
              <p className="crm-entity-detail__empty" style={{ margin: '6px 0 0' }}>
                {tDetail('scoreHint')}
              </p>
            </div>
          </div>
          <ul className="crm-entity-detail__list" style={{ marginTop: 16 }}>
            {match.whyKeys.map((key) => (
              <li key={key}>
                <IhIcon name="sparkles" size={14} />
                <div>
                  <strong>{t(`why.${key}`)}</strong>
                  <span>{tDetail('scoreFactor')}</span>
                </div>
              </li>
            ))}
          </ul>
        </CrmDetailPanel>
      ) : null}

      {tab === 'documents' ? (
        <CrmDetailPanel title={tDetail('tabs.documents')}>
          <ul className="crm-entity-detail__list">
            {preview.documents.map((doc) => (
              <li key={doc.id}>
                <IhIcon name="documents" size={14} />
                <div>
                  <strong>{t(`rail.docNames.${doc.nameKey}`)}</strong>
                  <span>{t(`rail.docMeta.${doc.metaKey}`)}</span>
                </div>
              </li>
            ))}
          </ul>
        </CrmDetailPanel>
      ) : null}

      {tab === 'timeline' || tab === 'activities' ? (
        <CrmDetailPanel title={tDetail(`tabs.${tab}`)}>
          <ul className="crm-entity-detail__list">
            {preview.activities.map((item) => (
              <li key={item.id}>
                <IhIcon name="activity" size={14} />
                <div>
                  <strong>{t(`rail.activity.${item.titleKey}`)}</strong>
                  <time>{t(`rail.activity.${item.timeKey}`)}</time>
                </div>
              </li>
            ))}
          </ul>
        </CrmDetailPanel>
      ) : null}

      {tab === 'notes' ? (
        <CrmDetailPanel title={tDetail('tabs.notes')}>
          <p>{tDetail('notesBody', { project: match.projectName })}</p>
        </CrmDetailPanel>
      ) : null}

      {tab === 'ai' ? (
        <CrmDetailPanel title={tDetail('tabs.ai')}>
          <p>{t(`rail.summaries.${preview.recommendationSummaryKey}`)}</p>
          <ul className="crm-entity-detail__list" style={{ marginTop: 12 }}>
            {preview.riskAlerts.map((alert) => (
              <li key={alert.id}>
                <IhIcon name="alert" size={14} />
                <div>
                  <strong>{t(`rail.alerts.${alert.titleKey}`)}</strong>
                  <span>{t(`rail.alerts.${alert.bodyKey}`)}</span>
                </div>
              </li>
            ))}
          </ul>
        </CrmDetailPanel>
      ) : null}
    </CrmEntityDetailShell>
  );
}
