'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import { AIPageShell } from './_components/ai-shell';

export default function MarketingAIHubPage() {
  const t = useTranslations('marketing.ai.hub');

  const links = [
    { href: '/workspaces/marketing/ai/assistant', label: t('openAssistant') },
    { href: '/workspaces/marketing/ai/dashboard', label: t('openDashboard') },
    { href: '/workspaces/marketing/ai/copilot', label: t('openCopilot') },
    { href: '/workspaces/marketing/ai/insights', label: t('openInsights') },
    { href: '/workspaces/marketing/ai/recommendations', label: t('openRecommendations') },
    { href: '/workspaces/marketing/ai/predictions', label: t('openPredictions') },
    { href: '/workspaces/marketing/ai/briefings', label: t('openBriefings') },
  ] as const;

  return (
    <AIPageShell title={t('title')} subtitle={t('subtitle')}>
      <section className="mkt-ai-hub">
        <p className="mkt-ai-hub__intro">{t('intro')}</p>
        <div className="mkt-ai-hub__grid">
          {links.map((link) => (
            <Link key={link.href} href={link.href as Route} className="mkt-ai-hub__card">
              {link.label}
            </Link>
          ))}
        </div>
      </section>
    </AIPageShell>
  );
}
