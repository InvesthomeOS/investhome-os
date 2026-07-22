'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';

const AI_TABS = [
  { href: '/workspaces/marketing/ai', key: 'hub' },
  { href: '/workspaces/marketing/ai/assistant', key: 'assistant' },
  { href: '/workspaces/marketing/ai/dashboard', key: 'dashboard' },
  { href: '/workspaces/marketing/ai/copilot', key: 'copilot' },
  { href: '/workspaces/marketing/ai/insights', key: 'insights' },
  { href: '/workspaces/marketing/ai/recommendations', key: 'recommendations' },
  { href: '/workspaces/marketing/ai/predictions', key: 'predictions' },
  { href: '/workspaces/marketing/ai/anomalies', key: 'anomalies' },
  { href: '/workspaces/marketing/ai/briefings', key: 'briefings' },
  { href: '/workspaces/marketing/ai/settings', key: 'settings' },
] as const;

export function AISubNav() {
  const pathname = usePathname();
  const t = useTranslations('marketing.ai.tabs');

  return (
    <nav className="mkt-ai-nav" aria-label={t('ariaLabel')}>
      {AI_TABS.map((tab) => {
        const isActive =
          pathname === tab.href || (tab.key !== 'hub' && pathname.startsWith(tab.href));
        return (
          <Link
            key={tab.key}
            href={tab.href as Route}
            className={isActive ? 'mkt-ai-nav__link mkt-ai-nav__link--active' : 'mkt-ai-nav__link'}
          >
            {t(tab.key)}
          </Link>
        );
      })}
    </nav>
  );
}

export function AIPageShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  const tHub = useTranslations('marketing.ai.hub');

  return (
    <main className="dashboard marketing-ai mkt-ai-workspace">
      <header className="dashboard__header mkt-ai-workspace__header">
        <p className="dashboard__eyebrow mkt-ai-workspace__eyebrow">{tHub('title')}</p>
        <h1 className="dashboard__title">{title}</h1>
        {subtitle ? <p className="dashboard__subtitle">{subtitle}</p> : null}
      </header>
      <AISubNav />
      {children}
    </main>
  );
}

export function AIDashboardSkeleton() {
  return (
    <div className="mkt-ai-skeleton" aria-hidden="true">
      <div className="mkt-ai-skeleton__row" />
      <div className="mkt-ai-skeleton__grid">
        <div className="mkt-ai-skeleton__card" />
        <div className="mkt-ai-skeleton__card" />
        <div className="mkt-ai-skeleton__card" />
        <div className="mkt-ai-skeleton__card" />
      </div>
    </div>
  );
}

export function PredictionSkeleton() {
  return (
    <div className="mkt-ai-skeleton mkt-ai-skeleton--predictions" aria-hidden="true">
      {[1, 2, 3].map((i) => (
        <div key={i} className="mkt-ai-skeleton__panel" />
      ))}
    </div>
  );
}

export function InsightSkeleton() {
  return (
    <div className="mkt-ai-skeleton mkt-ai-skeleton--insights" aria-hidden="true">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="mkt-ai-skeleton__line" />
      ))}
    </div>
  );
}

export function AIConfidenceBadge({ confidence }: { confidence: string }) {
  return <span className={`mkt-ai-confidence mkt-ai-confidence--${confidence}`}>{confidence}</span>;
}

export function AIEmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="mkt-ai-empty">
      <h2 className="mkt-ai-empty__title">{title}</h2>
      <p className="mkt-ai-empty__desc">{description}</p>
    </div>
  );
}
