'use client';

import { useMemo, useState } from 'react';
import { useLocale } from 'next-intl';

import { StatusChip, type StatusChipTone } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { emailPreviewText, stripHtml } from '@/workspaces/crm/contact-card/history-html';

import {
  JOURNEY_TIMELINE_EVENTS,
  type JourneyActivityType,
  type JourneyEventKind,
  type JourneyEventStatus,
  type JourneyInternalSalesNote,
  type JourneyTimelineEvent,
} from './journey-timeline-model';

type TimelineFilter = 'all' | JourneyEventKind;
type SupportedLocale = 'en' | 'tr';

type TimelineLabels = {
  title: string;
  subtitle: string;
  filterLabel: string;
  filters: Record<TimelineFilter, string>;
  kinds: Record<JourneyEventKind, string>;
  activityTypes: Record<JourneyActivityType, string>;
  statuses: Record<JourneyEventStatus, string>;
  assignedTo: string;
  project: string;
  internalNote: string;
  privateTeamOnly: string;
  showMore: string;
  showLess: string;
  noEvents: string;
};

const LABELS: Record<SupportedLocale, TimelineLabels> = {
  en: {
    title: 'Journey timeline',
    subtitle: 'Customer touchpoints, team context, and local AI-ready summaries in one view.',
    filterLabel: 'Filter journey events',
    filters: {
      all: 'All activity',
      customer_communication: 'Customer communication',
      internal_observation: 'Internal observations',
      ai_generated: 'AI summaries',
    },
    kinds: {
      customer_communication: 'Customer communication',
      internal_observation: 'Internal observation',
      ai_generated: 'AI-generated summary',
    },
    activityTypes: {
      call: 'Call',
      whatsapp: 'WhatsApp',
      email: 'Email',
      meeting: 'Meeting',
      proposal: 'Proposal',
      reservation: 'Reservation',
      contract: 'Contract',
      payment: 'Payment',
      document: 'Document',
      internal_note: 'Internal Note',
      ai_summary: 'AI Summary',
      follow_up_task: 'Follow-up Task',
      reminder: 'Reminder',
    },
    statuses: {
      completed: 'Completed',
      sent: 'Sent',
      scheduled: 'Scheduled',
      due: 'Due today',
      pending: 'Pending',
      signed: 'Signed',
      paid: 'Paid',
    },
    assignedTo: 'Assigned to',
    project: 'Related project',
    internalNote: 'Internal Note',
    privateTeamOnly: 'Private · team only',
    showMore: 'Show full note',
    showLess: 'Collapse note',
    noEvents: 'No events match this filter.',
  },
  tr: {
    title: 'Müşteri yolculuğu',
    subtitle: 'Müşteri temasları, ekip bağlamı ve yerel yapay zekâya hazır özetler tek görünümde.',
    filterLabel: 'Yolculuk olaylarını filtrele',
    filters: {
      all: 'Tüm aktiviteler',
      customer_communication: 'Müşteri iletişimi',
      internal_observation: 'Dahili gözlemler',
      ai_generated: 'YZ özetleri',
    },
    kinds: {
      customer_communication: 'Müşteri iletişimi',
      internal_observation: 'Dahili gözlem',
      ai_generated: 'YZ tarafından oluşturulan özet',
    },
    activityTypes: {
      call: 'Arama',
      whatsapp: 'WhatsApp',
      email: 'E-posta',
      meeting: 'Toplantı',
      proposal: 'Teklif',
      reservation: 'Rezervasyon',
      contract: 'Sözleşme',
      payment: 'Ödeme',
      document: 'Belge',
      internal_note: 'Dahili Not',
      ai_summary: 'YZ Özeti',
      follow_up_task: 'Takip Görevi',
      reminder: 'Hatırlatma',
    },
    statuses: {
      completed: 'Tamamlandı',
      sent: 'Gönderildi',
      scheduled: 'Planlandı',
      due: 'Bugün',
      pending: 'Bekliyor',
      signed: 'İmzalandı',
      paid: 'Ödendi',
    },
    assignedTo: 'Atanan',
    project: 'İlgili proje',
    internalNote: 'Dahili Not',
    privateTeamOnly: 'Özel · yalnızca ekip',
    showMore: 'Notun tamamını göster',
    showLess: 'Notu daralt',
    noEvents: 'Bu filtreyle eşleşen olay yok.',
  },
};

