import type { MetadataRoute } from 'next';

import { getSiteUrl } from '@/features/site/lib/site-config';

export default function robots(): MetadataRoute.Robots {
  const base = getSiteUrl();
  return {
    rules: [
      {
        userAgent: '*',
        allow: ['/', '/projects', '/calculators', '/insights', '/contact', '/lead', '/workflow'],
        disallow: ['/dashboard', '/company', '/workspaces', '/api', '/login'],
      },
    ],
    sitemap: `${base}/sitemap.xml`,
    host: base,
  };
}
