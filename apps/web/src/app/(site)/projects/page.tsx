import type { Metadata } from 'next';
import Link from 'next/link';
import { getLocale, getTranslations } from 'next-intl/server';

import { SITE_PROJECTS } from '@/features/site/content/projects';
import { buildSiteMetadata } from '@/features/site/lib/seo';

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const isEn = locale === 'en';
  return buildSiteMetadata({
    title: isEn ? 'Projects' : 'Projeler',
    description: isEn
      ? 'Featured and pipeline real estate projects from Investhome.'
      : 'Investhome’dan öne çıkan ve pipeline gayrimenkul projeleri.',
    path: '/projects',
    locale,
  });
}

export default async function ProjectsPage() {
  const t = await getTranslations('site.projects');
  const locale = (await getLocale()) === 'en' ? 'en' : 'tr';

  return (
    <div className="site-page">
      <div className="site-page__inner">
        <div className="site-page__intro">
          <h1>{t('title')}</h1>
          <p>{t('lead')}</p>
        </div>
        <div className="site-grid site-grid--3">
          {SITE_PROJECTS.map((project) => (
            <Link key={project.slug} href={`/projects/${project.slug}`} className="site-project-card">
              <div
                className={`site-project-card__media site-project-card__media--${project.gallery[0]?.tone || 'neutral'}`}
              />
              <div className="site-project-card__body">
                <span className="site-project-card__meta">{t(`status.${project.status}`)}</span>
                <h3>{project.name[locale]}</h3>
                <p>{project.summary[locale]}</p>
                <span className="site-project-card__cta">{t('view')}</span>
              </div>
            </Link>
          ))}
        </div>
        <p className="site-note">{t('apiNote')}</p>
      </div>
    </div>
  );
}
