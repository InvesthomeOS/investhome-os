'use client';

import type { Route } from 'next';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select, TextArea } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { createCalendarEvent, fetchActivity, fetchCalendar, updateActivity } from '@/workspaces/crm/api/activities';
import { fetchAgreements } from '@/workspaces/crm/api/agreements';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { CrmCalendarEvent, CrmCalendarEventKind } from '@/workspaces/crm/types/activities';

import { CALENDAR_DAY_KEYS, CALENDAR_HOURS, CALENDAR_VIEW_ORDER, type CalendarViewMode } from '../calendar-model';
import '../calendar-ops.css';

type EventKind = CrmCalendarEventKind | string;
type DrawerMode = 'detail' | 'create' | 'edit' | 'daylist';

type OpsFilters = {
  person: string;
  personId: string | null;
  projectGroup: string;
  eventKind: string;
  ownerId: string;
};

type EventForm = {
  title: string;
  kind: 'task' | 'meeting' | 'reminder';
  date: string;
  time: string;
  contactId: string;
  contactLabel: string;
  projectGroup: string;
  agreementId: string;
  ownerId: string;
  description: string;
};

const EMPTY_FILTERS: OpsFilters = {
  person: '',
  personId: null,
  projectGroup: '',
  eventKind: '',
  ownerId: '',
};

const EMPTY_FORM: EventForm = {
  title: '',
  kind: 'task',
  date: '',
  time: '',
  contactId: '',
  contactLabel: '',
  projectGroup: '',
  agreementId: '',
  ownerId: '',
  description: '',
};

const EVENT_KINDS: EventKind[] = ['task', 'meeting', 'reminder', 'payment', 'purchase', 'closing', 'delivery', 'document'];
const KIND_KEYS = new Set<string>([...EVENT_KINDS, 'other']);
const HOUR_START = CALENDAR_HOURS[0];
const SLOT_PX = 52;
const MONTH_VISIBLE = 2;

function startOfDay(value: Date): Date {
  const next = new Date(value);
  next.setHours(0, 0, 0, 0);
  return next;
}

function addDays(value: Date, amount: number): Date {
  const next = new Date(value);
  next.setDate(next.getDate() + amount);
  return next;
}

function mondayOf(value: Date): Date {
  const start = startOfDay(value);
  const offset = (start.getDay() + 6) % 7;
  return addDays(start, -offset);
}

function monthGridStart(cursor: Date): Date {
  return mondayOf(new Date(cursor.getFullYear(), cursor.getMonth(), 1));
}

function monthGridEnd(cursor: Date): Date {
  return addDays(monthGridStart(cursor), 42);
}

function isoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function parseStamp(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function personLabel(item: CrmCalendarEvent, unresolved: string): string {
  const name = (item.person_name || item.entity_name || '').trim();
  if (name && !['contact', 'unknown person', 'unknown'].includes(name.toLowerCase())) return name;
  if (item.entity_type === 'contact' && item.entity_id) return unresolved;
  return '';
}

function projectDisplay(item: CrmCalendarEvent): string {
  return [item.project_label, item.unit_number].filter(Boolean).join(' · ');
}

function displayOwner(name: string | null | undefined): string {
  return String(name || '')
    .replace(/\s*\((?:Demo|demo)\)\s*$/g, '')
    .trim();
}

function previewText(value: string | null | undefined): string {
  const text = String(value || '')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/\s+/g, ' ')
    .trim();
  if (!text || text.startsWith('{') || text.startsWith('[')) return '';
  return text;
}

function formatClock(value: Date, locale: string): string {
  return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(value);
}

function formatTimeRange(item: CrmCalendarEvent, locale: string): string {
  if (item.all_day) return '';
  const start = parseStamp(item.start_date) || parseStamp(item.event_at);
  const end = parseStamp(item.end_date);
  if (!start) return '';
  const startLabel = formatClock(start, locale);
  if (end && end.getTime() !== start.getTime()) return `${startLabel} – ${formatClock(end, locale)}`;
  return startLabel;
}

function formatDate(value: string | Date | null | undefined, locale: string): string {
  const stamp = value instanceof Date ? value : parseStamp(typeof value === 'string' ? value : null);
  if (!stamp) return '—';
  return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(stamp);
}

function rangeForView(view: CalendarViewMode, cursor: Date): { start: Date; end: Date } {
  if (view === 'day') {
    const start = startOfDay(cursor);
    return { start, end: addDays(start, 1) };
  }
  if (view === 'week') {
    const start = mondayOf(cursor);
    return { start, end: addDays(start, 7) };
  }
  return { start: monthGridStart(cursor), end: monthGridEnd(cursor) };
}

