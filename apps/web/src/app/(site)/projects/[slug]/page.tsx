import type { Metadata } from 'next';
import type { Route } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getLocale, getTranslations } from 'next-intl/server';

import { getProjectBySlug, SITE_PROJECTS } from '@/features/site/content/projects';
import { buildSiteMetadata, realEstateJsonLd } from '@/features/site/lib/seo';

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
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <section className="site-project-hero">
        <div className="site-project-hero__inner">
          <div className="site-project-hero__meta">{t(`status.${project.status}`)}</div>
          <h1>{project.name[locale]}</h1>
          <p>{project.summary[locale]}</p>
        </div>
      </section>

      <div className="site-page">
        <div className="site-page__inner site-split">
          <div>
            <section className="site-section" style={{ padding: '0 0 2.5rem' }}>
              <h2 style={{ fontWeight: 500, fontSize: '1.25rem' }}>{t('gallery')}</h2>
              <div className="site-gallery" style={{ marginTop: '1rem' }}>
                <div
                  className={`site-gallery__item site-gallery__item--${project.gallery[0]?.tone || 'neutral'}`}
                  role="img"
                  aria-label={project.gallery[0]?.alt[locale]}
                />
                <div className="site-gallery__stack">
                  {project.gallery.slice(1).map((g) => (
                    <div
                      key={g.id}
                      className={`site-gallery__item site-gallery__item--${g.tone}`}
                      role="img"
                      aria-label={g.alt[locale]}
                    />
                  ))}
                </div>
              </div>
            </section>

            <section style={{ marginBottom: '2.5rem' }}>
              <h2 style={{ fontWeight: 500, fontSize: '1.25rem' }}>{t('investment')}</h2>
              <p style={{ color: 'var(--site-muted)', lineHeight: 1.55 }}>
                {project.investmentSummary[locale]}
              </p>
            </section>

            <section style={{ marginBottom: '2.5rem' }}>
              <h2 style={{ fontWeight: 500, fontSize: '1.25rem' }}>{t('highlights')}</h2>
              <ul className="site-list" style={{ marginTop: '0.75rem' }}>
                {project.highlights[locale].map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>

            <section style={{ marginBottom: '2.5rem' }}>
              <h2 style={{ fontWeight: 500, fontSize: '1.25rem' }}>{t('amenities')}</h2>
              <ul className="site-list" style={{ marginTop: '0.75rem' }}>
                {project.amenities[locale].map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>

            {project.floorPlans.length > 0 ? (
              <section style={{ marginBottom: '2.5rem' }}>
                <h2 style={{ fontWeight: 500, fontSize: '1.25rem' }}>{t('floorPlans')}</h2>
                <table className="site-table" style={{ marginTop: '0.75rem' }}>
                  <thead>
                    <tr>
                      <th>{t('rooms')}</th>
                      <th>{t('area')}</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {project.floorPlans.map((fp) => (
                      <tr key={fp.id}>
                        <td>{fp.label[locale]}</td>
                        <td>{fp.areaM2} m²</td>
                        <td>{fp.rooms}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            ) : null}

            <section style={{ marginBottom: '2.5rem' }}>
              <h2 style={{ fontWeight: 500, fontSize: '1.25rem' }}>{t('location')}</h2>
              <p style={{ color: 'var(--site-muted)' }}>{project.location[locale]}</p>
              <p className="site-note">
                {t('mapNote')} ({project.coords.lat.toFixed(4)}, {project.coords.lng.toFixed(4)})
              </p>
            </section>

            {project.downloads.length > 0 ? (
              <section>
                <h2 style={{ fontWeight: 500, fontSize: '1.25rem' }}>{t('downloads')}</h2>
                <ul className="site-list" style={{ marginTop: '0.75rem' }}>
                  {project.downloads.map((d) => (
                    <li key={d.id}>
                      <Link href={d.href as Route}>{d.label[locale]}</Link>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </div>

          <aside className="site-aside">
            <h2>{t('investment')}</h2>
            <dl>
              {project.metrics.units != null ? (
                <>
                  <dt>{t('units')}</dt>
                  <dd>{project.metrics.units}</dd>
                </>
              ) : null}
              {project.metrics.projectedYield ? (
                <>
                  <dt>{t('yield')}</dt>
                  <dd>{project.metrics.projectedYield}</dd>
                </>
              ) : null}
              {project.metrics.minTicket ? (
                <>
                  <dt>{t('ticket')}</dt>
                  <dd>{project.metrics.minTicket}</dd>
                </>
              ) : null}
            </dl>
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
