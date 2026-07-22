import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getLocale, getTranslations } from 'next-intl/server';

import { SiteLeadForm } from '@/components/site/site-lead-form';
import type { SiteFormIntent } from '@/features/site/lib/site-config';
import { buildSiteMetadata } from '@/features/site/lib/seo';

const INTENTS: SiteFormIntent[] = [
  'consultation',
  'guide',
  'brochure',
  'analysis',
  'newsletter',
  'meeting',
  'calculator',
  'contact',
];

export function generateStaticParams() {
  return INTENTS.map((intent) => ({ intent }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ intent: string }>;
}): Promise<Metadata> {
  const { intent } = await params;
  if (!INTENTS.includes(intent as SiteFormIntent)) return {};
  const locale = await getLocale();
  const t = await getTranslations('site.lead');
  return buildSiteMetadata({
    title: t(`${intent}.title`),
    description: t(`${intent}.lead`),
    path: `/lead/${intent}`,
    locale,
  });
}

export default async function LeadIntentPage({
  params,
  searchParams,
}: {
  params: Promise<{ intent: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { intent } = await params;
  if (!INTENTS.includes(intent as SiteFormIntent)) notFound();

  const t = await getTranslations(`site.lead.${intent}`);
  const sp = await searchParams;
  const defaults: Record<string, string> = {};
  for (const key of ['project', 'calculator', 'results_summary', 'full_name', 'email']) {
    const v = sp[key];
    if (typeof v === 'string' && v) defaults[key] = v;
  }

  return (
    <div className="site-page">
      <div className="site-page__inner">
        <div className="site-page__intro">
          <h1>{t('title')}</h1>
          <p>{t('lead')}</p>
        </div>
        <SiteLeadForm intent={intent as SiteFormIntent} defaults={defaults} />
      </div>
    </div>
  );
}
