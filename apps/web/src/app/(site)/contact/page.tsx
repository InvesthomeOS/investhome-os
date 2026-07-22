import type { Metadata } from 'next';
import Link from 'next/link';
import { getLocale, getTranslations } from 'next-intl/server';

import { SiteLeadForm } from '@/components/site/site-lead-form';
import { buildSiteMetadata } from '@/features/site/lib/seo';

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const isEn = locale === 'en';
  return buildSiteMetadata({
    title: isEn ? 'Contact' : 'İletişim',
    description: isEn
      ? 'Contact Investhome for consultations, materials, and meetings.'
      : 'Danışmanlık, materyal ve toplantı için Investhome ile iletişime geçin.',
    path: '/contact',
    locale,
  });
}

export default async function ContactPage() {
  const t = await getTranslations('site.contact');

  return (
    <div className="site-page">
      <div className="site-page__inner site-split">
        <div>
          <div className="site-page__intro">
            <h1>{t('title')}</h1>
            <p>{t('lead')}</p>
          </div>
          <SiteLeadForm intent="contact" />
        </div>
        <aside className="site-aside">
          <h2>{t('altTitle')}</h2>
          <Link href="/lead/consultation" className="site-btn site-btn--primary">
            {t('consultation')}
          </Link>
          <Link href="/lead/guide" className="site-btn site-btn--ghost">
            {t('guide')}
          </Link>
          <Link href="/lead/newsletter" className="site-btn site-btn--ghost">
            {t('newsletter')}
          </Link>
        </aside>
      </div>
    </div>
  );
}
