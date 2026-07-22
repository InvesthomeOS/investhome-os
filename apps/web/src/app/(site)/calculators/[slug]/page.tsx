import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getLocale, getTranslations } from 'next-intl/server';

import { CalculatorClient } from '@/features/site/calculators/calculator-client';
import {
  getCalculator,
  SITE_CALCULATORS,
  type CalculatorSlug,
} from '@/features/site/calculators/math';
import { buildSiteMetadata } from '@/features/site/lib/seo';

export function generateStaticParams() {
  return SITE_CALCULATORS.map((c) => ({ slug: c.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const calc = getCalculator(slug);
  const locale = (await getLocale()) === 'en' ? 'en' : 'tr';
  if (!calc) return {};
  return buildSiteMetadata({
    title: calc.title[locale],
    description: calc.description[locale],
    path: `/calculators/${slug}`,
    locale,
  });
}

export default async function CalculatorDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const calc = getCalculator(slug);
  if (!calc) notFound();

  const t = await getTranslations('site.calculators');
  const locale = (await getLocale()) === 'en' ? 'en' : 'tr';

  return (
    <div className="site-page">
      <div className="site-page__inner">
        <div className="site-page__intro">
          <h1>{calc.title[locale]}</h1>
          <p>{calc.description[locale]}</p>
        </div>
        <CalculatorClient slug={slug as CalculatorSlug} />
        <p className="sr-only">{t('disclaimer')}</p>
      </div>
    </div>
  );
}
