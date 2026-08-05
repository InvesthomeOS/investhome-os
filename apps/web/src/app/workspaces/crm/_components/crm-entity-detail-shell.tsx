'use client';

import Link from 'next/link';
import type { Route } from 'next';
import type { ReactNode } from 'react';

import { Button } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

export type CrmDetailTab = {
  id: string;
  label: string;
};

type CrmEntityDetailShellProps = {
  backHref: string;
  backLabel: string;
  title: string;
  subtitle?: string;
  eyebrow?: string;
  avatar?: ReactNode;
  actions?: ReactNode;
  tabs: CrmDetailTab[];
  activeTab: string;
  onTabChange: (id: string) => void;
  children: ReactNode;
  testId?: string;
};

/**
 * Shared Dashboard-DS detail chrome for CRM presentation detail pages.
 * Presentation-only — no API coupling.
 */
export function CrmEntityDetailShell({
  backHref,
  backLabel,
  title,
  subtitle,
  eyebrow,
  avatar,
  actions,
  tabs,
  activeTab,
  onTabChange,
  children,
  testId = 'crm-entity-detail',
}: CrmEntityDetailShellProps) {
  return (
    <div className="crm-entity-detail" data-testid={testId}>
      <div className="crm-entity-detail__toolbar">
        <Link href={backHref as Route} className="crm-entity-detail__back">
          <IhIcon name="chevronLeft" size={14} />
          {backLabel}
        </Link>
        {actions ? <div className="crm-entity-detail__actions">{actions}</div> : null}
      </div>

      <header className="crm-entity-detail__header">
        {avatar ? <div className="crm-entity-detail__avatar">{avatar}</div> : null}
        <div className="crm-entity-detail__identity">
          {eyebrow ? <p className="crm-entity-detail__eyebrow">{eyebrow}</p> : null}
          <h1>{title}</h1>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      </header>

      <nav className="crm-entity-detail__tabs" aria-label="Detail sections">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={activeTab === tab.id ? 'is-active' : undefined}
            aria-current={activeTab === tab.id ? 'page' : undefined}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="crm-entity-detail__body">{children}</div>
    </div>
  );
}

export function CrmDetailPanel({
  title,
  children,
  actions,
}: {
  title: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section className="crm-entity-detail__panel">
      <div className="crm-entity-detail__panel-head">
        <h2>{title}</h2>
        {actions}
      </div>
      <div className="crm-entity-detail__panel-body">{children}</div>
    </section>
  );
}

export function CrmDetailMetaGrid({
  items,
}: {
  items: Array<{ label: string; value: ReactNode }>;
}) {
  return (
    <dl className="crm-entity-detail__meta">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function CrmDetailActionButton({
  children,
  onClick,
  variant = 'secondary',
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
}) {
  return (
    <Button type="button" variant={variant} size="sm" onClick={onClick}>
      {children}
    </Button>
  );
}
