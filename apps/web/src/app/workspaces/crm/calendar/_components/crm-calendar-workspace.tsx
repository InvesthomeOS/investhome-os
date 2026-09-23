'use client';

import type { Route } from 'next';
import { useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select, StatusChip, TextArea } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { createCalendarEvent, fetchActivity, fetchCalendar, updateActivity } from '@/workspaces/crm/api/activities';
import { fetchAgreements } from '@/workspaces/crm/api/agreements';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { CrmCalendarEvent, CrmCalendarEventKind } from '@/workspaces/crm/types/activities';

import { CALENDAR_DAY_KEYS, CALENDAR_VIEW_ORDER, type CalendarViewMode } from '../calendar-model';
import '../calendar.css';

type EventKind = CrmCalendarEventKind | string;

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
  return '—';
}

function projectUnit(item: CrmCalendarEvent): string {
  const parts = [item.project_label, item.unit_number ? `Daire ${item.unit_number}` : null].filter(Boolean);
  return parts.join(' · ') || '—';
}

function formatTime(item: CrmCalendarEvent, locale: string): string {
  if (item.all_day) return '';
  const stamp = parseStamp(item.event_at) || parseStamp(item.start_date);
  if (!stamp) return '';
  return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(stamp);
}

function formatDate(value: string | null | undefined, locale: string): string {
  const stamp = parseStamp(value);
  if (!stamp) return '—';
  return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    day: '2-digit',
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

function kindLabel(t: (key: string, ...args: never[]) => string, kind: string): string {
  return KIND_KEYS.has(kind) ? t(`kinds.${kind}`) : kind;
}

function EventChip({
  item,
  locale,
  onOpen,
}: {
  item: CrmCalendarEvent;
  locale: string;
  onOpen: (item: CrmCalendarEvent) => void;
}) {
  const t = useTranslations('crm.calendar');
  const time = formatTime(item, locale);
  const person = personLabel(item, t('unresolvedIdentity'));
  const project = projectUnit(item);
  return (
    <button
      type="button"
      className={`crm-cal-ops__chip is-${item.event_kind}${item.is_overdue ? ' is-overdue' : ''}${item.is_completed ? ' is-done' : ''}`}
      onClick={() => onOpen(item)}
      data-testid="crm-calendar-chip"
    >
      <span className="crm-cal-ops__chip-time">{time || t('allDay.short')}</span>
      <strong>{item.title}</strong>
      <span className="crm-cal-ops__chip-meta">
        {person}
        {project !== '—' ? ` · ${project}` : ''}
      </span>
      <em>{kindLabel(t, item.event_kind)}</em>
    </button>
  );
}

function EventDrawer({
  item,
  mode,
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
}: {
  item: CrmCalendarEvent | null;
  mode: 'detail' | 'create' | 'edit';
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
}) {
  const t = useTranslations('crm.calendar');
  const locale = useLocale();
  const router = useRouter();
  const person = item ? personLabel(item, t('unresolvedIdentity')) : form.contactLabel || '—';
  const purchaseHref =
    item?.agreement_id && item.entity_type === 'contact' && item.entity_id
      ? salesDetailUrl(item.entity_id, item.agreement_id)
      : form.agreementId && form.contactId
        ? salesDetailUrl(form.contactId, form.agreementId)
        : undefined;
  const contactHref =
    item?.entity_type === 'contact' && item.entity_id
      ? `/workspaces/crm/contacts/${item.entity_id}`
      : form.contactId
        ? `/workspaces/crm/contacts/${form.contactId}`
        : undefined;
  const isActivity = item?.record_kind === 'activity' || (!item?.record_kind && Boolean(item?.id && !item.id.includes(':')));

  return (
    <aside className="crm-cal-ops__drawer" role="dialog" aria-label={t('drawer.title')} data-testid="crm-calendar-drawer">
      <div className="crm-cal-ops__drawer-head">
        <h3>{mode === 'create' ? t('create.title') : mode === 'edit' ? t('actions.edit') : t('drawer.title')}</h3>
        <button type="button" className="crm-cal-ops__link-btn" onClick={onClose}>
          {t('actions.close')}
        </button>
      </div>
      <div className="crm-cal-ops__drawer-body">
        {mode === 'detail' && item ? (
          <>
            <h4>{item.title}</h4>
            <dl className="crm-cal-ops__kv">
              <dt>{t('drawer.datetime')}</dt>
              <dd>
                {formatDate(item.event_at, locale)}
                {formatTime(item, locale) ? ` · ${formatTime(item, locale)}` : ` · ${t('allDay.label')}`}
              </dd>
              <dt>{t('drawer.type')}</dt>
              <dd>{kindLabel(t, item.event_kind)}</dd>
              <dt>{t('drawer.person')}</dt>
              <dd>{person}</dd>
              <dt>{t('drawer.project')}</dt>
              <dd>{item.project_label || '—'}</dd>
              <dt>{t('drawer.unit')}</dt>
              <dd>{item.unit_number || '—'}</dd>
              <dt>{t('drawer.owner')}</dt>
              <dd>{item.assigned_user_name || '—'}</dd>
              <dt>{t('drawer.status')}</dt>
              <dd>{item.is_completed ? t('status.completed') : item.is_overdue ? t('status.overdue') : item.status || '—'}</dd>
              <dt>{t('drawer.source')}</dt>
              <dd>{item.source || 'CRM'}</dd>
            </dl>
            <section>
              <h4>{t('drawer.description')}</h4>
              <p>{item.summary || t('drawer.noDescription')}</p>
            </section>
            <div className="crm-cal-ops__drawer-actions">
              {contactHref ? (
                <Button type="button" variant="primary" size="sm" onClick={() => router.push(contactHref as Route)}>
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
        ) : (
          <form
            className="crm-cal-ops__form"
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
            <div className="crm-cal-ops__person-field">
              <Input
                label={t('form.person')}
                value={form.contactLabel}
                onChange={(event) => onPersonQuery(event.target.value)}
                placeholder={t('filters.personPlaceholder')}
              />
              {personSuggestions.length > 0 ? (
                <ul className="crm-cal-ops__suggest">
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
                  {user.full_name}
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
        )}
      </div>
    </aside>
  );
}

export function CrmCalendarWorkspace() {
  const t = useTranslations('crm.calendar');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { authLoading, canRead: canView, canManageTasks } = useCrmAccess();
  const queryClient = useQueryClient();
  const [view, setView] = useState<CalendarViewMode>('month');
  const [cursor, setCursor] = useState(() => startOfDay(new Date()));
  const [filters, setFilters] = useState<OpsFilters>(EMPTY_FILTERS);
  const [personDraft, setPersonDraft] = useState('');
  const [selected, setSelected] = useState<CrmCalendarEvent | null>(null);
  const [mode, setMode] = useState<'detail' | 'create' | 'edit' | null>(null);
  const [form, setForm] = useState<EventForm>(EMPTY_FORM);
  const canQuery = !authLoading && canView;
  const range = useMemo(() => rangeForView(view, cursor), [view, cursor]);

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
      (personDraft.trim().length >= 2 || (mode !== 'detail' && form.contactLabel.trim().length >= 2 && !form.contactId)),
  });
  const purchasesQuery = useQuery({
    queryKey: ['crm', 'agreements', 'calendar-purchases', form.contactId],
    queryFn: () => fetchAgreements({ contact_id: form.contactId, page: 1, page_size: 20 }),
    enabled: canQuery && Boolean(form.contactId) && mode !== 'detail' && mode !== null,
  });

  const projects = projectsQuery.data?.project_groups ?? [];
  const users = (usersQuery.data?.items ?? []).map((user) => ({ id: user.id, full_name: user.full_name }));
  const personSuggestions = personSuggestQuery.data?.items ?? [];
  const purchases = (purchasesQuery.data?.items ?? []).map((item) => ({
    id: item.id,
    label: [item.project_group_label, item.unit_number ? `Daire ${item.unit_number}` : null].filter(Boolean).join(' · '),
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
    setForm({ ...EMPTY_FORM, kind, date: isoDate(cursor) });
    setMode('create');
  };
  const openDetail = (item: CrmCalendarEvent) => {
    setSelected(item);
    setMode('detail');
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
      description: item.summary || '',
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
      return `${formatDate(start.toISOString(), locale)} – ${formatDate(end.toISOString(), locale)}`;
    }
    return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', { month: 'long', year: 'numeric' }).format(cursor);
  }, [cursor, locale, view]);

  if (authLoading) {
    return (
      <div className="crm-calendar-ds crm-cal-ops" data-testid="crm-calendar-workspace">
        <div className="crm-cal-ops__skeleton" aria-hidden="true" />
      </div>
    );
  }
  if (!canView) {
    return (
      <div className="crm-calendar-ds crm-cal-ops" data-testid="crm-calendar-workspace">
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </div>
    );
  }

  const monthCells = Array.from({ length: 42 }, (_, index) => addDays(monthGridStart(cursor), index));
  const weekDays = Array.from({ length: 7 }, (_, index) => addDays(mondayOf(cursor), index));
  const listItems = [...events].sort((a, b) => (a.event_at || '').localeCompare(b.event_at || ''));

  return (
    <div className="crm-calendar-ds crm-cal-ops" data-testid="crm-calendar-workspace">
      <header className="crm-cal-ops__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('opsSubtitle')}</p>
        </div>
        <div className="crm-cal-ops__header-actions">
          <span className="crm-cal-ops__count">{t('eventCount', { count: listQuery.data?.total ?? events.length })}</span>
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

      <section className="crm-cal-ops__toolbar" aria-label={t('dateNav.aria')}>
        <Button type="button" variant="primary" size="sm" onClick={() => setCursor(startOfDay(new Date()))}>
          {t('dateNav.today')}
        </Button>
        <button type="button" className="crm-cal-ops__nav-btn" aria-label={t('dateNav.prev')} onClick={() => setCursor((prev) => shiftCursor(view, prev, -1))}>
          ‹
        </button>
        <button type="button" className="crm-cal-ops__nav-btn" aria-label={t('dateNav.next')} onClick={() => setCursor((prev) => shiftCursor(view, prev, 1))}>
          ›
        </button>
        <strong className="crm-cal-ops__range">{rangeLabel}</strong>
        <div className="crm-cal-ops__views" role="group" aria-label={t('viewAria')}>
          {CALENDAR_VIEW_ORDER.map((modeKey) => (
            <button
              key={modeKey}
              type="button"
              className={view === modeKey ? 'is-active' : undefined}
              onClick={() => setView(modeKey)}
            >
              {t(`views.${modeKey}`)}
            </button>
          ))}
        </div>
      </section>

      <section className="crm-cal-ops__filters" aria-label={t('filters.aria')}>
        <div className="crm-cal-ops__person-field">
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
            <ul className="crm-cal-ops__suggest">
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
              {user.full_name}
            </option>
          ))}
        </Select>
        <div className="crm-cal-ops__filter-actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {t('filters.clear')}
          </Button>
        </div>
      </section>

      {listQuery.isError ? <ErrorState title={t('loadFailed')} message={t('emptyDescription')} /> : null}

      {view === 'month' ? (
        <div className="crm-cal-ops__month" role="region" aria-label={t('views.month')}>
          <div className="crm-cal-ops__month-head">
            {CALENDAR_DAY_KEYS.map((dayKey) => (
              <div key={dayKey}>{t(`days.${dayKey}`)}</div>
            ))}
          </div>
          <div className="crm-cal-ops__month-grid">
            {monthCells.map((day) => {
              const key = isoDate(day);
              const dayEvents = eventsByDay.get(key) ?? [];
              const extra = Math.max(0, dayEvents.length - 3);
              return (
                <div
                  key={key}
                  className={`crm-cal-ops__month-cell${isoDate(day) === isoDate(new Date()) ? ' is-today' : ''}${day.getMonth() !== cursor.getMonth() ? ' is-muted' : ''}`}
                >
                  <button type="button" className="crm-cal-ops__month-num" onClick={() => { setCursor(day); setView('day'); }}>
                    {day.getDate()}
                  </button>
                  {dayEvents.slice(0, 3).map((item) => (
                    <EventChip key={item.id} item={item} locale={locale} onOpen={openDetail} />
                  ))}
                  {extra > 0 ? <span className="crm-cal-ops__more">+{extra}</span> : null}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {view === 'week' ? (
        <div className="crm-cal-ops__week" role="region" aria-label={t('views.week')}>
          {weekDays.map((day) => {
            const key = isoDate(day);
            const dayEvents = eventsByDay.get(key) ?? [];
            return (
              <section key={key} className={key === isoDate(new Date()) ? 'is-today' : undefined}>
                <header>
                  <span>{t(`days.${CALENDAR_DAY_KEYS[(day.getDay() + 6) % 7]}`)}</span>
                  <strong>{day.getDate()}</strong>
                </header>
                {dayEvents.length === 0 ? <p className="crm-cal-ops__empty-day">{t('emptyDay')}</p> : null}
                {dayEvents.map((item) => (
                  <EventChip key={item.id} item={item} locale={locale} onOpen={openDetail} />
                ))}
              </section>
            );
          })}
        </div>
      ) : null}

      {view === 'day' ? (
        <div className="crm-cal-ops__day" role="region" aria-label={t('views.day')}>
          {(eventsByDay.get(isoDate(cursor)) ?? []).length === 0 ? (
            <div className="crm-cal-ops__empty">
              <strong>{t('emptyTitle')}</strong>
              <p>{t('emptyDescription')}</p>
            </div>
          ) : (
            (eventsByDay.get(isoDate(cursor)) ?? []).map((item) => (
              <article key={item.id} className={`crm-cal-ops__row${item.is_overdue ? ' is-overdue' : ''}`} onClick={() => openDetail(item)}>
                <span>{formatTime(item, locale) || t('allDay.label')}</span>
                <div>
                  <strong>{item.title}</strong>
                  <p>
                    {personLabel(item, t('unresolvedIdentity'))} · {projectUnit(item)}
                  </p>
                </div>
                <StatusChip tone={item.is_overdue ? 'danger' : item.is_completed ? 'success' : 'info'}>
                  {kindLabel(t, item.event_kind)}
                </StatusChip>
              </article>
            ))
          )}
        </div>
      ) : null}

      {view === 'list' ? (
        <div className="crm-cal-ops__list" role="region" aria-label={t('views.list')}>
          {listQuery.isLoading ? <p>{tCommon('loading')}</p> : null}
          {listItems.length === 0 && !listQuery.isLoading ? (
            <div className="crm-cal-ops__empty">
              <strong>{t('emptyTitle')}</strong>
              <p>{t('emptyDescription')}</p>
            </div>
          ) : (
            <table className="crm-cal-ops__table">
              <thead>
                <tr>
                  <th>{t('table.when')}</th>
                  <th>{t('table.title')}</th>
                  <th>{t('table.person')}</th>
                  <th>{t('table.project')}</th>
                  <th>{t('table.type')}</th>
                </tr>
              </thead>
              <tbody>
                {listItems.map((item) => (
                  <tr key={item.id} className={item.is_overdue ? 'is-overdue' : undefined} onClick={() => openDetail(item)}>
                    <td>
                      {formatDate(item.event_at, locale)}
                      {formatTime(item, locale) ? ` · ${formatTime(item, locale)}` : ''}
                    </td>
                    <td>
                      <strong>{item.title}</strong>
                    </td>
                    <td>{personLabel(item, t('unresolvedIdentity'))}</td>
                    <td>{projectUnit(item)}</td>
                    <td>
                      <StatusChip tone={item.is_overdue ? 'danger' : item.is_completed ? 'success' : 'info'}>
                        {kindLabel(t, item.event_kind)}
                      </StatusChip>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ) : null}

      {mode ? (
        <>
          <button type="button" className="crm-cal-ops__drawer-backdrop" aria-label={t('actions.close')} onClick={() => setMode(null)} />
          <EventDrawer
            item={selectedDetail}
            mode={mode}
            form={form}
            canManage={canManageTasks}
            users={users}
            projects={projects}
            purchases={purchases}
            personSuggestions={mode === 'detail' ? [] : personSuggestions}
            saving={saveMutation.isPending}
            onClose={() => setMode(null)}
            onEdit={() => selected && openEdit(selected)}
            onSave={() => void saveMutation.mutate()}
            onFormChange={(patch) => setForm((prev) => ({ ...prev, ...patch }))}
            onPersonQuery={(value) => setForm((prev) => ({ ...prev, contactLabel: value, contactId: '' }))}
            onPickPerson={(id, name) => setForm((prev) => ({ ...prev, contactId: id, contactLabel: name }))}
          />
        </>
      ) : null}
    </div>
  );
}
