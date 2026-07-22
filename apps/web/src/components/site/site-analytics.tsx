'use client';

import { useEffect } from 'react';

import { ANALYTICS_ENV } from '@/features/site/lib/site-config';

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
    fbq?: ((...args: unknown[]) => void) & { queue?: unknown[] };
    _fbq?: unknown;
    _linkedin_data_partner_ids?: string[];
  }
}

/**
 * Loads GA4 / Meta / LinkedIn / Google Ads only when corresponding env vars are set.
 * Never hardcodes measurement IDs or secrets.
 */
export function SiteAnalytics() {
  useEffect(() => {
    const { ga4Id, metaPixelId, linkedInPartnerId, googleAdsId } = ANALYTICS_ENV;

    if (ga4Id) {
      const s = document.createElement('script');
      s.async = true;
      s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(ga4Id)}`;
      document.head.appendChild(s);
      window.dataLayer = window.dataLayer || [];
      window.gtag = (...args: unknown[]) => {
        window.dataLayer?.push(args);
      };
      window.gtag('js', new Date());
      window.gtag('config', ga4Id);
      if (googleAdsId) {
        window.gtag('config', googleAdsId);
      }
    }

    if (metaPixelId && !window.fbq) {
      const n = ((...args: unknown[]) => {
        n.queue = n.queue || [];
        n.queue.push(args);
      }) as ((...args: unknown[]) => void) & { queue?: unknown[] };
      window.fbq = n;
      window._fbq = n;
      const t = document.createElement('script');
      t.async = true;
      t.src = 'https://connect.facebook.net/en_US/fbevents.js';
      document.head.appendChild(t);
      window.fbq('init', metaPixelId);
      window.fbq('track', 'PageView');
    }

    if (linkedInPartnerId) {
      window._linkedin_data_partner_ids = window._linkedin_data_partner_ids || [];
      window._linkedin_data_partner_ids.push(linkedInPartnerId);
      const s = document.createElement('script');
      s.async = true;
      s.src = 'https://snap.licdn.com/li.lms-analytics/insight.min.js';
      document.head.appendChild(s);
    }
  }, []);

  return null;
}

export function trackSiteEvent(name: string, params?: Record<string, string | number | boolean>) {
  try {
    window.gtag?.('event', name, params);
    window.fbq?.('trackCustom', name, params);
  } catch {
    // analytics must never break UX
  }
}
