'use client';

import type { FormEvent } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Route } from 'next';
import Link from 'next/link';
import { useLocale } from 'next-intl';
import { usePathname, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { canViewPrivateNotes } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { emailPreviewText } from '@/workspaces/crm/contact-card/history-html';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { CrmContactDetail } from '@/workspaces/crm/types';
import type {
  CrmActivityCategory,
  CrmActivityDetail,
  CrmActivityStatus,
  CrmActivityType,
} from '@/workspaces/crm/types/activities';

import { ActivityDetailPanel } from '../../_components/activity-detail-panel';
import { CRM_EVENT_IDENTITIES, getCrmEventIdentity } from './crm-event-identity';
import {
  JOURNEY_TIMELINE_EVENTS,
  type JourneyActivityType,
  type JourneyEventStatus,
  type JourneyTimelineEvent,
} from './journey-timeline-model';

type ContactJourneyWorkspacePreview = {
  contact: CrmContactDetail;
  canViewInternalNotes?: boolean;
  enableDebugStates?: boolean;
  contactHref?: Route;
};

type ContactJourneyWorkspaceProps = {
  contactId: string;
  preview?: ContactJourneyWorkspacePreview;
};

type WorkspaceState = 'ready' | 'loading' | 'error' | 'empty';

const PAGE_SIZE = 6;

const STATUS_LABELS: Record<JourneyEventStatus, string> = {
  completed: 'Completed',
  sent: 'Sent',
  scheduled: 'Scheduled',
  due: 'Due today',
  pending: 'Pending',
  signed: 'Signed',
  paid: 'Paid',
};

const AI_ACTIONS = [
  'Summarize Journey',
  'Detect Risks',
  'Next Best Action',
  'Missing Follow-up',
  'Buying Signals',
] as const;

function eventTitle(event: JourneyTimelineEvent): string {
  if (event.id === 'journey-follow-up') return 'Follow up proposal';
  if (event.id === 'journey-proposal') return 'Proposal sent – North Towers A-1204';
  if (event.id === 'journey-viewing') return 'Unit viewed – North Towers A-1204';
  if (event.id === 'journey-call') return 'Intro call';
  return getCrmEventIdentity(event.activityType).label;
}

function relativeFixtureActivity(
  event: JourneyTimelineEvent | undefined,
  anchor: JourneyTimelineEvent | undefined,
  locale: string,
): string {
  if (!event || !anchor) return 'No recent activity';
  const eventDate = new Date(event.occurredAt);
  const anchorDate = new Date(anchor.occurredAt);
  const eventDay = Date.UTC(eventDate.getUTCFullYear(), eventDate.getUTCMonth(), eventDate.getUTCDate());
  const anchorDay = Date.UTC(anchorDate.getUTCFullYear(), anchorDate.getUTCMonth(), anchorDate.getUTCDate());
  const dayDifference = Math.max(0, Math.round((anchorDay - eventDay) / 86_400_000));
  const relative = dayDifference === 0 ? 'Today' : dayDifference === 1 ? 'Yesterday' : `${dayDifference} days ago`;
  const time = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(eventDate);
  return `${relative} · ${time}`;
}

function mapActivityType(activityType: JourneyActivityType): CrmActivityType {
  const map: Record<JourneyActivityType, CrmActivityType> = {
    call: 'phone_call',
    whatsapp: 'whatsapp',
    email: 'email',
    meeting: 'meeting',
    proposal: 'proposal_sent',
    reservation: 'reservation',
    contract: 'contract_signed',
    payment: 'payment',
    document: 'document_sent',
    internal_note: 'note',
    ai_summary: 'system_event',
    follow_up_task: 'follow_up',
    reminder: 'reminder',
  };
  return map[activityType];
}

function mapActivityCategory(activityType: JourneyActivityType): CrmActivityCategory {
  if (['call', 'whatsapp', 'email'].includes(activityType)) return 'communication';
  if (activityType === 'meeting') return 'meeting';
  if (['follow_up_task', 'reminder'].includes(activityType)) return 'follow_up';
  if (activityType === 'internal_note') return 'note';
  if (['proposal', 'contract', 'document'].includes(activityType)) return 'document';
  if (['reservation', 'payment'].includes(activityType)) return 'transaction';
  if (activityType === 'ai_summary') return 'system';
  return 'other';
}

function mapActivityStatus(status: JourneyEventStatus): CrmActivityStatus {
  if (status === 'scheduled' || status === 'due') return 'scheduled';
  if (status === 'pending') return 'planned';
  return 'completed';
}

function toActivityDetail(
  event: JourneyTimelineEvent,
  contactId: string,
  canViewInternalNotes: boolean,
): CrmActivityDetail {
  const activityType = mapActivityType(event.activityType);
  const status = mapActivityStatus(event.status);
  return {
    id: event.id,
    entity_type: 'contact',
    entity_id: contactId,
    related_entity_type: event.relatedProject ? 'project' : null,
    related_entity_id: event.relatedProject ? `local-${event.relatedProject.toLowerCase().replaceAll(' ', '-')}` : null,
    activity_type: activityType,
    activity_category: mapActivityCategory(event.activityType),
    title: eventTitle(event),
    summary: event.summary,
    status,
    task_status: activityType === 'follow_up' ? 'not_started' : null,
    priority: event.status === 'due' ? 'high' : 'medium',
    owner_id: event.assignedTo.id,
    assigned_user_id: event.assignedTo.id,
    assigned_team_id: null,
    start_date: event.occurredAt,
    end_date: null,
    due_date: event.status === 'due' || event.status === 'scheduled' ? event.occurredAt : null,
    completed_at: status === 'completed' ? event.occurredAt : null,
    reminder_date: event.activityType === 'reminder' ? event.occurredAt : null,
    timezone: 'Europe/Istanbul',
    location: event.activityType === 'meeting' ? 'North Towers sales gallery' : null,
    meeting_url: null,
    tags: [event.kind],
    visibility: event.kind === 'internal_observation' ? 'team' : 'organization',
    is_pinned: event.status === 'due',
    is_favorite: false,
    follow_up_reason: activityType === 'follow_up' ? 'opportunity' : null,
    created_at: event.occurredAt,
    updated_at: event.occurredAt,
    created_by: event.assignedTo.id,
    archived_at: null,
    has_attachments: Boolean(event.attachment),
    comment_count: canViewInternalNotes && event.internalSalesNote ? 1 : 0,
    description: event.summary,
    outcome: null,
    duration_minutes: event.activityType === 'call' ? 12 : null,
    estimated_duration_minutes: null,
    actual_duration_minutes: null,
    recurrence_frequency: null,
    recurrence_rule: null,
    metadata_json: null,
    entity_links: [],
    checklist_items: [],
    attachments: event.attachment
      ? [
          {
            id: `attachment-${event.id}`,
            file_name: event.attachment.fileName,
            file_url: null,
            mime_type: 'application/pdf',
            file_size_bytes: null,
            document_id: null,
            created_at: event.occurredAt,
          },
        ]
      : [],
    reminders: [],
    comments:
      canViewInternalNotes && event.internalSalesNote
        ? [
            {
              id: event.internalSalesNote.id,
              parent_id: null,
              body: event.internalSalesNote.body,
              mentions: null,
              reactions: null,
              created_by: event.internalSalesNote.author.id,
              created_at: event.internalSalesNote.createdAt,
              updated_at: null,
            },
          ]
        : [],
  };
}

function JourneyActivityDetail({
  event,
  contactId,
  canViewInternalNotes,
  onClose,
}: {
  event: JourneyTimelineEvent;
  contactId: string;
  canViewInternalNotes: boolean;
  onClose: () => void;
}) {
  const activity = useMemo(
    () => toActivityDetail(event, contactId, canViewInternalNotes),
    [canViewInternalNotes, contactId, event],
  );

  return (
    <div className="journey-workspace__detail-shell">
      <ActivityDetailPanel activity={activity} loading={false} onClose={onClose} />
      <div className="journey-workspace__detail-indicators" aria-label="Activity indicators">
        {canViewInternalNotes && event.internalSalesNote ? (
          <span><IhIcon name="user" size={14} />Private team note</span>
        ) : null}
        {event.attachment ? (
          <span><IhIcon name="documents" size={14} />Attachment: {event.attachment.fileName}</span>
        ) : null}
      </div>
    </div>
  );
}

function ContactJourneyWorkspacePresentation({
  contact,
  canViewInternalNotes,
  enableDebugStates = false,
  contactHref,
}: {
  contact: CrmContactDetail;
  canViewInternalNotes: boolean;
  enableDebugStates?: boolean;
  contactHref?: Route;
}) {
  const locale = useLocale();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [selectedEvent, setSelectedEvent] = useState<JourneyTimelineEvent | null>(null);
  const [isDrawerClosing, setIsDrawerClosing] = useState(false);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const closeTimerRef = useRef<number | null>(null);
  const dateFormatter = useMemo(
    () => new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }),
    [locale],
  );

  const search = searchParams.get('q')?.trim().toLowerCase() ?? '';
  const dateFrom = searchParams.get('from') ?? '';
  const dateTo = searchParams.get('to') ?? '';
  const activityType = searchParams.get('type') ?? '';
  const memberId = searchParams.get('member') ?? '';
  const project = searchParams.get('project') ?? '';
  const requestedPage = Number.parseInt(searchParams.get('page') ?? '1', 10);
  const page = Number.isFinite(requestedPage) && requestedPage > 0 ? requestedPage : 1;
  const debugState = enableDebugStates ? searchParams.get('state') : null;
  const workspaceState: WorkspaceState =
    debugState === 'loading' || debugState === 'error' || debugState === 'empty' ? debugState : 'ready';
  const effectiveCanViewInternalNotes =
    canViewInternalNotes && !(enableDebugStates && searchParams.get('notes') === 'hidden');

  const teamMembers = useMemo(
    () =>
      Array.from(new Map(JOURNEY_TIMELINE_EVENTS.map((event) => [event.assignedTo.id, event.assignedTo])).values()),
    [],
  );
  const projects = useMemo(
    () =>
      Array.from(
        new Set(
          JOURNEY_TIMELINE_EVENTS.map((event) => event.relatedProject).filter(
            (value): value is string => Boolean(value),
          ),
        ),
      ),
    [],
  );

  const filteredEvents = useMemo(() => {
    if (workspaceState === 'empty') return [];
    return JOURNEY_TIMELINE_EVENTS.filter((event) => {
      if (!effectiveCanViewInternalNotes && event.activityType === 'internal_note') return false;
      const searchable = `${eventTitle(event)} ${event.summary} ${event.relatedProject ?? ''} ${event.assignedTo.name}`.toLowerCase();
      const eventDate = event.occurredAt.slice(0, 10);
      return (
        (!search || searchable.includes(search)) &&
        (!dateFrom || eventDate >= dateFrom) &&
        (!dateTo || eventDate <= dateTo) &&
        (!activityType || event.activityType === activityType) &&
        (!memberId || event.assignedTo.id === memberId) &&
        (!project || event.relatedProject === project)
      );
    });
  }, [
    activityType,
    dateFrom,
    dateTo,
    effectiveCanViewInternalNotes,
    memberId,
    project,
    search,
    workspaceState,
  ]);

  const visibleEvents = filteredEvents.slice(0, page * PAGE_SIZE);
  const resolvedContactHref = contactHref ?? (`/workspaces/crm/contacts/${contact.id}` as Route);
  const executiveSummary = useMemo(() => {
    const lastActivity = JOURNEY_TIMELINE_EVENTS.find(
      (event) =>
        event.kind === 'customer_communication' &&
        (event.status === 'completed' || event.status === 'sent'),
    );
    const proposal = JOURNEY_TIMELINE_EVENTS.find((event) => event.activityType === 'proposal');
    const followUp = JOURNEY_TIMELINE_EVENTS.find(
      (event) => event.activityType === 'follow_up_task' && event.status === 'due',
    );
    const meeting = JOURNEY_TIMELINE_EVENTS.find(
      (event) => event.activityType === 'meeting' && event.status === 'scheduled',
    );
    const documents = JOURNEY_TIMELINE_EVENTS.filter((event) => event.attachment);
    const expectedValue =
      typeof contact.buyer_profile?.budget === 'string' ? contact.buyer_profile.budget : 'Not specified';
    return {
      lastActivity: relativeFixtureActivity(lastActivity, JOURNEY_TIMELINE_EVENTS[0], locale),
      opportunity: proposal?.relatedProject ?? projects[0] ?? 'No active project',
      opportunityStage: proposal ? `${getCrmEventIdentity(proposal.activityType).label} · ${STATUS_LABELS[proposal.status]}` : 'No stage',
      expectedValue,
      nextMeeting: meeting ? `${eventTitle(meeting)} · ${dateFormatter.format(new Date(meeting.occurredAt))}` : 'No meeting scheduled',
      dueFollowUp: followUp ? `${eventTitle(followUp)} · ${dateFormatter.format(new Date(followUp.occurredAt))}` : 'No open follow-up',
      properties: projects,
      documents,
    };
  }, [contact.buyer_profile, dateFormatter, locale, projects]);

  function replaceParams(nextParams: URLSearchParams) {
    const query = nextParams.toString();
    window.history.replaceState(null, '', query ? `${pathname}?${query}` : pathname);
  }

  function setParam(name: string, value: string) {
    const nextParams = new URLSearchParams(searchParams.toString());
    if (value) nextParams.set(name, value);
    else nextParams.delete(name);
    nextParams.delete('page');
    replaceParams(nextParams);
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setParam('q', String(formData.get('q') ?? '').trim());
  }

  function openDetail(event: JourneyTimelineEvent) {
    if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current);
    setIsDrawerClosing(false);
    returnFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setSelectedEvent(event);
  }

  const finishCloseDetail = useCallback(() => {
    closeTimerRef.current = null;
    setSelectedEvent(null);
    setIsDrawerClosing(false);
    window.requestAnimationFrame(() => returnFocusRef.current?.focus());
  }, []);

  const closeDetail = useCallback(() => {
    if (isDrawerClosing) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      finishCloseDetail();
      return;
    }
    setIsDrawerClosing(true);
    closeTimerRef.current = window.setTimeout(finishCloseDetail, 140);
  }, [finishCloseDetail, isDrawerClosing]);

  useEffect(
    () => () => {
      if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current);
    },
    [],
  );

  useEffect(() => {
    if (!selectedEvent) return;
    const closeButton = document.querySelector<HTMLElement>('.journey-workspace__drawer .crm-modal__close');
    closeButton?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeDetail();
      if (event.key !== 'Tab') return;
      const drawer = document.querySelector<HTMLElement>('.journey-workspace__drawer');
      const focusable = drawer
        ? Array.from(
            drawer.querySelectorAll<HTMLElement>(
              'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
            ),
          )
        : [];
      const first = focusable[0];
      const last = focusable.at(-1);
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [closeDetail, selectedEvent]);

  return (
    <section className="journey-workspace" aria-labelledby="journey-workspace-title">
      <header className="journey-workspace__context">
        <Link href={resolvedContactHref} className="journey-workspace__back">
          <IhIcon name="chevronLeft" size={15} />
          Back to customer
        </Link>
        <div className="journey-workspace__identity">
          <span className="journey-workspace__avatar" aria-hidden="true">AY</span>
          <div>
            <div className="journey-workspace__title-row">
              <h1 id="journey-workspace-title">{contact.display_name}</h1>
              <StatusChip tone="success">Active buyer</StatusChip>
            </div>
            <p>{contact.primary_phone} · {contact.primary_email}</p>
            <span>Owner <strong>{contact.owner_name}</strong></span>
          </div>
        </div>
        <div className="journey-workspace__context-summary">
          <span>
            <small>Customer journey</small>
            <strong>{JOURNEY_TIMELINE_EVENTS.length} Activities</strong>
          </span>
          <span>
            <small>Last activity</small>
            <strong>{executiveSummary.lastActivity}</strong>
          </span>
        </div>
      </header>

      <form className="journey-workspace__toolbar" onSubmit={submitSearch}>
        <div className="journey-workspace__search-group">
          <label className="journey-workspace__search">
            <span className="sr-only">Search journey</span>
            <IhIcon name="search" size={16} />
            <input key={search} name="q" defaultValue={searchParams.get('q') ?? ''} placeholder="Search journey" />
          </label>
          <button type="submit" className="journey-workspace__search-button">Search</button>
        </div>
        <label>
          <span>From</span>
          <input type="date" value={dateFrom} onChange={(event) => setParam('from', event.target.value)} />
        </label>
        <label>
          <span>To</span>
          <input type="date" value={dateTo} onChange={(event) => setParam('to', event.target.value)} />
        </label>
        <label>
          <span>Activity type</span>
          <select value={activityType} onChange={(event) => setParam('type', event.target.value)}>
            <option value="">All types</option>
            {(Object.keys(CRM_EVENT_IDENTITIES) as JourneyActivityType[]).map((type) => (
              <option key={type} value={type}>{CRM_EVENT_IDENTITIES[type].label}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Team member</span>
          <select value={memberId} onChange={(event) => setParam('member', event.target.value)}>
            <option value="">All members</option>
            {teamMembers.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
          </select>
        </label>
        <label>
          <span>Project</span>
          <select value={project} onChange={(event) => setParam('project', event.target.value)}>
            <option value="">All projects</option>
            {projects.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <div className="journey-workspace__toolbar-meta">
          <strong aria-live="polite">{filteredEvents.length} results</strong>
          <button type="button" onClick={() => window.history.replaceState(null, '', pathname)}>Clear filters</button>
        </div>
      </form>

      {workspaceState === 'loading' ? (
        <div className="journey-workspace__state"><LoadingState label="Loading journey…" /></div>
      ) : workspaceState === 'error' ? (
        <div className="journey-workspace__state">
          <ErrorState
            title="Journey unavailable"
            message="The local presentation could not be displayed."
            action={<button type="button" onClick={() => setParam('state', '')}>Retry</button>}
          />
        </div>
      ) : (
        <div className="journey-workspace__layout">
          <main className="journey-workspace__timeline" aria-label="Customer journey activity">
            {visibleEvents.length > 0 ? (
              <>
                <ol className="journey-workspace__events">
                  {visibleEvents.map((event) => {
                    const identity = getCrmEventIdentity(event.activityType);
                    const isSelected = selectedEvent?.id === event.id;
                    return (
                      <li
                        key={event.id}
                        className={`journey-workspace__event journey-workspace__event--${event.kind} ${identity.className} journey-workspace__event--status-${event.status}${isSelected ? ' journey-workspace__event--selected' : ''}`}
                      >
                        <span className="journey-workspace__event-marker" aria-hidden="true">
                          <IhIcon name={identity.icon} size={17} />
                        </span>
                        <button
                          type="button"
                          className="journey-workspace__event-card"
                          aria-pressed={isSelected}
                          onClick={() => openDetail(event)}
                        >
                        <span className="journey-workspace__event-topline">
                          <span>
                            <strong>{eventTitle(event)}</strong>
                            <small>{identity.label}</small>
                          </span>
                          <time dateTime={event.occurredAt}>{dateFormatter.format(new Date(event.occurredAt))}</time>
                        </span>
                        <span className="journey-workspace__event-summary">{emailPreviewText(event.summary)}</span>
                        <span className="journey-workspace__event-meta">
                          <span>{event.assignedTo.initials} · {event.assignedTo.name}</span>
                          {event.relatedProject ? <span><IhIcon name="projects" size={13} />{event.relatedProject}</span> : null}
                          <span className={`journey-workspace__event-status journey-workspace__event-status--${event.status}`}>
                            {STATUS_LABELS[event.status]}
                          </span>
                          {effectiveCanViewInternalNotes && event.internalSalesNote ? (
                            <span className="journey-workspace__private-indicator"><IhIcon name="user" size={12} />Private note</span>
                          ) : null}
                          {event.attachment ? <span><IhIcon name="documents" size={12} />Attachment</span> : null}
                        </span>
                        </button>
                      </li>
                    );
                  })}
                </ol>
                <div className="journey-workspace__pagination">
                  <span>Showing {visibleEvents.length} of {filteredEvents.length}</span>
                  {visibleEvents.length < filteredEvents.length ? (
                    <button
                      type="button"
                      onClick={() => {
                        const nextParams = new URLSearchParams(searchParams.toString());
                        nextParams.set('page', String(page + 1));
                        replaceParams(nextParams);
                      }}
                    >
                      Load more
                    </button>
                  ) : <span>End of journey</span>}
                </div>
              </>
            ) : (
              <EmptyState title="No journey activity" description="Clear or adjust the filters to see more results." />
            )}
          </main>

          <aside className="journey-workspace__rail" aria-label="Journey support">
            <section>
              <span className="journey-workspace__rail-eyebrow">Next action</span>
              <h2>Follow up proposal</h2>
              <StatusChip tone="warning">Due today · 4:00 PM</StatusChip>
              <p>Send the revised payment-plan terms and confirm Monday’s reservation window.</p>
            </section>
            <section>
              <span className="journey-workspace__rail-eyebrow">Journey snapshot</span>
              <dl>
                <div><dt>Last interaction</dt><dd>Jul 24, 9:12 AM</dd></div>
                <div><dt>Total activities</dt><dd>{JOURNEY_TIMELINE_EVENTS.length}</dd></div>
                <div><dt>Open tasks / follow-ups</dt><dd>3</dd></div>
                <div><dt>Most recent project</dt><dd>North Towers A-1204</dd></div>
              </dl>
            </section>
            <section className="journey-workspace__decision">
              <span className="journey-workspace__rail-eyebrow">Executive context</span>
              <div className="journey-workspace__decision-grid">
                <article>
                  <span><IhIcon name="target" size={15} />Active opportunity</span>
                  <strong>{executiveSummary.opportunity}</strong>
                  <small>{executiveSummary.opportunityStage} · {executiveSummary.expectedValue}</small>
                </article>
                <article>
                  <span><IhIcon name="calendar" size={15} />Upcoming meetings</span>
                  <strong>{executiveSummary.nextMeeting}</strong>
                  <small>{executiveSummary.dueFollowUp}</small>
                </article>
                <article>
                  <span><IhIcon name="inventory" size={15} />Related properties</span>
                  <strong>{executiveSummary.properties.length} selected unit</strong>
                  <small>{executiveSummary.properties.join(', ') || 'No related property'}</small>
                </article>
                <article>
                  <span><IhIcon name="documents" size={15} />Recent documents</span>
                  <strong>{executiveSummary.documents.length} files in journey</strong>
                  <small>{executiveSummary.documents.slice(0, 2).map((event) => event.attachment?.fileName).join(' · ')}</small>
                </article>
              </div>
            </section>
            <section className="journey-workspace__ai">
              <span className="journey-workspace__rail-eyebrow"><IhIcon name="sparkles" size={14} />AI insights</span>
              <p>Presentation placeholders only. No AI service or processing is connected.</p>
              <ul>
                {AI_ACTIONS.map((action) => <li key={action}>{action}<span>Future</span></li>)}
              </ul>
            </section>
          </aside>
        </div>
      )}

      {selectedEvent ? (
        <div className={`journey-workspace__drawer-layer${isDrawerClosing ? ' journey-workspace__drawer-layer--closing' : ''}`} role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeDetail();
        }}>
          <div
            className="journey-workspace__drawer"
            role="dialog"
            aria-modal="true"
            aria-label={`${eventTitle(selectedEvent)} activity detail`}
          >
            <JourneyActivityDetail
              event={selectedEvent}
              contactId={contact.id}
              canViewInternalNotes={effectiveCanViewInternalNotes}
              onClose={closeDetail}
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}

function ContactJourneyWorkspaceLive({ contactId }: { contactId: string }) {
  const { authLoading, user, canRead } = useCrmAccess();
  const detailQuery = useQuery({
    ...contactQueries.detail(contactId),
    enabled: !authLoading && canRead,
  });

  if (authLoading || detailQuery.isLoading) return <LoadingState label="Loading customer journey…" />;
  if (!canRead) return <EmptyState title="Access denied" description="You cannot view this customer journey." />;
  if (detailQuery.isError || !detailQuery.data) {
    return <ErrorState title="Journey unavailable" message={detailQuery.error?.message ?? 'Unable to load customer.'} />;
  }

  return (
    <ContactJourneyWorkspacePresentation
      contact={detailQuery.data}
      canViewInternalNotes={canViewPrivateNotes(user)}
    />
  );
}

export function ContactJourneyWorkspace({ contactId, preview }: ContactJourneyWorkspaceProps) {
  if (preview) {
    return (
      <ContactJourneyWorkspacePresentation
        contact={preview.contact}
        canViewInternalNotes={preview.canViewInternalNotes ?? true}
        enableDebugStates={preview.enableDebugStates}
        contactHref={preview.contactHref}
      />
    );
  }
  return <ContactJourneyWorkspaceLive contactId={contactId} />;
}
