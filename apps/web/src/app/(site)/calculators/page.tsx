import type { Metadata } from 'next';
import Link from 'next/link';
import { getLocale, getTranslations } from 'next-intl/server';

import { SITE_CALCULATORS } from '@/features/site/calculators/math';
import { buildSiteMetadata } from '@/features/site/lib/seo';

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const isEn = locale === 'en';
  return buildSiteMetadata({
    title: isEn ? 'Investment calculators' : 'Yatırım hesaplayıcıları',
    description: isEn
      ? 'ROI, cash flow, rental yield, mortgage, refinance, appreciation, and 1031 calculators.'
      : 'ROI, nakit akışı, kira getirisi, mortgage, refinansman, değer artışı ve 1031 hesaplayıcıları.',
    path: '/calculators',
    locale,
  });
}

export default async function CalculatorsPage() {
  const t = await getTranslations('site.calculators');
  const locale = (await getLocale()) === 'en' ? 'en' : 'tr';

  return (
    <div className="site-page">
      <div className="site-page__inner">
        <div className="site-page__intro">
          <h1>{t('title')}</h1>
          <p>{t('lead')}</p>
        </div>
        <div className="site-grid site-grid--3">
          {SITE_CALCULATORS.map((calc) => (
            <Link key={calc.slug} href={`/calculators/${calc.slug}`} className="site-project-card">
              <div className="site-project-card__body" style={{ paddingTop: '1.35rem' }}>
                <span className="site-project-card__meta">{calc.slug}</span>
                <h3>{calc.title[locale]}</h3>
                <p>{calc.description[locale]}</p>
                <span className="site-project-card__cta">{t('open')}</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
