export type SiteProject = {
  slug: string;
  href: string;
  name: { en: string; tr: string };
  location: { en: string; tr: string };
  city: string;
  summary: { en: string; tr: string };
  coverImage: string;
  coverAlt: { en: string; tr: string };
  coverPosition?: string;
  featured?: boolean;
};

/**
 * Public catalog for Investhome Washington, DC projects.
 * Copy is limited to verified names and addresses — no invented
 * unit counts, prices, yields, or sales status.
 */
export const SITE_PROJECTS: SiteProject[] = [
  {
    slug: 'the-temple',
    href: 'https://www.investhome.com/The-Temple/index.html',
    name: { en: 'THE TEMPLE', tr: 'THE TEMPLE' },
    location: { en: '1610 Columbia Rd NW, Washington, DC', tr: '1610 Columbia Rd NW, Washington, DC' },
    city: 'Washington, DC',
    featured: true,
    summary: {
      en: '1610 Columbia Rd NW, Washington, DC',
      tr: '1610 Columbia Rd NW, Washington, DC',
    },
    coverImage: '/brand/images/projects/the-temple.jpg',
    coverAlt: {
      en: 'THE TEMPLE exterior, 1610 Columbia Rd NW, Washington, DC',
      tr: 'THE TEMPLE dış görünüm, 1610 Columbia Rd NW, Washington, DC',
    },
    coverPosition: 'center 32%',
  },
  {
    slug: 'uniloft',
    href: 'https://www.investhome.com/proje/uniloft/',
    name: { en: 'UNILOFT', tr: 'UNILOFT' },
    location: { en: '300 I St NE, Washington, DC', tr: '300 I St NE, Washington, DC' },
    city: 'Washington, DC',
    featured: true,
    summary: {
      en: '300 I St NE, Washington, DC',
      tr: '300 I St NE, Washington, DC',
    },
    coverImage: '/brand/images/projects/uniloft.jpg',
    coverAlt: {
      en: 'UNILOFT exterior, 300 I St NE, Washington, DC',
      tr: 'UNILOFT dış görünüm, 300 I St NE, Washington, DC',
    },
    coverPosition: 'center 46%',
  },
  {
    slug: '1812-h-place',
    href: 'https://www.investhome.com/proje/1812-h-place/',
    name: { en: '1812 H PLACE', tr: '1812 H PLACE' },
    location: { en: '1812 H Place NE, Washington, DC', tr: '1812 H Place NE, Washington, DC' },
    city: 'Washington, DC',
    featured: true,
    summary: {
      en: '1812 H Place NE, Washington, DC',
      tr: '1812 H Place NE, Washington, DC',
    },
    coverImage: '/brand/images/projects/1812-h-place.jpg',
    coverAlt: {
      en: '1812 H Place exterior, Washington, DC',
      tr: '1812 H Place dış görünüm, Washington, DC',
    },
    coverPosition: 'center 50%',
  },
];

export function getFeaturedProjects(): SiteProject[] {
  return SITE_PROJECTS.filter((p) => p.featured);
}

export function getProjectBySlug(slug: string): SiteProject | undefined {
  return SITE_PROJECTS.find((p) => p.slug === slug);
}
