import Link from 'next/link';
import type { Route } from 'next';
import { getLocale, getTranslations } from 'next-intl/server';

import { BrandLogo } from '@/components/brand/brand-logo';
import { getLatestArticles } from '@/features/site/content/articles';
import { getFeaturedProjects } from '@/features/site/content/projects';
import { SITE_TRUST } from '@/features/site/content/trust';

export default async function SiteHomePage() {
  const t = await getTranslations('site.home');
  const tp = await getTranslations('site.projects');
  const locale = (await getLocale()) === 'en' ? 'en' : 'tr';
  const projects = getFeaturedProjects();
  const articles = getLatestArticles(3);

  return (
    <>
      <section className="site-hero" aria-label="Hero">
        <div className="site-hero__visual" aria-hidden />
        <div className="site-hero__grid" aria-hidden />
        <div className="site-hero__content">
          <BrandLogo tone="white" layout="full" className="site-hero__brand" priority />
          <h1>{t('headline')}</h1>
          <p className="site-hero__lead">{t('lead')}</p>
          <div className="site-hero__actions">
            <Link href={'/projects' as Route} className="site-btn site-btn--primary">
              {t('ctaPrimary')}
            </Link>
            <Link href={'/lead/consultation' as Route} className="site-btn site-btn--ghost" style={{ color: '#fff', borderColor: 'rgba(255,255,255,0.45)' }}>
              {t('ctaSecondary')}
            </Link>
          </div>
        </div>
      </section>

      <section className="site-section">
        <div className="site-section__inner">
          <div className="site-section__head">
            <h2>{t('trustTitle')}</h2>
            <p>{t('trustLead')}</p>
          </div>
          <div className="site-trust__stats">
            {SITE_TRUST.stats.map((stat) => (
              <div key={stat.id} className="site-trust__stat">
                <strong>{stat.value}</strong>
                <span>{stat.label[locale]}</span>
              </div>
            ))}
          </div>
          <div className="site-trust__partners">
            {SITE_TRUST.partners.map((p) => (
              <span key={p.id} className="site-trust__partner">
                {p.name}
              </span>
            ))}
          </div>
          {SITE_TRUST.testimonials.length === 0 ? (
            <p className="site-trust__empty">{t('trustEmpty')}</p>
          ) : null}
        </div>
      </section>

      <section className="site-section site-section--wash">
        <div className="site-section__inner">
          <div className="site-section__head">
            <h2>{t('highlightsTitle')}</h2>
            <p>{t('highlightsLead')}</p>
          </div>
          <div className="site-grid site-grid--3">
            <div>
              <h3 style={{ marginTop: 0, fontWeight: 500 }}>{t('h1Title')}</h3>
              <p style={{ color: 'var(--site-muted)', lineHeight: 1.5 }}>{t('h1Body')}</p>
            </div>
            <div>
              <h3 style={{ marginTop: 0, fontWeight: 500 }}>{t('h2Title')}</h3>
              <p style={{ color: 'var(--site-muted)', lineHeight: 1.5 }}>{t('h2Body')}</p>
            </div>
            <div>
              <h3 style={{ marginTop: 0, fontWeight: 500 }}>{t('h3Title')}</h3>
              <p style={{ color: 'var(--site-muted)', lineHeight: 1.5 }}>{t('h3Body')}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="site-section">
        <div className="site-section__inner">
          <div className="site-section__head">
            <h2>{t('projectsTitle')}</h2>
            <p>{t('projectsLead')}</p>
          </div>
          <div className="site-grid site-grid--3">
            {projects.map((project) => (
              <a key={project.slug} href={project.href} className="site-project-card">
                <div className="site-project-card__media">
                  <img
                    src={project.coverImage}
                    alt={project.coverAlt[locale]}
                    style={{ objectPosition: project.coverPosition || 'center' }}
                  />
                </div>
                <div className="site-project-card__body">
                  <span className="site-project-card__meta">{project.city}</span>
                  <h3>{project.name[locale]}</h3>
                  <p>{project.summary[locale]}</p>
                  <span className="site-project-card__cta">{tp('view')}</span>
                </div>
              </a>
            ))}
          </div>
          <div style={{ marginTop: '1.75rem' }}>
            <Link href="/projects" className="site-btn site-btn--ghost">
              {t('projectsCta')}
            </Link>
          </div>
        </div>
      </section>

      <section className="site-section site-section--wash">
        <div className="site-section__inner">
          <div className="site-section__head">
            <h2>{t('insightsTitle')}</h2>
            <p>{t('insightsLead')}</p>
          </div>
          <div>
            {articles.map((article) => (
              <Link key={article.slug} href={`/insights/${article.slug}`} className="site-article-card">
                <div className="site-article-card__meta">
                  <span>{article.publishedAt}</span>
                  <span>
                    {article.readingMinutes} min
                  </span>
                </div>
                <h3>{article.title[locale]}</h3>
                <p>{article.excerpt[locale]}</p>
              </Link>
            ))}
          </div>
          <div style={{ marginTop: '1.5rem' }}>
            <Link href="/insights" className="site-btn site-btn--ghost">
              {t('insightsCta')}
            </Link>
          </div>
        </div>
      </section>

      <section className="site-section site-section--ink">
        <div className="site-section__inner site-cta-band">
          <div>
            <h2>{t('ctaTitle')}</h2>
            <p>{t('ctaLead')}</p>
          </div>
          <div className="site-cta-band__actions">
            <Link href="/lead/consultation" className="site-btn site-btn--primary">
              {t('ctaPrimaryBand')}
            </Link>
            <Link href="/lead/analysis" className="site-btn site-btn--ghost" style={{ color: '#fff', borderColor: 'rgba(255,255,255,0.35)' }}>
              {t('ctaSecondaryBand')}
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