const ACTIVITY_ICONS: Record<JourneyActivityType, IhIconName> = {
  call: 'activity',
  whatsapp: 'inbox',
  email: 'inbox',
  meeting: 'meeting',
  proposal: 'documents',
  reservation: 'calendar',
  contract: 'documents',
  payment: 'finance',
  document: 'documents',
  internal_note: 'user',
  ai_summary: 'sparkles',
  follow_up_task: 'check',
  reminder: 'bell',
};

const STATUS_TONES: Record<JourneyEventStatus, StatusChipTone> = {
  completed: 'success',
  sent: 'info',
  scheduled: 'info',
  due: 'warning',
  pending: 'warning',
  signed: 'success',
  paid: 'success',
};

const FILTERS: readonly TimelineFilter[] = [
  'all',
  'customer_communication',
  'internal_observation',
  'ai_generated',
];

const PROFILE_EVENT_IDS = [
  'journey-follow-up',
  'journey-proposal',
  'journey-viewing',
  'journey-call',
] as const;

const PROFILE_EVENT_TITLES: Record<(typeof PROFILE_EVENT_IDS)[number], Record<SupportedLocale, string>> = {
  'journey-follow-up': { en: 'Follow up proposal', tr: 'Teklif takibi' },
  'journey-proposal': { en: 'Proposal sent – North Towers A-1204', tr: 'Teklif gönderildi – North Towers A-1204' },
  'journey-viewing': { en: 'Unit viewed – North Towers A-1204', tr: 'Ünite görüntülendi – North Towers A-1204' },
  'journey-call': { en: 'Intro call', tr: 'Tanışma araması' },
};

function InternalNote({
  note,
  labels,
  locale,
}: {
  note: JourneyInternalSalesNote;
  labels: TimelineLabels;
  locale: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const isLong = note.body.length > 120;
  const panelId = `journey-note-${note.id}`;

  return (
    <aside className="crm-journey__internal-note" aria-label={labels.internalNote}>
      <div className="crm-journey__note-heading">
        <div>
          <span className="crm-journey__note-label">{labels.internalNote}</span>
          <span className="crm-journey__private-label">{labels.privateTeamOnly}</span>
        </div>
        <div className="crm-journey__note-author">
          <span className="crm-journey__avatar" aria-hidden="true">
            {note.author.initials}
          </span>
          <span>{note.author.name}</span>
          <time dateTime={note.createdAt}>
            {new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(
              new Date(note.createdAt),
            )}
          </time>
        </div>
      </div>
      <p
        id={panelId}
        className={
          expanded ? 'crm-journey__note-body crm-journey__note-body--expanded' : 'crm-journey__note-body'
        }
      >
        {note.body}
      </p>
      {isLong ? (
        <button
          type="button"
          className="crm-journey__note-toggle"
          aria-expanded={expanded}
          aria-controls={panelId}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? labels.showLess : labels.showMore}
          <IhIcon name={expanded ? 'chevronLeft' : 'chevronRight'} size={14} />
        </button>
      ) : null}
    </aside>
  );
}

