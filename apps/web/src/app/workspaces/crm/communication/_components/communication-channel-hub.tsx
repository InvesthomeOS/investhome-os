'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, Input, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

export type CommChannelKey = 'email' | 'calls' | 'sms' | 'whatsapp' | 'meetings';

export type ChannelActivityStatus = 'sent' | 'delivered' | 'failed' | 'scheduled' | 'completed' | 'missed';

export type ChannelActivity = {
  id: string;
  channel: CommChannelKey;
  subject: string;
  person: string;
  status: ChannelActivityStatus;
  when: string;
  preview: string;
};

const DEMO_ACTIVITIES: ChannelActivity[] = [
  {
    id: 'act-email-1',
    channel: 'email',
    subject: 'Marina Heights öneri paketi',
    person: 'Ahmet Yılmaz',
    status: 'delivered',
    when: '26.07.2026 09:40',
    preview: 'Görüşme özeti ve birim karşılaştırması eklendi.',
  },
  {
    id: 'act-email-2',
    channel: 'email',
    subject: 'Sözleşme taslağı',
    person: 'Elif Kaya',
    status: 'scheduled',
    when: '26.07.2026 14:00',
    preview: 'İmza öncesi son kontrol için planlandı.',
  },
  {
    id: 'act-call-1',
    channel: 'calls',
    subject: 'Takip araması',
    person: 'Can Özkan',
    status: 'completed',
    when: '25.07.2026 16:12',
    preview: 'Outbound · 4 dk · Connected',
  },
  {
    id: 'act-call-2',
    channel: 'calls',
    subject: 'Yatırımcı bilgilendirme',
    person: 'Nova Capital',
    status: 'missed',
    when: '25.07.2026 11:05',
    preview: 'Inbound · No answer',
  },
  {
    id: 'act-sms-1',
    channel: 'sms',
    subject: 'Randevu hatırlatma',
    person: 'Zeynep Arslan',
    status: 'delivered',
    when: '26.07.2026 08:15',
    preview: 'Yarın 11:00 showroom ziyareti.',
  },
  {
    id: 'act-sms-2',
    channel: 'sms',
    subject: 'Ödeme planı linki',
    person: 'Mehmet Kaya',
    status: 'failed',
    when: '24.07.2026 19:22',
    preview: 'Carrier rejected — invalid number.',
  },
  {
    id: 'act-wa-1',
    channel: 'whatsapp',
    subject: 'Birim fotoğrafları',
    person: 'Ayşe Demir',
    status: 'delivered',
    when: '26.07.2026 10:05',
    preview: '3 görsel + kısa not gönderildi.',
  },
  {
    id: 'act-wa-2',
    channel: 'whatsapp',
    subject: 'Teklif onayı',
    person: 'Horizon Partners',
    status: 'sent',
    when: '25.07.2026 20:40',
    preview: 'Onay bekleniyor.',
  },
  {
    id: 'act-mtg-1',
    channel: 'meetings',
    subject: 'Showroom turu',
    person: 'Ahmet Yılmaz',
    status: 'scheduled',
    when: '27.07.2026 11:00',
    preview: 'Marina Heights · 45 dk',
  },
  {
    id: 'act-mtg-2',
    channel: 'meetings',
    subject: 'Yatırımcı brifing',
    person: 'Nova Capital',
    status: 'completed',
    when: '22.07.2026 15:30',
    preview: 'Teams · Completed',
  },
];

const STATUS_TONE: Record<
  ChannelActivityStatus,
  'success' | 'warning' | 'info' | 'default' | 'danger'
> = {
  sent: 'info',
  delivered: 'success',
  failed: 'danger',
  scheduled: 'warning',
  completed: 'success',
  missed: 'danger',
};

const CHANNELS: CommChannelKey[] = ['email', 'calls', 'sms', 'whatsapp', 'meetings'];

export function CommunicationChannelHub() {
  const t = useTranslations('crm.communication.channelsHub');
  const [channel, setChannel] = useState<CommChannelKey>('email');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');

  const filtered = useMemo(() => {
    return DEMO_ACTIVITIES.filter((item) => {
      if (item.channel !== channel) return false;
      if (status && item.status !== status) return false;
      if (search) {
        const q = search.trim().toLowerCase();
        if (
          !item.subject.toLowerCase().includes(q) &&
          !item.person.toLowerCase().includes(q) &&
          !item.preview.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [channel, search, status]);

  return (
    <div className="crm-comm-hub" data-testid="crm-communication-channel-hub">
      <div className="crm-comm-hub__tabs" role="tablist" aria-label={t('tabsAria')}>
        {CHANNELS.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={channel === key}
            className={`crm-comm-hub__tab${channel === key ? ' is-active' : ''}`}
            onClick={() => setChannel(key)}
          >
            {t(`channels.${key}`)}
          </button>
        ))}
      </div>

      <section className="crm-comm-hub__toolbar" aria-label={t('filters.aria')}>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('filters.searchPlaceholder')}
          aria-label={t('filters.search')}
        />
        <Select value={status} onChange={(e) => setStatus(e.target.value)} aria-label={t('filters.status')}>
          <option value="">{t('filters.anyStatus')}</option>
          {(['sent', 'delivered', 'failed', 'scheduled', 'completed', 'missed'] as ChannelActivityStatus[]).map(
            (key) => (
              <option key={key} value={key}>
                {t(`status.${key}`)}
              </option>
            ),
          )}
        </Select>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            setSearch('');
            setStatus('');
          }}
        >
          {t('filters.clear')}
        </Button>
      </section>

      {filtered.length === 0 ? (
        <EmptyState title={t('empty.title')} description={t('empty.description')} />
      ) : (
        <ol className="crm-comm-hub__timeline" aria-label={t('timelineAria')}>
          {filtered.map((item) => (
            <li key={item.id} className="crm-comm-hub__item">
              <span className="crm-comm-hub__dot" aria-hidden="true" />
              <div className="crm-comm-hub__item-body">
                <div className="crm-comm-hub__item-top">
                  <strong>{item.subject}</strong>
                  <StatusChip tone={STATUS_TONE[item.status]}>{t(`status.${item.status}`)}</StatusChip>
                </div>
                <div className="crm-comm-hub__item-meta">
                  <span>
                    <IhIcon name="user" size={12} /> {item.person}
                  </span>
                  <time>{item.when}</time>
                </div>
                <p>{item.preview}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
