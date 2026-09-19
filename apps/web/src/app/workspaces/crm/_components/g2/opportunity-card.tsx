'use client';

import { useRef, type DragEvent, type MouseEvent } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { formatShortDate, type SalesOpportunity } from '@/lib/api/sales';
import { IhIcon } from '@/components/icons/ih-icons';

import { isOpportunityOverdue } from './opportunity-presentation';

type OpportunityCardProps = {
  opportunity: SalesOpportunity;
  assigneeName?: string;
  customerName?: string | null;
  projectName?: string | null;
  canViewSensitiveValues: boolean;
  draggable?: boolean;
  dragging?: boolean;
  selected?: boolean;
  onOpen: () => void;
  onDragStart?: () => void;
  onDragEnd?: () => void;
};

const AVATAR_TONES = ['#3d7cf5', '#6b5ce8', '#1f9a74', '#d4892a', '#c45c6a', '#2f8fb5', '#5b7c9a'];

function initialsFromName(name: string): string {
  const cleaned = name.replace(/^#\d+\s*/, '').trim();
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (!parts.length) return '?';
  if (parts.length === 1) return (parts[0] ?? '?').slice(0, 2).toUpperCase();
  return `${parts[0]?.[0] ?? ''}${parts[parts.length - 1]?.[0] ?? ''}`.toUpperCase();
}

function avatarTone(name: string): string {
  let hash = 0;
  for (let index = 0; index < name.length; index += 1) {
    hash = (hash + name.charCodeAt(index) * (index + 1)) % AVATAR_TONES.length;
  }
  return AVATAR_TONES[hash] ?? AVATAR_TONES[0]!;
}

function formatRelative(iso: string | null | undefined, locale: string): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const diffMs = Date.now() - date.getTime();
  const future = diffMs < 0;
  const minutes = Math.max(1, Math.round(Math.abs(diffMs) / 60000));
  const tr = locale.startsWith('tr');
  if (minutes < 60) {
    return tr
      ? future
        ? `${minutes} dk sonra`
        : `${minutes} dk önce`
      : future
        ? `in ${minutes}m`
        : `${minutes}m ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return tr
      ? future
        ? `${hours}s sonra`
        : `${hours}s önce`
      : future
        ? `in ${hours}h`
        : `${hours}h ago`;
  }
  const days = Math.round(hours / 24);
  return tr
    ? future
      ? `${days}g sonra`
      : `${days}g önce`
    : future
      ? `in ${days}d`
      : `${days}d ago`;
}

export function OpportunityCard({
  opportunity,
  assigneeName,
  customerName,
  projectName,
  canViewSensitiveValues: _canViewSensitiveValues,
  draggable = false,
  dragging = false,
  selected = false,
  onOpen,
  onDragStart,
  onDragEnd,
}: OpportunityCardProps) {
  const locale = useLocale();
  const tCommon = useTranslations('common');
  const overdue = isOpportunityOverdue(opportunity);
  const name = customerName?.trim() || opportunity.display_id || opportunity.opportunity_code;
  const phone = opportunity.contact_phone?.trim() || tCommon('noValue');
  const email = opportunity.contact_email?.trim() || tCommon('noValue');
  const owner = opportunity.contact_owner_name ?? assigneeName ?? tCommon('noValue');
  const lastActivity =
    formatRelative(opportunity.contact_last_activity_at || opportunity.last_contact_at, locale) ??
    tCommon('noValue');
  const followUp = opportunity.contact_next_follow_up_at
    ? formatShortDate(opportunity.contact_next_follow_up_at.slice(0, 10), locale)
    : null;
  const didDragRef = useRef(false);

  const handleDragStart = (event: DragEvent<HTMLElement>) => {
    if (!draggable) {
      event.preventDefault();
      return;
    }
    didDragRef.current = true;
    event.dataTransfer.setData('text/plain', opportunity.id);
    event.dataTransfer.setData('application/x-opportunity-id', opportunity.id);
    event.dataTransfer.effectAllowed = 'move';
    onDragStart?.();
  };

  const handleClick = (event: MouseEvent<HTMLElement>) => {
    if (didDragRef.current) {
      event.preventDefault();
      didDragRef.current = false;
      return;
    }
    onOpen();
  };

  return (
    <article
      className={[
        'opportunity-card',
        dragging ? 'opportunity-card--dragging' : '',
        selected ? 'opportunity-card--selected' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      draggable={draggable}
      onDragStart={handleDragStart}
      onDragEnd={(event) => {
        event.dataTransfer.clearData();
        onDragEnd?.();
        window.setTimeout(() => {
          didDragRef.current = false;
        }, 0);
      }}
      onClick={handleClick}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onOpen();
        }
      }}
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      aria-label={`${name}, ${phone}`}
    >
      <div className="opportunity-card__top">
        <span className="opportunity-card__avatar" style={{ background: avatarTone(name) }} aria-hidden="true">
          {initialsFromName(name)}
        </span>
        <div className="opportunity-card__identity">
          <strong>{name}</strong>
          <span className="opportunity-card__line">
            <IhIcon name="phone" size={12} />
            {phone}
          </span>
          <span className="opportunity-card__line">
            <IhIcon name="mail" size={12} />
            {email}
          </span>
        </div>
      </div>

      {projectName?.trim() ? (
        <div className="opportunity-card__project">
          <IhIcon name="home" size={12} />
          <span>{projectName.trim()}</span>
        </div>
      ) : null}

      <div className="opportunity-card__footer">
        <span className="is-owner">
          <IhIcon name="user" size={12} />
          {owner}
        </span>
        <span>
          <IhIcon name="activity" size={12} />
          {lastActivity}
        </span>
        {followUp ? (
          <span className={overdue ? 'is-overdue' : undefined}>
            <IhIcon name="calendar" size={12} />
            {followUp}
          </span>
        ) : null}
      </div>
    </article>
  );
}