function JourneyEventCard({
  event,
  labels,
  locale,
  canViewInternalNotes,
}: {
  event: JourneyTimelineEvent;
  labels: TimelineLabels;
  locale: string;
  canViewInternalNotes: boolean;
}) {
  const dateTime = new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(event.occurredAt));

  return (
    <li className={`crm-journey__event crm-journey__event--${event.kind}`}>
      <span className="crm-journey__rail" aria-hidden="true">
        <span className="crm-journey__marker">
          <IhIcon name={ACTIVITY_ICONS[event.activityType]} size={18} />
        </span>
      </span>
      <article className="crm-journey__event-card">
        <div className="crm-journey__event-topline">
          <div className="crm-journey__event-title">
            <span className="crm-journey__kind-label">{labels.kinds[event.kind]}</span>
            <h3>{labels.activityTypes[event.activityType]}</h3>
          </div>
          <div className="crm-journey__event-status">
            <StatusChip tone={STATUS_TONES[event.status]}>{labels.statuses[event.status]}</StatusChip>
            <time dateTime={event.occurredAt}>{dateTime}</time>
          </div>
        </div>
        <p className="crm-journey__summary">{emailPreviewText(event.summary)}</p>
        <dl className="crm-journey__meta">
          <div>
            <dt>{labels.assignedTo}</dt>
            <dd>
              <span className="crm-journey__avatar" aria-hidden="true">
                {event.assignedTo.initials}
              </span>
              {event.assignedTo.name}
            </dd>
          </div>
          {event.relatedProject ? (
            <div>
              <dt>{labels.project}</dt>
              <dd>{event.relatedProject}</dd>
            </div>
          ) : null}
        </dl>
        {canViewInternalNotes && event.internalSalesNote ? (
          <InternalNote note={event.internalSalesNote} labels={labels} locale={locale} />
        ) : null}
      </article>
    </li>
  );
}