function shiftCursor(view: CalendarViewMode, cursor: Date, direction: -1 | 1): Date {
  if (view === 'day') return addDays(cursor, direction);
  if (view === 'week') return addDays(cursor, direction * 7);
  return new Date(cursor.getFullYear(), cursor.getMonth() + direction, 1);
}

function kindLabel(t: (key: string) => string, kind: string): string {
  return KIND_KEYS.has(kind) ? t(`kinds.${kind}`) : t('kinds.other');
}

function kindTone(kind: string): string {
  if (kind === 'task' || kind === 'meeting' || kind === 'reminder' || kind === 'purchase') return kind;
  if (kind === 'payment' || kind === 'closing') return 'purchase';
  return 'other';
}

function chipMeta(item: CrmCalendarEvent, unresolved: string, kind: string): string {
  const person = personLabel(item, unresolved);
  const project = projectDisplay(item);
  return [person || null, project || null, !person && !project ? kind : null].filter(Boolean).join(' · ');
}

function timedLayout(item: CrmCalendarEvent): { top: number; height: number } | null {
  if (item.all_day) return null;
  const start = parseStamp(item.start_date) || parseStamp(item.event_at);
  if (!start) return null;
  const end = parseStamp(item.end_date);
  const startMin = start.getHours() * 60 + start.getMinutes();
  const endMin = end ? end.getHours() * 60 + end.getMinutes() : startMin + 60;
  const top = ((startMin - HOUR_START * 60) / 60) * SLOT_PX;
  const height = Math.max(((Math.max(endMin, startMin + 30) - startMin) / 60) * SLOT_PX, 28);
  if (top + height <= 0 || top >= SLOT_PX * CALENDAR_HOURS.length) return null;
  return { top: Math.max(top, 0), height };
}

function EventChip({
  item,
  locale,
  compact,
  onOpen,
}: {
  item: CrmCalendarEvent;
  locale: string;
  compact?: boolean;
  onOpen: (item: CrmCalendarEvent) => void;
}) {
  const t = useTranslations('crm.calendar');
  const time = formatTimeRange(item, locale);
  const kind = kindLabel(t, item.event_kind);
  const meta = chipMeta(item, t('unresolvedIdentity'), kind);
  const titleBits = [item.title, time, meta].filter(Boolean);
  return (
    <button
      type="button"
      className={`crm-ops-chip is-${kindTone(item.event_kind)}${item.is_overdue ? ' is-overdue' : ''}${item.is_completed ? ' is-done' : ''}`}
      onClick={() => onOpen(item)}
      title={titleBits.join('\n')}
      data-testid="crm-calendar-chip"
    >
      <strong>{item.title}</strong>
      {time ? <span className="is-time">{time}</span> : null}
      {!compact && meta ? <span className="is-meta">{meta}</span> : null}
    </button>
  );
}

