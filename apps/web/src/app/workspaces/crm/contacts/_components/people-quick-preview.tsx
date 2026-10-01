'use client';

import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';

import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { CrmContactSummary } from '@/workspaces/crm/types';

type Copy = {
  preview: string;
  close: string;
  openPerson: string;
  company: string;
  role: string;
  phone: string;
  email: string;
  tags: string;
  purchases: string;
  activities: string;
  empty: string;
  loading: string;
};

function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '•';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function display(value: string | null | undefined) {
  const next = value?.trim();
  return next ? next : null;
}

function relativeTime(value: string | null | undefined, locale: string) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const delta = Date.now() - date.getTime();
  const minutes = Math.round(delta / 60000);
  const rtf = new Intl.RelativeTimeFormat(locale.startsWith('tr') ? 'tr' : 'en', { numeric: 'auto' });
  if (Math.abs(minutes) < 60) return rtf.format(-minutes, 'minute');
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 48) return rtf.format(-hours, 'hour');
  const days = Math.round(hours / 24);
  if (Math.abs(days) < 30) return rtf.format(-days, 'day');
  return date.toLocaleDateString(locale.startsWith('tr') ? 'tr-TR' : 'en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function PeopleQuickPreview({
  contact,
  locale,
  copy,
  roleLabel,
  onClose,
  onOpen,
}: {
  contact: CrmContactSummary;
  locale: string;
  copy: Copy;
  roleLabel: string;
  onClose: () => void;
  onOpen: () => void;
}) {
  const detailQuery = useQuery({
    ...contactQueries.detail(contact.id),
    enabled: Boolean(contact.id),
  });
  const detail = detailQuery.data;
  const company = display(contact.organization_name) || display(contact.company_name);
  const phone = display(contact.primary_phone);
  const email = display(contact.primary_email);
  const tags = (contact.tag_items?.map((item) => item.name) ?? contact.tags ?? []).filter(Boolean);
  const purchases = (detail?.purchases ?? [])
    .filter((row) => !row.is_historical_unit_change)
    .slice(0, 5);
  const agreements = (detail?.crm_agreements ?? []).slice(0, 5);
  const projectRows =
    purchases.length > 0
      ? purchases.map((row) => ({
          id: row.agreement_id,
          title: [row.project_label, row.unit_number].filter(Boolean).join(' · '),
          meta: row.amount_label || row.stage || null,
        }))
      : agreements.map((row) => ({
          id: row.id,
          title: [row.project_label, row.unit_number].filter(Boolean).join(' · '),
          meta: row.status || null,
        }));
  const activities = (detail?.crm_activities ?? []).slice(0, 4);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <aside className="crm-people-preview" data-testid="crm-people-preview">
      <header className="crm-people-preview__head">
        <div className="crm-people-preview__identity">
          <span className="ctc-ds__avatar is-navy is-lg" aria-hidden="true">
            {initials(contact.display_name)}
          </span>
          <div>
            <strong>{contact.display_name}</strong>
            {roleLabel ? <span>{roleLabel}</span> : null}
            {company ? <span>{company}</span> : null}
          </div>
        </div>
        <button type="button" className="crm-people-preview__close" onClick={onClose} aria-label={copy.close}>
          ×
        </button>
      </header>

      <div className="crm-people-preview__actions">
        {phone ? (
          <a href={`tel:${phone}`} className="crm-people-preview__icon-btn" title={copy.phone}>
            {copy.phone}
          </a>
        ) : null}
        {email ? (
          <a href={`mailto:${email}`} className="crm-people-preview__icon-btn" title={copy.email}>
            {copy.email}
          </a>
        ) : null}
        <button type="button" className="crm-people-preview__open" data-testid="crm-people-preview-open" onClick={onOpen}>
          {copy.openPerson}
        </button>
      </div>

      <dl className="crm-people-preview__facts">
        {phone ? (
          <div>
            <dt>{copy.phone}</dt>
            <dd>{phone}</dd>
          </div>
        ) : null}
        {email ? (
          <div>
            <dt>{copy.email}</dt>
            <dd>{email}</dd>
          </div>
        ) : null}
        {company ? (
          <div>
            <dt>{copy.company}</dt>
            <dd>{company}</dd>
          </div>
        ) : null}
        {roleLabel ? (
          <div>
            <dt>{copy.role}</dt>
            <dd>{roleLabel}</dd>
          </div>
        ) : null}
      </dl>

      {tags.length ? (
        <section>
          <h3>{copy.tags}</h3>
          <div className="crm-people-preview__tags">
            {tags.map((tag) => (
              <span key={tag}>{tag}</span>
            ))}
          </div>
        </section>
      ) : null}

      <section>
        <h3>{copy.purchases}</h3>
        {detailQuery.isLoading ? (
          <p className="crm-people-preview__empty">{copy.loading}</p>
        ) : projectRows.length === 0 ? (
          <p className="crm-people-preview__empty">{copy.empty}</p>
        ) : (
          <ul>
            {projectRows.map((row) => (
              <li key={row.id}>
                <strong>{row.title || copy.empty}</strong>
                {row.meta ? <span>{row.meta}</span> : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h3>{copy.activities}</h3>
        {detailQuery.isLoading ? (
          <p className="crm-people-preview__empty">{copy.loading}</p>
        ) : activities.length === 0 ? (
          <p className="crm-people-preview__empty">{copy.empty}</p>
        ) : (
          <ul>
            {activities.map((item) => (
              <li key={item.id}>
                <strong>{item.title || item.activity_type}</strong>
                <span>{relativeTime(item.created_at, locale)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}

export { initials };
