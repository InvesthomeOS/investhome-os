import type { Metadata } from 'next';
import { getLocale, getTranslations } from 'next-intl/server';

import { SITE_PROJECTS } from '@/features/site/content/projects';
import { buildSiteMetadata } from '@/features/site/lib/seo';

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const isEn = locale === 'en';
  return buildSiteMetadata({
    title: isEn ? 'Projects' : 'Projeler',
    description: isEn
      ? 'Investhome projects in Washington, DC.'
      : 'Washington, DC’deki Investhome projeleri.',
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
                <span className="site-project-card__cta">{t('view')}</span>
              </div>
            </a>
          ))}
        </div>
        <p className="site-note">{t('apiNote')}</p>
      </div>
    </div>
  );
}
