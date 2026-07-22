import type { Metadata } from 'next';
import Link from 'next/link';
import { getLocale, getTranslations } from 'next-intl/server';

import {
  getArticlesByCategory,
  searchArticles,
  SITE_ARTICLE_CATEGORIES,
  type SiteArticleCategory,
} from '@/features/site/content/articles';
import { buildSiteMetadata } from '@/features/site/lib/seo';

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const isEn = locale === 'en';
  return buildSiteMetadata({
    title: isEn ? 'Insights & knowledge center' : 'İçgörüler ve bilgi merkezi',
    description: isEn
      ? 'Guides, market notes, and investment primers from Investhome.'
      : 'Investhome’dan rehberler, piyasa notları ve yatırım primerleri.',
    path: '/insights',
    locale,
  });
}

export default async function InsightsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; category?: string }>;
}) {
  const t = await getTranslations('site.insights');
  const locale = (await getLocale()) === 'en' ? 'en' : 'tr';
  const sp = await searchParams;
  const category = SITE_ARTICLE_CATEGORIES.find((c) => c.id === sp.category)?.id as
    | SiteArticleCategory
    | undefined;
  const articles = sp.q ? searchArticles(sp.q) : getArticlesByCategory(category);

  return (
    <div className="site-page">
      <div className="site-page__inner">
        <div className="site-page__intro">
          <h1>{t('title')}</h1>
          <p>{t('lead')}</p>
        </div>

        <form className="site-search" action="/insights" method="get">
          <label className="sr-only" htmlFor="site-insights-q">
            {t('search')}
          </label>
          <input
            id="site-insights-q"
            name="q"
            defaultValue={sp.q || ''}
            placeholder={t('searchPlaceholder')}
          />
          <button type="submit" className="site-btn site-btn--primary site-btn--sm">
            {t('search')}
          </button>
        </form>

        <div className="site-chips">
          <Link href="/insights" className={!category && !sp.q ? 'site-chip is-active' : 'site-chip'}>
            {t('all')}
          </Link>
          {SITE_ARTICLE_CATEGORIES.map((c) => (
            <Link
              key={c.id}
              href={`/insights?category=${c.id}`}
              className={category === c.id ? 'site-chip is-active' : 'site-chip'}
            >
              {c.label[locale]}
            </Link>
          ))}
        </div>

        {articles.length === 0 ? (
          <p style={{ color: 'var(--site-muted)' }}>{t('empty')}</p>
        ) : (
          articles.map((article) => (
            <Link key={article.slug} href={`/insights/${article.slug}`} className="site-article-card">
              <div className="site-article-card__meta">
                <span>{article.publishedAt}</span>
                <span>{t('minRead', { n: article.readingMinutes })}</span>
                <span>{article.category}</span>
              </div>
              <h3>{article.title[locale]}</h3>
              <p>{article.excerpt[locale]}</p>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
