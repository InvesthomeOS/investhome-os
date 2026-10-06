import type { Metadata } from 'next';
import type { Route } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getLocale, getTranslations } from 'next-intl/server';

import { getProjectBySlug, SITE_PROJECTS } from '@/features/site/content/projects';
import { buildSiteMetadata, realEstateJsonLd } from '@/features/site/lib/seo';
import { JsonLdScript } from '@/components/site/json-ld-script';

export function generateStaticParams() {
  return SITE_PROJECTS.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const project = getProjectBySlug(slug);
  const locale = (await getLocale()) === 'en' ? 'en' : 'tr';
  if (!project) return {};
  return buildSiteMetadata({
    title: project.name[locale],
    description: project.summary[locale],
    path: `/projects/${slug}`,
    locale,
  });
}

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const project = getProjectBySlug(slug);
  if (!project) notFound();

  const t = await getTranslations('site.projects');
  const locale = (await getLocale()) === 'en' ? 'en' : 'tr';
  const jsonLd = realEstateJsonLd({
    name: project.name[locale],
    description: project.summary[locale],
    path: `/projects/${slug}`,
    city: project.city,
  });

  return (
    <>
      <JsonLdScript data={jsonLd} />
      <section className="site-project-hero" aria-label={project.name[locale]}>
        <div
          className="site-project-hero__visual"
          style={{
            backgroundImage: `url(${project.coverImage})`,
            backgroundPosition: project.coverPosition || 'center',
          }}
          aria-hidden
        />
        <div className="site-project-hero__inner">
          <div className="site-project-hero__meta">{project.city}</div>
          <h1>{project.name[locale]}</h1>
          <p>{project.summary[locale]}</p>
        </div>
      </section>

      <div className="site-page">
        <div className="site-page__inner site-split">
          <div>
            <section className="site-section" style={{ padding: '0 0 2.5rem' }}>
              <h2 style={{ fontWeight: 500, fontSize: '1.25rem' }}>{t('gallery')}</h2>
              <div className="site-gallery site-gallery--single" style={{ marginTop: '1rem' }}>
                <div className="site-gallery__item">
                  <img
                    src={project.coverImage}
                    alt={project.coverAlt[locale]}
                    style={{ objectPosition: project.coverPosition || 'center' }}
                  />
                </div>
              </div>
            </section>

            <section style={{ marginBottom: '2.5rem' }}>
              <h2 style={{ fontWeight: 500, fontSize: '1.25rem' }}>{t('location')}</h2>
              <p style={{ color: 'var(--site-muted)' }}>{project.location[locale]}</p>
            </section>
          </div>

          <aside className="site-aside">
            <h2>{project.name[locale]}</h2>
            <p style={{ color: 'var(--site-muted)', lineHeight: 1.5 }}>{project.location[locale]}</p>
            <Link
              href={`/lead/consultation?project=${project.slug}` as Route}
              className="site-btn site-btn--primary"
            >
              {t('reserve')}
            </Link>
            <Link href={'/lead/brochure' as Route} className="site-btn site-btn--ghost">
              {t('downloads')}
            </Link>
          </aside>
        </div>
      </div>
    </>
  );
}
