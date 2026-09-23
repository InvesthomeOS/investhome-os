'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { EmptyState, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import { makePeoplePreview } from '../people-demo-data';
import type { PeopleRow } from '../people-model';
import {
  CrmDetailMetaGrid,
  CrmDetailPanel,
  CrmEntityDetailShell,
} from '../../_components/crm-entity-detail-shell';
import '../../_components/crm-entity-detail.css';
import '../people.css';

const PERSON_TABS = ['overview', 'company', 'activity', 'notes'] as const;
type PersonTab = (typeof PERSON_TABS)[number];

function findPerson(id: string): PeopleRow | null {
  return makePeoplePreview().people.find((row) => row.id === id) ?? null;
}

export function CrmPersonDetailView({
  personId,
  listHref = '/workspaces/crm/people',
}: {
  personId: string;
  listHref?: string;
}) {
  const t = useTranslations('crm.people');
  const tDetail = useTranslations('crm.personDetail');
  const [tab, setTab] = useState<PersonTab>('overview');
  const person = useMemo(() => findPerson(personId), [personId]);

  if (!person) {
    return (
      <EmptyState title={tDetail('notFoundTitle')} description={tDetail('notFoundDescription')} />
    );
  }

  return (
    <CrmEntityDetailShell
      testId="crm-person-detail"
      backHref={listHref}
      backLabel={tDetail('back')}
      title={person.name}
      subtitle={`${person.company} · ${t(`titles.${person.titleKey}`)}`}
      eyebrow={tDetail('eyebrow')}
      avatar={
        <span className={`crm-people__avatar is-${person.avatarTone} is-md`} aria-hidden="true">
          {person.initials}
        </span>
      }
      tabs={PERSON_TABS.map((id) => ({ id, label: tDetail(`tabs.${id}`) }))}
      activeTab={tab}
      onTabChange={(id) => setTab(id as PersonTab)}
    >
      {tab === 'overview' ? (
        <CrmDetailPanel title={tDetail('tabs.overview')}>
          <CrmDetailMetaGrid
            items={[
              { label: t('table.role'), value: t(`role.${person.role}`) },
              { label: t('table.department'), value: t(`department.${person.department}`) },
              { label: t('table.relation'), value: t(`relation.${person.relation}`) },
              { label: tDetail('score'), value: String(person.relationScore) },
              { label: t('filters.owner'), value: person.owner },
              { label: t('filters.country'), value: t(`country.${person.country}`) },
              {
                label: t('table.lastActivity'),
                value: `${t(`lastActivity.${person.lastActivityKey}`)} · ${person.lastActivityDate}`,
              },
            ]}
          />
          <p style={{ marginTop: 14 }}>{t(`aiNotes.${person.aiNoteKey}`)}</p>
        </CrmDetailPanel>
      ) : null}

      {tab === 'company' ? (
        <CrmDetailPanel title={tDetail('tabs.company')}>
          <div className="crm-people__company-cell" style={{ marginBottom: 12 }}>
            <span className={`crm-people__company-mark is-${person.companyTone}`} aria-hidden="true">
              {person.companyInitials}
            </span>
            <strong>{person.company}</strong>
          </div>
          <StatusChip tone="info">{t(`role.${person.role}`)}</StatusChip>
        </CrmDetailPanel>
      ) : null}

      {tab === 'activity' ? (
        <CrmDetailPanel title={tDetail('tabs.activity')}>
          <ul className="crm-entity-detail__list">
            <li>
              <IhIcon name="activity" size={14} />
              <div>
                <strong>{t(`lastActivity.${person.lastActivityKey}`)}</strong>
                <time>{person.lastActivityDate}</time>
              </div>
            </li>
          </ul>
        </CrmDetailPanel>
      ) : null}

      {tab === 'notes' ? (
        <CrmDetailPanel title={tDetail('tabs.notes')}>
          <p>{t(`aiNotes.${person.aiNoteKey}`)}</p>
        </CrmDetailPanel>
      ) : null}
    </CrmEntityDetailShell>
  );
}