function EventDrawer({
  item,
  mode,
  dayEvents,
  dayLabel,
  form,
  canManage,
  users,
  projects,
  purchases,
  personSuggestions,
  saving,
  onClose,
  onEdit,
  onSave,
  onFormChange,
  onPersonQuery,
  onPickPerson,
  onOpenEvent,
}: {
  item: CrmCalendarEvent | null;
  mode: DrawerMode;
  dayEvents: CrmCalendarEvent[];
  dayLabel: string;
  form: EventForm;
  canManage: boolean;
  users: Array<{ id: string; full_name: string }>;
  projects: Array<{ id: string; label: string }>;
  purchases: Array<{ id: string; label: string }>;
  personSuggestions: Array<{ id: string; display_name: string }>;
  saving: boolean;
  onClose: () => void;
  onEdit: () => void;
  onSave: () => void;
  onFormChange: (patch: Partial<EventForm>) => void;
  onPersonQuery: (value: string) => void;
  onPickPerson: (id: string, name: string) => void;
  onOpenEvent: (item: CrmCalendarEvent) => void;
}) {
  const t = useTranslations('crm.calendar');
  const locale = useLocale();
  const router = useRouter();
  const { openContact } = useContactCard();
  const person = item ? personLabel(item, t('unresolvedIdentity')) : form.contactLabel;
  const project = item ? projectDisplay(item) : '';
  const owner = item ? displayOwner(item.assigned_user_name) : '';
  const description = item ? previewText(item.summary) : '';
  const purchaseHref =
    item?.agreement_id && item.entity_type === 'contact' && item.entity_id
      ? salesDetailUrl(item.entity_id, item.agreement_id)
      : form.agreementId && form.contactId
        ? salesDetailUrl(form.contactId, form.agreementId)
        : undefined;
  const contactId = item?.entity_type === 'contact' ? item.entity_id : form.contactId || null;
  const isActivity = item?.record_kind === 'activity' || (!item?.record_kind && Boolean(item?.id && !item.id.includes(':')));
  const statusLabel = item?.is_completed
    ? t('status.completed')
    : item?.status && !/^[a-z0-9_]+$/i.test(item.status)
      ? item.status
      : '';

  return (
    <aside className="crm-ops-drawer" role="dialog" aria-label={t('drawer.title')} data-testid="crm-calendar-drawer">
      <div className="crm-ops-drawer__head">
        <h3>
          {mode === 'create' ? t('create.title') : mode === 'edit' ? t('actions.edit') : mode === 'daylist' ? t('overflow.title', { date: dayLabel }) : t('drawer.title')}
        </h3>
        <button type="button" className="crm-ops-link" onClick={onClose}>
          {t('actions.close')}
        </button>
      </div>
      <div className="crm-ops-drawer__body">
        {mode === 'daylist' ? (
          <div className="crm-ops-daylist">
            {dayEvents.length === 0 ? <p className="crm-ops-note">{t('emptyDay')}</p> : null}
            {dayEvents.map((event) => (
              <EventChip key={event.id} item={event} locale={locale} onOpen={onOpenEvent} />
            ))}
          </div>
        ) : null}

        {mode === 'detail' && item ? (
          <>
            <h4>{item.title}</h4>
            <dl className="crm-ops-kv">
              <dt>{t('drawer.type')}</dt>
              <dd>{kindLabel(t, item.event_kind)}</dd>
              <dt>{t('drawer.date')}</dt>
              <dd>{formatDate(item.event_at, locale)}</dd>
              <dt>{t('drawer.time')}</dt>
              <dd>{formatTimeRange(item, locale) || t('allDay.label')}</dd>
              <dt>{t('drawer.person')}</dt>
              <dd>
                {person && contactId ? (
                  <button type="button" className="crm-ops-link" onClick={() => openContact(contactId)}>
                    {person}
                  </button>
                ) : (
                  person || '—'
                )}
              </dd>
              <dt>{t('drawer.projectUnit')}</dt>
              <dd>{project || '—'}</dd>
              <dt>{t('drawer.owner')}</dt>
              <dd>{owner || '—'}</dd>
              {statusLabel ? (
                <>
                  <dt>{t('drawer.status')}</dt>
                  <dd>{statusLabel}</dd>
                </>
              ) : null}
            </dl>
            {description ? <p className="crm-ops-note">{description}</p> : <p className="crm-ops-note">{t('drawer.noDescription')}</p>}
            <div className="crm-ops-drawer__actions">
              {contactId ? (
                <Button type="button" variant="primary" size="sm" onClick={() => openContact(contactId)}>
                  {t('actions.openContact')}
                </Button>
              ) : null}
              {purchaseHref ? (
                <Button type="button" variant="secondary" size="sm" onClick={() => router.push(purchaseHref as Route)}>
                  {t('actions.openPurchase')}
                </Button>
              ) : null}
              {canManage && isActivity ? (
                <Button type="button" variant="secondary" size="sm" onClick={onEdit}>
                  {item.event_kind === 'task' || item.event_kind === 'reminder' ? t('actions.openTask') : t('actions.edit')}
                </Button>
              ) : null}
            </div>
          </>
        ) : null}

        {mode === 'create' || mode === 'edit' ? (
          <form
            className="crm-ops-form"
            onSubmit={(event) => {
              event.preventDefault();
              onSave();
            }}
          >
            <Input label={t('form.title')} value={form.title} onChange={(event) => onFormChange({ title: event.target.value })} required />
            <Select label={t('form.kind')} value={form.kind} onChange={(event) => onFormChange({ kind: event.target.value as EventForm['kind'] })}>
              <option value="task">{t('kinds.task')}</option>
              <option value="meeting">{t('kinds.meeting')}</option>
              <option value="reminder">{t('kinds.reminder')}</option>
            </Select>
            <Input label={t('form.date')} type="date" value={form.date} onChange={(event) => onFormChange({ date: event.target.value })} required />
            <Input label={t('form.time')} type="time" value={form.time} onChange={(event) => onFormChange({ time: event.target.value })} />
            <div className="crm-ops-person">
              <Input
                label={t('form.person')}
                value={form.contactLabel}
                onChange={(event) => onPersonQuery(event.target.value)}
                placeholder={t('filters.personPlaceholder')}
              />
              {personSuggestions.length > 0 ? (
                <ul className="crm-ops-suggest">
                  {personSuggestions.map((contact) => (
                    <li key={contact.id}>
                      <button type="button" onClick={() => onPickPerson(contact.id, contact.display_name)}>
                        {contact.display_name}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
            <Select label={t('form.project')} value={form.projectGroup} onChange={(event) => onFormChange({ projectGroup: event.target.value })}>
              <option value="">{t('filters.any')}</option>
              {projects.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.label}
                </option>
              ))}
            </Select>
            <Select label={t('form.purchase')} value={form.agreementId} onChange={(event) => onFormChange({ agreementId: event.target.value })}>
              <option value="">{t('filters.any')}</option>
              {purchases.map((purchase) => (
                <option key={purchase.id} value={purchase.id}>
                  {purchase.label}
                </option>
              ))}
            </Select>
            <Select label={t('form.owner')} value={form.ownerId} onChange={(event) => onFormChange({ ownerId: event.target.value })}>
              <option value="">{t('filters.any')}</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {displayOwner(user.full_name) || user.full_name}
                </option>
              ))}
            </Select>
            <TextArea
              label={t('form.description')}
              value={form.description}
              onChange={(event) => onFormChange({ description: event.target.value })}
              rows={4}
            />
            <Button type="submit" size="sm" disabled={saving || !form.title.trim() || !form.date}>
              {t('actions.save')}
            </Button>
          </form>
        ) : null}
      </div>
    </aside>
  );
}

