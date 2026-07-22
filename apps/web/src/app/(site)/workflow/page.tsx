import type { Metadata } from 'next';
import Link from 'next/link';
import { getLocale, getTranslations } from 'next-intl/server';

import { buildSiteMetadata } from '@/features/site/lib/seo';

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const isEn = locale === 'en';
  return buildSiteMetadata({
    title: isEn ? 'AI content workflow' : 'AI içerik iş akışı',
    description: isEn
      ? 'AI draft, human review, publish, SEO, and internal linking — no autonomous publish.'
      : 'AI taslak, insan incelemesi, yayın, SEO ve iç bağlantılar — otonom yayın yok.',
    path: '/workflow',
    locale,
  });
}

export default async function WorkflowPage() {
  const t = await getTranslations('site.workflow');

  return (
    <div className="site-page">
      <div className="site-page__inner">
        <div className="site-page__intro">
          <h1>{t('title')}</h1>
          <p>{t('lead')}</p>
        </div>
        <div className="site-workflow">
          <div className="site-workflow__step">
            <strong>01</strong>
            <h3>{t('s1')}</h3>
            <p>{t('s1Body')}</p>
          </div>
          <div className="site-workflow__step">
            <strong>02</strong>
            <h3>{t('s2')}</h3>
            <p>{t('s2Body')}</p>
          </div>
          <div className="site-workflow__step">
            <strong>03</strong>
            <h3>{t('s3')}</h3>
            <p>{t('s3Body')}</p>
          </div>
          <div className="site-workflow__step">
            <strong>04</strong>
            <h3>{t('s4')}</h3>
            <p>{t('s4Body')}</p>
          </div>
        </div>
        <p className="site-note">{t('note')}</p>
        <div style={{ marginTop: '1.5rem' }}>
          <Link href="/login?next=/workspaces/marketing/ai" className="site-btn site-btn--primary">
            {t('cta')}
          </Link>
        </div>
      </div>
    </div>
  );
}
