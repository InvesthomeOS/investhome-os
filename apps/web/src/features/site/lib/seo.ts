import type { Metadata } from 'next';

import { getSiteUrl, SITE_NAME } from './site-config';

export function siteAbsoluteUrl(path = '/'): string {
  const base = getSiteUrl();
  if (!path || path === '/') return base;
  return `${base}${path.startsWith('/') ? path : `/${path}`}`;
}

export function buildSiteMetadata(opts: {
  title: string;
  description: string;
  path?: string;
  locale?: string;
  image?: string;
  type?: 'website' | 'article';
}): Metadata {
  const url = siteAbsoluteUrl(opts.path || '/');
  const image = opts.image || siteAbsoluteUrl('/brand/logos/investhome-logo-color.png');
  const title = opts.title.includes(SITE_NAME) ? opts.title : `${opts.title} · ${SITE_NAME}`;

  return {
    title,
    description: opts.description,
    alternates: { canonical: url },
    openGraph: {
      type: opts.type || 'website',
      url,
      title,
      description: opts.description,
      siteName: SITE_NAME,
      locale: opts.locale === 'en' ? 'en_US' : 'tr_TR',
      images: [{ url: image, width: 1200, height: 630, alt: SITE_NAME }],
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description: opts.description,
      images: [image],
    },
  };
}

export function organizationJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: SITE_NAME,
    url: getSiteUrl(),
    logo: siteAbsoluteUrl('/brand/logos/investhome-logo-color.png'),
    sameAs: [],
  };
}

export function websiteJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: SITE_NAME,
    url: getSiteUrl(),
    potentialAction: {
      '@type': 'SearchAction',
      target: `${getSiteUrl()}/insights?q={search_term_string}`,
      'query-input': 'required name=search_term_string',
    },
  };
}

export function articleJsonLd(article: {
  title: string;
  description: string;
  path: string;
  publishedAt: string;
  authorName: string;
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: article.title,
    description: article.description,
    datePublished: article.publishedAt,
    author: { '@type': 'Person', name: article.authorName },
    publisher: {
      '@type': 'Organization',
      name: SITE_NAME,
      logo: {
        '@type': 'ImageObject',
        url: siteAbsoluteUrl('/brand/logos/investhome-logo-color.png'),
      },
    },
    mainEntityOfPage: siteAbsoluteUrl(article.path),
  };
}

export function realEstateJsonLd(project: {
  name: string;
  description: string;
  path: string;
  city: string;
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'RealEstateListing',
    name: project.name,
    description: project.description,
    url: siteAbsoluteUrl(project.path),
    address: {
      '@type': 'PostalAddress',
      addressLocality: project.city,
      addressCountry: 'TR',
    },
  };
}
