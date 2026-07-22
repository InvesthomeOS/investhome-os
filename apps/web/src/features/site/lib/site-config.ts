/** Public website configuration — env-driven, no secrets hardcoded. */

export const SITE_NAME = 'Investhome';
export const SITE_TAGLINE_EN = 'Premium real estate investment';
export const SITE_TAGLINE_TR = 'Premium gayrimenkul yatırımı';

export function getSiteUrl(): string {
  return (
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, '') ||
    process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, '') ||
    'http://localhost:3000'
  );
}

/** Marketing form slugs expected in the CRM/Marketing workspace (published forms). */
export const SITE_FORM_SLUGS = {
  consultation: process.env.NEXT_PUBLIC_SITE_FORM_CONSULTATION || 'site-consultation',
  guide: process.env.NEXT_PUBLIC_SITE_FORM_GUIDE || 'site-guide-download',
  brochure: process.env.NEXT_PUBLIC_SITE_FORM_BROCHURE || 'site-brochure',
  analysis: process.env.NEXT_PUBLIC_SITE_FORM_ANALYSIS || 'site-investment-analysis',
  newsletter: process.env.NEXT_PUBLIC_SITE_FORM_NEWSLETTER || 'site-newsletter',
  meeting: process.env.NEXT_PUBLIC_SITE_FORM_MEETING || 'site-schedule-meeting',
  calculator: process.env.NEXT_PUBLIC_SITE_FORM_CALCULATOR || 'site-calculator-lead',
  contact: process.env.NEXT_PUBLIC_SITE_FORM_CONTACT || 'site-contact',
} as const;

export type SiteFormIntent = keyof typeof SITE_FORM_SLUGS;

export const ANALYTICS_ENV = {
  ga4Id: process.env.NEXT_PUBLIC_GA4_MEASUREMENT_ID || '',
  metaPixelId: process.env.NEXT_PUBLIC_META_PIXEL_ID || '',
  linkedInPartnerId: process.env.NEXT_PUBLIC_LINKEDIN_PARTNER_ID || '',
  googleAdsId: process.env.NEXT_PUBLIC_GOOGLE_ADS_ID || '',
} as const;
