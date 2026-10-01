import type { Metadata } from 'next';
import { getLocale } from 'next-intl/server';

import { SiteAnalytics } from '@/components/site/site-analytics';
import { SiteFooter } from '@/components/site/site-footer';
import { SiteHeader } from '@/components/site/site-header';
import { JsonLdScript } from '@/components/site/json-ld-script';
import { buildSiteMetadata, organizationJsonLd, websiteJsonLd } from '@/features/site/lib/seo';

import './site.css';

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const isEn = locale === 'en';
  return buildSiteMetadata({
    title: isEn ? 'Premium real estate investment' : 'Premium gayrimenkul yatırımı',
    description: isEn
      ? 'Investhome — curated projects, investment calculators, and insights for disciplined real estate investors.'
      : 'Investhome — seçilmiş projeler, yatırım hesaplayıcıları ve disiplinli yatırımcılar için içgörüler.',
    path: '/',
    locale,
  });
}

export default async function SiteLayout({ children }: { children: React.ReactNode }) {
  const jsonLd = [organizationJsonLd(), websiteJsonLd()];

  return (
    <div className="site-root" data-theme="light">
      <JsonLdScript data={jsonLd} />
      <SiteAnalytics />
      <SiteHeader />
      <main id="site-main">{children}</main>
      <SiteFooter />
    </div>
  );
}
