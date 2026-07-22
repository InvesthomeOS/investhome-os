import type { MetadataRoute } from 'next';

import { SITE_ARTICLES } from '@/features/site/content/articles';
import { SITE_CALCULATORS } from '@/features/site/calculators/math';
import { SITE_PROJECTS } from '@/features/site/content/projects';
import { getSiteUrl } from '@/features/site/lib/site-config';

export default function sitemap(): MetadataRoute.Sitemap {
  const base = getSiteUrl();
  const now = new Date();

  const staticRoutes = [
    '',
    '/projects',
    '/calculators',
    '/insights',
    '/contact',
    '/workflow',
    '/lead/consultation',
    '/lead/guide',
    '/lead/brochure',
    '/lead/analysis',
    '/lead/newsletter',
    '/lead/meeting',
  ].map((path) => ({
    url: `${base}${path || '/'}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: path === '' ? 1 : 0.7,
  }));

  const projects = SITE_PROJECTS.map((p) => ({
    url: `${base}/projects/${p.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.8,
  }));

  const calculators = SITE_CALCULATORS.map((c) => ({
    url: `${base}/calculators/${c.slug}`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.6,
  }));

  const articles = SITE_ARTICLES.map((a) => ({
    url: `${base}/insights/${a.slug}`,
    lastModified: new Date(a.publishedAt),
    changeFrequency: 'monthly' as const,
    priority: 0.65,
  }));

  return [...staticRoutes, ...projects, ...calculators, ...articles];
}