export function CrmCalendarWorkspace() {
  const t = useTranslations('crm.calendar');
  const locale = useLocale();
  const { openContact } = useContactCard();
  const { authLoading, canRead: canView, canManageTasks } = useCrmAccess();
  const queryClient = useQueryClient();
  const [view, setView] = useState<CalendarViewMode>('month');
  const [cursor, setCursor] = useState(() => startOfDay(new Date()));
  const [filters, setFilters] = useState<OpsFilters>(EMPTY_FILTERS);
  const [personDraft, setPersonDraft] = useState('');
  const [selected, setSelected] = useState<CrmCalendarEvent | null>(null);
  const [dayListKey, setDayListKey] = useState<string | null>(null);
  const [mode, setMode] = useState<DrawerMode | null>(null);
  const [form, setForm] = useState<EventForm>(EMPTY_FORM);
  const canQuery = !authLoading && canView;
  const range = useMemo(() => rangeForView(view, cursor), [view, cursor]);
  const todayKey = isoDate(new Date());

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((prev) => ({
        ...prev,
        person: personDraft,
        personId: personDraft.trim() ? prev.personId : null,
      }));
    }, 220);
    return () => window.clearTimeout(timer);
  }, [personDraft]);

  const listQuery = useQuery({
    queryKey: [
      'crm',
      'calendar',
      range.start.toISOString(),
      range.end.toISOString(),
      filters.person,
      filters.personId,
      filters.projectGroup,
      filters.eventKind,
      filters.ownerId,
    ],
    queryFn: () =>
      fetchCalendar({
        start: range.start.toISOString(),
        end: range.end.toISOString(),
        assigned_user_id: filters.ownerId || undefined,
        contact_search: filters.personId ? undefined : filters.person.trim() || undefined,
        entity_id: filters.personId || undefined,
        project_group: filters.projectGroup || undefined,
        event_kind: filters.eventKind || undefined,
      }),
    enabled: canQuery,
    placeholderData: keepPreviousData,
  });

  const events = listQuery.data?.events ?? [];
  const detailQuery = useQuery({
    queryKey: ['crm', 'activities', selected?.id],
    queryFn: () => fetchActivity(selected?.id || ''),
    enabled: Boolean(selected?.id && !selected.id.includes(':') && mode === 'detail'),
  });
  const selectedDetail = selected
    ? { ...selected, summary: detailQuery.data?.description || detailQuery.data?.summary || selected.summary }
    : null;

  const projectsQuery = useQuery({
    queryKey: ['crm', 'agreements', 'calendar-projects'],
    queryFn: () => fetchAgreements({ page: 1, page_size: 1 }),
    enabled: canQuery,
  });
  const usersQuery = useQuery({
    queryKey: ['users', 'calendar-filter'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: canQuery,
  });
  const personSuggestQuery = useQuery({
    ...contactQueries.list({ search: personDraft.trim() || form.contactLabel.trim(), page: 1, page_size: 8 }),
    enabled:
      canQuery &&
      (personDraft.trim().length >= 2 || (mode !== 'detail' && mode !== 'daylist' && form.contactLabel.trim().length >= 2 && !form.contactId)),
  });
  const purchasesQuery = useQuery({
    queryKey: ['crm', 'agreements', 'calendar-purchases', form.contactId],
    queryFn: () => fetchAgreements({ contact_id: form.contactId, page: 1, page_size: 20 }),
    enabled: canQuery && Boolean(form.contactId) && (mode === 'create' || mode === 'edit'),
  });

  const projects = projectsQuery.data?.project_groups ?? [];
  const users = (usersQuery.data?.items ?? []).map((user) => ({ id: user.id, full_name: user.full_name }));
  const personSuggestions = personSuggestQuery.data?.items ?? [];
  const purchases = (purchasesQuery.data?.items ?? []).map((item) => ({
    id: item.id,
    label: [item.project_group_label, item.unit_number].filter(Boolean).join(' · '),
  }));

  const saveMutation = useMutation({
    mutationFn: async () => {
      const occurs = form.time ? `${form.date}T${form.time}:00` : `${form.date}T09:00:00`;
      const occursAt = new Date(occurs).toISOString();
      if (mode === 'edit' && selected && !selected.id.includes(':')) {
        await updateActivity(selected.id, {
          title: form.title.trim(),
          description: form.description.trim() || undefined,
          assigned_user_id: form.ownerId || undefined,
          due_date: form.kind === 'meeting' ? undefined : occursAt,
          start_date: form.kind === 'meeting' ? occursAt : undefined,
          entity_type: form.contactId ? 'contact' : undefined,
          entity_id: form.contactId || undefined,
          related_entity_type: form.agreementId ? 'transaction' : undefined,
          related_entity_id: form.agreementId || undefined,
        });
        return;
      }
      await createCalendarEvent({
        title: form.title.trim(),
        event_kind: form.kind,
        description: form.description.trim() || undefined,
        occurs_at: occursAt,
        contact_id: form.contactId || undefined,
        project_group: form.projectGroup || undefined,
        agreement_id: form.agreementId || undefined,
        assigned_user_id: form.ownerId || undefined,
      });
    },
    onSuccess: () => {
      setMode(null);
      setSelected(null);
      setForm(EMPTY_FORM);
      void queryClient.invalidateQueries({ queryKey: ['crm'] });
    },
  });

  const patchFilters = (patch: Partial<OpsFilters>) => setFilters((prev) => ({ ...prev, ...patch }));
  const clearFilters = () => {
    setFilters(EMPTY_FILTERS);
    setPersonDraft('');
  };
  const openCreate = (kind: EventForm['kind']) => {
    setSelected(null);
    setDayListKey(null);
    setForm({ ...EMPTY_FORM, kind, date: isoDate(cursor) });
    setMode('create');
  };
  const openDetail = (item: CrmCalendarEvent) => {
    setSelected(item);
    setDayListKey(null);
    setMode('detail');
  };
  const openDayList = (day: Date) => {
    setSelected(null);
    setDayListKey(isoDate(day));
    setMode('daylist');
  };
  const openEdit = (item: CrmCalendarEvent) => {
    const stamp = parseStamp(item.event_at);
    setSelected(item);
    setForm({
      title: item.title,
      kind: item.event_kind === 'meeting' || item.event_kind === 'reminder' ? item.event_kind : 'task',
      date: stamp ? isoDate(stamp) : isoDate(cursor),
      time: item.all_day || !stamp ? '' : `${String(stamp.getHours()).padStart(2, '0')}:${String(stamp.getMinutes()).padStart(2, '0')}`,
      contactId: item.entity_type === 'contact' ? item.entity_id || '' : '',
      contactLabel: personLabel(item, ''),
      projectGroup: item.project_group || '',
      agreementId: item.agreement_id || '',
      ownerId: item.assigned_user_id || '',
      description: previewText(item.summary),
    });
    setMode('edit');
  };

  const eventsByDay = useMemo(() => {
    const map = new Map<string, CrmCalendarEvent[]>();
    for (const item of events) {
      const stamp = parseStamp(item.event_at);
      if (!stamp) continue;
      const key = isoDate(stamp);
      const bucket = map.get(key) ?? [];
      bucket.push(item);
      map.set(key, bucket);
    }
    return map;
  }, [events]);

  const rangeLabel = useMemo(() => {
    if (view === 'day') {
      return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      }).format(cursor);
    }
    if (view === 'week') {
      const start = mondayOf(cursor);
      const end = addDays(start, 6);
      return `${formatDate(start, locale)} – ${formatDate(end, locale)}`;
    }
    return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', { month: 'long', year: 'numeric' }).format(cursor);
  }, [cursor, locale, view]);

  const monthCells = Array.from({ length: 42 }, (_, index) => addDays(monthGridStart(cursor), index));
  const weekDays = Array.from({ length: 7 }, (_, index) => addDays(mondayOf(cursor), index));
  const listItems = [...events].sort((a, b) => (a.event_at || '').localeCompare(b.event_at || ''));
  const dayListEvents = dayListKey ? (eventsByDay.get(dayListKey) ?? []) : [];
  const dayListLabel = dayListKey ? formatDate(`${dayListKey}T12:00:00`, locale) : '';

  const shell = (children: ReactNode) => (
    <div className="crm-ops" data-testid="crm-calendar-workspace">
      {children}
    </div>
  );

  if (authLoading) {
    return shell(<div className="crm-ops-skeleton" aria-hidden="true" />);
  }
  if (!canView) {
    return shell(<ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />);
  }

  return shell(
    <>
      <header className="crm-ops__header">
        <div className="crm-ops__title">
          <span className="crm-ops__title-icon" aria-hidden>
            <IhIcon name="calendar" size={20} />
          </span>
          <div>
            <h1>{t('title')}</h1>
            <p>{t('opsSubtitle')}</p>
          </div>
        </div>
        <div className="crm-ops__header-tools">
          <span className="crm-ops__count">{t('eventCount', { count: listQuery.data?.total ?? events.length })}</span>
          {canManageTasks ? (
            <>
              <Button type="button" size="sm" onClick={() => openCreate('task')}>
                {t('create.task')}
              </Button>
              <Button type="button" variant="secondary" size="sm" onClick={() => openCreate('meeting')}>
                {t('create.meeting')}
              </Button>
              <Button type="button" variant="secondary" size="sm" onClick={() => openCreate('reminder')}>
                {t('create.reminder')}
              </Button>
            </>
          ) : null}
        </div>
      </header>

      <section className="crm-ops-toolbar" aria-label={t('dateNav.aria')}>
        <div className="crm-ops-toolbar__nav">
          <Button type="button" variant="primary" size="sm" onClick={() => setCursor(startOfDay(new Date()))}>
            {t('dateNav.today')}
          </Button>
          <button type="button" className="crm-ops-nav" aria-label={t('dateNav.prev')} onClick={() => setCursor((prev) => shiftCursor(view, prev, -1))}>
            ‹
          </button>
          <button type="button" className="crm-ops-nav" aria-label={t('dateNav.next')} onClick={() => setCursor((prev) => shiftCursor(view, prev, 1))}>
            ›
          </button>
          <strong className="crm-ops-range">{rangeLabel}</strong>
        </div>
        <div className="crm-ops-views" role="group" aria-label={t('viewAria')}>
          {CALENDAR_VIEW_ORDER.map((modeKey) => (
            <button key={modeKey} type="button" className={view === modeKey ? 'is-active' : undefined} onClick={() => setView(modeKey)}>
              {t(`views.${modeKey}`)}
            </button>
          ))}
        </div>
      </section>

      <section className="crm-ops-filtercard" aria-label={t('filters.aria')}>
        <div className="crm-ops-person">
          <Input
            label={t('filters.person')}
            value={personDraft}
            onChange={(event) => {
              setPersonDraft(event.target.value);
              patchFilters({ personId: null });
            }}
            placeholder={t('filters.personPlaceholder')}
          />
          {personDraft.trim().length >= 2 && !filters.personId && personSuggestions.length > 0 ? (
            <ul className="crm-ops-suggest">
              {personSuggestions.map((contact) => (
                <li key={contact.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setPersonDraft(contact.display_name);
                      patchFilters({ person: contact.display_name, personId: contact.id });
                    }}
                  >
                    {contact.display_name}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <Select label={t('filters.project')} value={filters.projectGroup} onChange={(event) => patchFilters({ projectGroup: event.target.value })}>
          <option value="">{t('filters.allProjects')}</option>
          {projects.map((group) => (
            <option key={group.id} value={group.id}>
              {group.label}
            </option>
          ))}
        </Select>
        <Select label={t('filters.type')} value={filters.eventKind} onChange={(event) => patchFilters({ eventKind: event.target.value })}>
          <option value="">{t('filters.any')}</option>
          {EVENT_KINDS.map((kind) => (
            <option key={kind} value={kind}>
              {kindLabel(t, kind)}
            </option>
          ))}
        </Select>
        <Select label={t('filters.owner')} value={filters.ownerId} onChange={(event) => patchFilters({ ownerId: event.target.value })}>
          <option value="">{t('filters.allOwners')}</option>
          {users.map((user) => (
            <option key={user.id} value={user.id}>
              {displayOwner(user.full_name) || user.full_name}
            </option>
          ))}
        </Select>
        <div className="crm-ops-filtercard__actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {t('filters.clear')}
          </Button>
        </div>
      </section>

      {listQuery.isError ? <ErrorState title={t('loadFailed')} message={t('emptyDescription')} /> : null}

      {view === 'month' ? (
        <section className="crm-ops-board" aria-label={t('views.month')}>
          <div className="crm-ops-month-head">
            {CALENDAR_DAY_KEYS.map((dayKey) => (
              <div key={dayKey}>{t(`days.${dayKey}`)}</div>
            ))}
          </div>
          <div className="crm-ops-month-grid">
            {monthCells.map((day) => {
              const key = isoDate(day);
              const dayEvents = eventsByDay.get(key) ?? [];
              const extra = Math.max(0, dayEvents.length - MONTH_VISIBLE);
              return (
                <div
                  key={key}
                  className={`crm-ops-month-cell${key === todayKey ? ' is-today' : ''}${day.getMonth() !== cursor.getMonth() ? ' is-muted' : ''}`}
                >
                  <button
                    type="button"
                    className="crm-ops-month-num"
                    onClick={() => {
                      setCursor(day);
                      setView('day');
                    }}
                  >
                    {day.getDate()}
                  </button>
                  {dayEvents.slice(0, MONTH_VISIBLE).map((item) => (
                    <EventChip key={item.id} item={item} locale={locale} onOpen={openDetail} />
                  ))}
                  {extra > 0 ? (
                    <button type="button" className="crm-ops-more" onClick={() => openDayList(day)}>
                      {t('overflow.more', { count: extra })}
                    </button>
                  ) : null}
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {view === 'week' ? (
        <section className="crm-ops-board" aria-label={t('views.week')}>
          <div className="crm-ops-week">
            <div className="crm-ops-week__gutter" />
            {weekDays.map((day) => {
              const key = isoDate(day);
              return (
                <div key={`head-${key}`} className={`crm-ops-week__dayhead${key === todayKey ? ' is-today' : ''}`}>
                  <span>{t(`days.${CALENDAR_DAY_KEYS[(day.getDay() + 6) % 7]}`)}</span>
                  <strong>{day.getDate()}</strong>
                </div>
              );
            })}
            <div className="crm-ops-week__gutter">{t('allDay.short')}</div>
            {weekDays.map((day) => {
              const key = isoDate(day);
              const allDay = (eventsByDay.get(key) ?? []).filter((item) => item.all_day || !timedLayout(item));
              return (
                <div key={`all-${key}`} className={`crm-ops-week__allday-cell${key === todayKey ? ' is-today' : ''}`}>
                  {allDay.map((item) => (
                    <EventChip key={item.id} item={item} locale={locale} compact onOpen={openDetail} />
                  ))}
                </div>
              );
            })}
            <div className="crm-ops-week__body">
              <div className="crm-ops-week__gutter-col">
                {CALENDAR_HOURS.map((hour) => (
                  <div key={`label-${hour}`} className="crm-ops-week__label">
                    {`${String(hour).padStart(2, '0')}:00`}
                  </div>
                ))}
              </div>
              {weekDays.map((day) => {
                const key = isoDate(day);
                const timed = (eventsByDay.get(key) ?? []).filter((item) => timedLayout(item));
                return (
                  <div key={`col-${key}`} className={`crm-ops-week__col${key === todayKey ? ' is-today' : ''}`}>
                    {timed.map((item) => {
                      const layout = timedLayout(item);
                      if (!layout) return null;
                      return (
                        <div key={item.id} className="crm-ops-week__event" style={{ top: layout.top, height: layout.height }}>
                          <EventChip item={item} locale={locale} compact onOpen={openDetail} />
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      ) : null}

      {view === 'day' ? (
        <section className="crm-ops-board" aria-label={t('views.day')}>
          {(() => {
            const dayEvents = eventsByDay.get(isoDate(cursor)) ?? [];
            const allDay = dayEvents.filter((item) => item.all_day || !timedLayout(item));
            const timed = dayEvents.filter((item) => timedLayout(item));
            if (dayEvents.length === 0) {
              return (
                <div className="crm-ops-empty">
                  <strong>{t('emptyTitle')}</strong>
                  <p>{t('emptyDescription')}</p>
                </div>
              );
            }
            return (
              <div className="crm-ops-day">
                {allDay.length > 0 ? (
                  <div className="crm-ops-day__allday">
                    {allDay.map((item) => (
                      <EventChip key={item.id} item={item} locale={locale} onOpen={openDetail} />
                    ))}
                  </div>
                ) : null}
                <div>
                  {CALENDAR_HOURS.map((hour) => (
                    <div key={hour} className="crm-ops-day__label">
                      {`${String(hour).padStart(2, '0')}:00`}
                    </div>
                  ))}
                </div>
                <div className="crm-ops-day__track">
                  {timed.map((item) => {
                    const layout = timedLayout(item);
                    if (!layout) return null;
                    return (
                      <div key={item.id} className="crm-ops-day__event" style={{ top: layout.top, height: layout.height }}>
                        <EventChip item={item} locale={locale} onOpen={openDetail} />
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}
        </section>
      ) : null}

      {view === 'list' ? (
        <section className="crm-ops-board crm-ops-list" aria-label={t('views.list')}>
          {listQuery.isLoading && listItems.length === 0 ? <div className="crm-ops-skeleton" /> : null}
          {listItems.length === 0 && !listQuery.isLoading ? (
            <div className="crm-ops-empty">
              <strong>{t('emptyTitle')}</strong>
              <p>{t('emptyDescription')}</p>
            </div>
          ) : (
            <table className="crm-ops-table">
              <thead>
                <tr>
                  <th>{t('table.when')}</th>
                  <th>{t('table.type')}</th>
                  <th className="is-title">{t('table.title')}</th>
                  <th>{t('table.person')}</th>
                  <th>{t('table.project')}</th>
                  <th>{t('table.owner')}</th>
                  <th>{t('table.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {listItems.map((item) => {
                  const person = personLabel(item, t('unresolvedIdentity'));
                  const project = projectDisplay(item);
                  const owner = displayOwner(item.assigned_user_name);
                  const contactId = item.entity_type === 'contact' ? item.entity_id : null;
                  const time = formatTimeRange(item, locale);
                  return (
                    <tr key={item.id}>
                      <td>
                        {formatDate(item.event_at, locale)}
                        {time ? ` · ${time}` : ''}
                      </td>
                      <td>
                        <span className={`crm-ops-badge is-${kindTone(item.event_kind)}`}>{kindLabel(t, item.event_kind)}</span>
                      </td>
                      <td className="is-title">
                        <strong>{item.title}</strong>
                      </td>
                      <td>
                        {person && contactId ? (
                          <button type="button" className="crm-ops-link" onClick={() => openContact(contactId)}>
                            {person}
                          </button>
                        ) : (
                          person || '—'
                        )}
                      </td>
                      <td>{project || '—'}</td>
                      <td>{owner || '—'}</td>
                      <td>
                        <button type="button" className="crm-ops-action" onClick={() => openDetail(item)}>
                          {t('table.open')}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      ) : null}

      {mode ? (
        <>
          <button type="button" className="crm-ops-drawer-backdrop" aria-label={t('actions.close')} onClick={() => setMode(null)} />
          <EventDrawer
            item={selectedDetail}
            mode={mode}
            dayEvents={dayListEvents}
            dayLabel={dayListLabel}
            form={form}
            canManage={canManageTasks}
            users={users}
            projects={projects}
            purchases={purchases}
            personSuggestions={mode === 'detail' || mode === 'daylist' ? [] : personSuggestions}
            saving={saveMutation.isPending}
            onClose={() => setMode(null)}
            onEdit={() => selected && openEdit(selected)}
            onSave={() => void saveMutation.mutate()}
            onFormChange={(patch) => setForm((prev) => ({ ...prev, ...patch }))}
            onPersonQuery={(value) => setForm((prev) => ({ ...prev, contactLabel: value, contactId: '' }))}
            onPickPerson={(id, name) => setForm((prev) => ({ ...prev, contactId: id, contactLabel: name }))}
            onOpenEvent={openDetail}
          />
        </>
      ) : null}
    </>,
  );
}