export function ContactJourneyTimeline({
  canViewInternalNotes,
  variant = 'full',
  localeOverride,
  onViewFullJourney,
}: {
  canViewInternalNotes: boolean;
  variant?: 'full' | 'profile';
  localeOverride?: SupportedLocale;
  onViewFullJourney?: () => void;
}) {
  const locale = useLocale();
  const supportedLocale: SupportedLocale = localeOverride ?? (locale.startsWith('tr') ? 'tr' : 'en');
  const formatLocale = localeOverride ?? locale;
  const labels = LABELS[supportedLocale];
  const [filter, setFilter] = useState<TimelineFilter>('all');
  const [expandedProfileEventId, setExpandedProfileEventId] = useState<string | null>(null);
  const visibleEvents = useMemo(
    () => (filter === 'all' ? JOURNEY_TIMELINE_EVENTS : JOURNEY_TIMELINE_EVENTS.filter((event) => event.kind === filter)),
    [filter],
  );

  if (variant === 'profile') {
    const profileEvents =
      filter === 'all'
        ? PROFILE_EVENT_IDS.map((eventId) => JOURNEY_TIMELINE_EVENTS.find((event) => event.id === eventId)).filter(
            (event): event is JourneyTimelineEvent => Boolean(event),
          )
        : visibleEvents.slice(0, 4);

    return (
      <section className="crm-journey crm-journey--profile" aria-labelledby="crm-profile-journey-title">
        <header className="crm-journey__profile-header">
          <h2 id="crm-profile-journey-title">{labels.title}</h2>
          <label>
            <span className="sr-only">{labels.filterLabel}</span>
            <select
              value={filter}
              onChange={(event) => {
                setFilter(event.target.value as TimelineFilter);
                setExpandedProfileEventId(null);
              }}
            >
              {FILTERS.map((filterId) => (
                <option key={filterId} value={filterId}>{labels.filters[filterId]}</option>
              ))}
            </select>
          </label>
        </header>

        <ol className="crm-journey__profile-list">
          {profileEvents.map((event) => {
            const expanded = expandedProfileEventId === event.id;
            const detailId = `profile-journey-detail-${event.id}`;
            const profileTitle =
              event.id in PROFILE_EVENT_TITLES
                ? PROFILE_EVENT_TITLES[event.id as keyof typeof PROFILE_EVENT_TITLES][supportedLocale]
                : labels.activityTypes[event.activityType];
            return (
              <li key={event.id} className={`crm-journey__profile-event crm-journey__profile-event--${event.kind}`}>
                <span className="crm-journey__profile-marker" aria-hidden="true">
                  <IhIcon name={ACTIVITY_ICONS[event.activityType]} size={14} />
                </span>
                <div className="crm-journey__profile-content">
                  <div className="crm-journey__profile-title-row">
                    <button
                      type="button"
                      aria-expanded={expanded}
                      aria-controls={detailId}
                      onClick={() => setExpandedProfileEventId(expanded ? null : event.id)}
                    >
                      {profileTitle}
                    </button>
                    {event.status === 'due' ? (
                      <span className="crm-journey__profile-status">{labels.statuses[event.status]}</span>
                    ) : null}
                    <time dateTime={event.occurredAt}>
                      {new Intl.DateTimeFormat(formatLocale, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      }).format(new Date(event.occurredAt))}
                    </time>
                  </div>
                  <div className="crm-journey__profile-meta">
                    <span>{labels.activityTypes[event.activityType]}</span>
                    <span>·</span>
                    <span>{labels.assignedTo} {event.assignedTo.name}</span>
                    {event.kind === 'ai_generated' ? <span className="crm-journey__profile-ai">{labels.kinds.ai_generated}</span> : null}
                    {canViewInternalNotes && event.internalSalesNote ? (
                      <span className="crm-journey__profile-note-available">{labels.internalNote}</span>
                    ) : null}
                  </div>
                  {expanded ? (
                    <div id={detailId} className="crm-journey__profile-detail">
                      <p>{stripHtml(event.summary)}</p>
                      <dl>
                        <div><dt>{labels.statuses[event.status]}</dt><dd>{event.relatedProject ?? '—'}</dd></div>
                      </dl>
                      {canViewInternalNotes && event.internalSalesNote ? (
                        <InternalNote note={event.internalSalesNote} labels={labels} locale={formatLocale} />
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ol>
        <button type="button" className="crm-journey__profile-footer" onClick={onViewFullJourney}>
          {supportedLocale === 'tr' ? 'Tüm yolculuğu görüntüle' : 'View full journey'}
        </button>
      </section>
    );
  }

  return (
    <section className="crm-journey" aria-labelledby="crm-journey-title">
      <header className="crm-journey__header">
        <div>
          <p className="company-workspace__eyebrow">{labels.kinds.customer_communication}</p>
          <h2 id="crm-journey-title">{labels.title}</h2>
          <p>{labels.subtitle}</p>
        </div>
        <span className="crm-journey__count" aria-label={`${visibleEvents.length} events`}>
          {visibleEvents.length}
        </span>
      </header>

      <div className="crm-journey__filters" role="group" aria-label={labels.filterLabel}>
        {FILTERS.map((filterId) => (
          <button
            key={filterId}
            type="button"
            className={filter === filterId ? 'crm-journey__filter crm-journey__filter--active' : 'crm-journey__filter'}
            aria-pressed={filter === filterId}
            onClick={() => setFilter(filterId)}
          >
            {labels.filters[filterId]}
          </button>
        ))}
      </div>

      <div className="crm-journey__legend" aria-label={labels.filterLabel}>
        {(['customer_communication', 'internal_observation', 'ai_generated'] as const).map((kind) => (
          <span key={kind} className={`crm-journey__legend-item crm-journey__legend-item--${kind}`}>
            <span aria-hidden="true" />
            {labels.kinds[kind]}
          </span>
        ))}
      </div>

      {visibleEvents.length > 0 ? (
        <ol className="crm-journey__list">
          {visibleEvents.map((event) => (
            <JourneyEventCard
              key={event.id}
              event={event}
              labels={labels}
              locale={formatLocale}
              canViewInternalNotes={canViewInternalNotes}
            />
          ))}
        </ol>
      ) : (
        <p className="crm-journey__empty">{labels.noEvents}</p>
      )}
    </section>
  );
}
