'use client';

import Link from 'next/link';
import type { Route } from 'next';
import type { ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { LoadingState } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { useAuth } from '@/lib/auth/auth-context';
import { canViewKnowledge } from '@/lib/knowledge/knowledge-permissions';
import { KNOWLEDGE_NAV_ITEMS } from '@/lib/knowledge/nav';

type KnowledgeHubShellProps = {
  children: ReactNode;
  title?: string;
  subtitle?: string;
};

export function KnowledgeHubShell({ children, title, subtitle }: KnowledgeHubShellProps) {
  const t = useTranslations('knowledge');
  const pathname = usePathname();
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <main className="leads-page" data-knowledge-hub aria-busy="true">
        <header className="leads-page__header">
          <p className="dashboard__eyebrow">{t('eyebrow')}</p>
          <h1>{t('title')}</h1>
          <p className="leads-page__subtitle">{t('subtitle')}</p>
        </header>
        <LoadingState label={t('loading')} lines={5} />
      </main>
    );
  }

  if (!canViewKnowledge(user)) {
    return (
      <main className="leads-page" data-knowledge-hub>
        <header className="leads-page__header">
          <p className="dashboard__eyebrow">{t('eyebrow')}</p>
          <h1>{t('title')}</h1>
        </header>
        <div className="documents-empty">
          <h2>{t('permissionDenied')}</h2>
          <p>{t('permissionDeniedHint')}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="leads-page knowledge-hub" data-knowledge-hub>
      <header className="leads-page__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1>{title ?? t('title')}</h1>
        <p className="leads-page__subtitle">{subtitle ?? t('subtitle')}</p>
      </header>

      <nav className="knowledge-hub__tabs" aria-label={t('navAriaLabel')}>
        {KNOWLEDGE_NAV_ITEMS.map((item) => {
          const isRoot = item.href === '/dashboard/knowledge';
          const isActive = isRoot
            ? pathname === item.href
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
          const label = t(item.labelKey as 'nav.overview');
          return (
            <Link
              key={item.href}
              href={item.href as Route}
              className={`knowledge-hub__tab${isActive ? ' knowledge-hub__tab--active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
            >
              <IhIcon name={item.icon} size={16} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="knowledge-hub__body">{children}</div>
    </main>
  );
}
