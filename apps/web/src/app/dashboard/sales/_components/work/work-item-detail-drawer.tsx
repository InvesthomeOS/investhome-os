'use client';

import { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, Drawer, Tabs } from '@investhome/ui';

import type { WorkItem } from '@/lib/api/work-items';
import { useWorkItemLabels } from '@/lib/i18n/work-item-labels';

interface WorkItemDetailDrawerProps {
  item: WorkItem | null;
  open: boolean;
  onClose: () => void;
  onComplete: (item: WorkItem) => void;
  onEdit: (item: WorkItem) => void;
}

function formatDate(value: string | null, locale: string) {
  if (!value) return '—';
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

export function WorkItemDetailDrawer({ item, open, onClose, onComplete, onEdit }: WorkItemDetailDrawerProps) {
  const t = useTranslations('work');
  const locale = useLocale();
  const { getTypeLabel, getStatusLabel, getPriorityLabel } = useWorkItemLabels();
  const [activeTab, setActiveTab] = useState('overview');

  if (!item || !open) return null;

  const tabs = [
    { id: 'overview', label: t('tabs.overview') },
    { id: 'meeting', label: t('tabs.meeting') },
    { id: 'followUp', label: t('tabs.followUp') },
    { id: 'related', label: t('tabs.related') },
    { id: 'outcome', label: t('tabs.outcome') },
  ];

  return (
    <Drawer open onClose={onClose} title={item.title}>
      <div className="sales-work-drawer">
        <div className="sales-work-drawer__actions">
          {item.status !== 'completed' && item.status !== 'cancelled' && (
            <>
              <Button variant="primary" onClick={() => onComplete(item)}>
                {t('actions.complete')}
              </Button>
              <Button variant="secondary" onClick={() => onEdit(item)}>
                {t('actions.edit')}
              </Button>
            </>
          )}
        </div>
        <Tabs tabs={tabs} activeId={activeTab} onChange={setActiveTab} />
        {activeTab === 'overview' && (
          <dl className="sales-work-drawer__fields">
            <div><dt>{t('fields.type')}</dt><dd>{getTypeLabel(item.work_item_type)}</dd></div>
            <div><dt>{t('fields.status')}</dt><dd>{getStatusLabel(item.effective_status ?? item.status)}</dd></div>
            <div><dt>{t('fields.priority')}</dt><dd>{getPriorityLabel(item.priority)}</dd></div>
            <div><dt>{t('fields.due')}</dt><dd>{formatDate(item.due_at, locale)}</dd></div>
            <div><dt>{t('fields.description')}</dt><dd>{item.description ?? '—'}</dd></div>
          </dl>
        )}
        {activeTab === 'meeting' && item.meeting && (
          <dl className="sales-work-drawer__fields">
            <div><dt>{t('fields.meetingType')}</dt><dd>{item.meeting.meeting_type}</dd></div>
            <div><dt>{t('fields.location')}</dt><dd>{item.meeting.location ?? '—'}</dd></div>
            <div><dt>{t('fields.meetingUrl')}</dt><dd>{item.meeting.meeting_url ?? '—'}</dd></div>
            <div><dt>{t('fields.agenda')}</dt><dd>{item.meeting.agenda ?? '—'}</dd></div>
            <p className="sales-work-drawer__hint">{t('meetingUrlHint')}</p>
          </dl>
        )}
        {activeTab === 'followUp' && item.follow_up && (
          <dl className="sales-work-drawer__fields">
            <div><dt>{t('fields.contactMethod')}</dt><dd>{item.follow_up.contact_method}</dd></div>
            <div><dt>{t('fields.responseStatus')}</dt><dd>{item.follow_up.response_status}</dd></div>
            <div><dt>{t('fields.notes')}</dt><dd>{item.follow_up.notes ?? '—'}</dd></div>
          </dl>
        )}
        {activeTab === 'related' && (
          <dl className="sales-work-drawer__fields">
            {item.lead_id && <div><dt>{t('fields.lead')}</dt><dd>{item.lead_id}</dd></div>}
            {item.opportunity_id && <div><dt>{t('fields.opportunity')}</dt><dd>{item.opportunity_id}</dd></div>}
            {item.proposal_id && <div><dt>{t('fields.proposal')}</dt><dd>{item.proposal_id}</dd></div>}
          </dl>
        )}
        {activeTab === 'outcome' && <p>{item.outcome ?? t('noOutcome')}</p>}
      </div>
    </Drawer>
  );
}
