export type TrustStat = {
  id: string;
  value: string;
  label: { en: string; tr: string };
};

export type TrustPartner = {
  id: string;
  name: string;
};

export type TrustTestimonial = {
  id: string;
  quote: { en: string; tr: string };
  name: string;
  role: { en: string; tr: string };
};

/** Honest placeholders — empty reviews until CRM/marketing review feeds are wired. */
export const SITE_TRUST = {
  stats: [
    {
      id: 'years',
      value: '15+',
      label: { en: 'Years investing discipline', tr: 'Yıllık yatırım disiplini' },
    },
    {
      id: 'projects',
      value: '40+',
      label: { en: 'Projects delivered or in pipeline', tr: 'Teslim edilen veya pipeline proje' },
    },
    {
      id: 'cities',
      value: '8',
      label: { en: 'Cities with active focus', tr: 'Aktif odak şehir' },
    },
    {
      id: 'investors',
      value: '1.2k+',
      label: { en: 'Investor relationships', tr: 'Yatırımcı ilişkisi' },
    },
  ] satisfies TrustStat[],
  partners: [
    { id: 'p1', name: 'Regional banking partners' },
    { id: 'p2', name: 'Institutional advisors' },
    { id: 'p3', name: 'Design & delivery studios' },
    { id: 'p4', name: 'Property management network' },
  ] satisfies TrustPartner[],
  /** No fabricated quotes — empty until real testimonials are sourced. */
  testimonials: [] as TrustTestimonial[],
  reviews: [] as { id: string; score: number; source: string }[],
};
