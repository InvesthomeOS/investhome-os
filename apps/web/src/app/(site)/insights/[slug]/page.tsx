import type { Metadata } from 'next';
import type { Route } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getLocale, getTranslations } from 'next-intl/server';

import {
  getArticleBySlug,
  getRelatedArticles,
  SITE_ARTICLES,
} from '@/features/site/content/articles';
import { articleJsonLd, buildSiteMetadata } from '@/features/site/lib/seo';
import { JsonLdScript } from '@/components/site/json-ld-script';

export function generateStaticParams() {
  return SITE_ARTICLES.map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const article = getArticleBySlug(slug);
  const locale = (await getLocale()) === 'en' ? 'en' : 'tr';
  if (!article) return {};
  return buildSiteMetadata({
    title: article.seo.title[locale],
    description: article.seo.description[locale],
    path: `/insights/${slug}`,
    locale,
    type: 'article',
  });
}

export default async function InsightArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = getArticleBySlug(slug);
  if (!article) notFound();

  const t = await getTranslations('site.insights');
  const locale = (await getLocale()) === 'en' ? 'en' : 'tr';
  const related = getRelatedArticles(slug);
  const jsonLd = articleJsonLd({
    title: article.title[locale],
    description: article.excerpt[locale],
    path: `/insights/${slug}`,
    publishedAt: article.publishedAt,
    authorName: article.author.name,
  });

  return (
    <div className="site-page">
      <JsonLdScript data={jsonLd} />
      <div className="site-page__inner">
        <article className="site-article">
          <div className="site-article__meta">
            <span>{article.publishedAt}</span>
            <span>{t('minRead', { n: article.readingMinutes })}</span>
            <span>{t('by', { name: article.author.name })}</span>
            <span>{article.author.role[locale]}</span>
          </div>
          <h1>{article.title[locale]}</h1>
          <div className="site-article__body">
            {article.body[locale].map((para) => (
              <p key={para}>{para}</p>
            ))}
          </div>
          <div className="site-chips" style={{ marginTop: '1.5rem' }} aria-label={t('tags')}>
            {article.tags.map((tag) => (
              <span key={tag} className="site-chip">
                #{tag}
              </span>
            ))}
          </div>
          {article.workflow.internalLinks.length > 0 ? (
            <div style={{ marginTop: '1.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.65rem' }}>
              {article.workflow.internalLinks.map((href) => (
                <Link key={href} href={href as Route} className="site-btn site-btn--ghost site-btn--sm">
                  {href}
                </Link>
              ))}
            </div>
          ) : null}
        </article>

        <section style={{ marginTop: '3rem', maxWidth: '42rem' }}>
          <h2 style={{ fontWeight: 500, fontSize: '1.25rem' }}>{t('related')}</h2>
          {related.map((a) => (
            <Link key={a.slug} href={`/insights/${a.slug}`} className="site-article-card">
              <div className="site-article-card__meta">
                <span>{a.publishedAt}</span>
                <span>{t('minRead', { n: a.readingMinutes })}</span>
              </div>
              <h3>{a.title[locale]}</h3>
              <p>{a.excerpt[locale]}</p>
            </Link>
          ))}
        </section>
      </div>
    </div>
  );
}
