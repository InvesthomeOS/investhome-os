'use client';

import type { ReactNode } from 'react';
import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Drawer, Tabs } from '@investhome/ui';

export type CrmRecordDrawerSectionId =
  | 'summary'
  | 'timeline'
  | 'nextAction'
  | 'customer'
  | 'proposal'
  | 'reservation'
  | 'notes'
  | 'activities'
  | 'emails'
  | 'tasks'
  | 'documents'
  | 'ai'
  | 'projects'
  | 'investors';

export type CrmRecordDrawerProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  badge?: ReactNode;
  summary: ReactNode;
  sections?: Partial<Record<CrmRecordDrawerSectionId, ReactNode>>;
  footer?: ReactNode;
  wide?: boolean;
};

const SECTION_ORDER: CrmRecordDrawerSectionId[] = [
  'summary',
  'timeline',
  'nextAction',
  'customer',
  'proposal',
  'reservation',
  'notes',
  'activities',
  'emails',
  'tasks',
  'documents',
  'ai',
  'projects',
  'investors',
];

/** Twenty-inspired slide-over record drawer — original Investhome UI, no AGPL source. */
export function CrmRecordDrawer({
  open,
  onClose,
  title,
  subtitle,
  badge,
  summary,
  sections = {},
  footer,
  wide = true,
}: CrmRecordDrawerProps) {
  const t = useTranslations('crm.g2.drawer');
  const available = SECTION_ORDER.filter((id) => id === 'summary' || sections[id] != null);
  const [active, setActive] = useState<string>('summary');

  const tabs = available.map((id) => ({
    id,
    label: t(id as 'summary'),
  }));

  return (
    <Drawer open={open} onClose={onClose} title={title} footer={footer} wide={wide} ariaLabel={title}>
      <div className="crm-g2-drawer" data-testid="crm-g2-drawer">
        <div className="crm-g2-drawer__hero">
          {badge ? <div className="crm-g2-drawer__badge">{badge}</div> : null}
          {subtitle ? <p className="crm-g2-drawer__subtitle">{subtitle}</p> : null}
        </div>

        <Tabs activeId={active} onChange={setActive} tabs={tabs} />

        <div className="crm-g2-drawer__body">
          {active === 'summary' ? summary : null}
          {active !== 'summary' && sections[active as CrmRecordDrawerSectionId]
            ? sections[active as CrmRecordDrawerSectionId]
            : null}
          {active !== 'summary' && !sections[active as CrmRecordDrawerSectionId] ? (
            <p className="crm-g2-drawer__empty">{t('emptySection')}</p>
          ) : null}
        </div>
      </div>
    </Drawer>
  );
}

export function CrmDrawerField({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="crm-g2-drawer__field">
      <dt>{label}</dt>
      <dd>{value ?? '—'}</dd>
    </div>
  );
}
