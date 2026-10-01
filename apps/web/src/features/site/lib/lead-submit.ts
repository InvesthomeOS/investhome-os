import { ApiError } from '@/lib/api/client';
import { SITE_FORM_SLUGS, type SiteFormIntent } from './site-config';

export type LeadSubmitValues = Record<string, string | boolean | null>;

export type LeadSubmitResult =
  | { ok: true; id: string; status: string; offline?: false }
  | { ok: true; id: string; status: 'queued_offline'; offline: true }
  | { ok: false; message: string; status?: number };

function idempotencyKey(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `site-${crypto.randomUUID()}`;
  }
  return `site-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function trackingFromBrowser() {
  if (typeof window === 'undefined') return undefined;
  const params = new URLSearchParams(window.location.search);
  return {
    utm_source: params.get('utm_source') || undefined,
    utm_medium: params.get('utm_medium') || undefined,
    utm_campaign: params.get('utm_campaign') || undefined,
    utm_content: params.get('utm_content') || undefined,
    utm_term: params.get('utm_term') || undefined,
    landing_url: window.location.href,
    referrer: document.referrer || undefined,
  };
}

function queueOffline(intent: SiteFormIntent, slug: string, values: LeadSubmitValues) {
  try {
    const key = 'ih_site_lead_queue';
    const existing = JSON.parse(sessionStorage.getItem(key) || '[]') as unknown[];
    const entry = { intent, slug, values, at: new Date().toISOString() };
    sessionStorage.setItem(key, JSON.stringify([...existing, entry].slice(-20)));
  } catch {
    // ignore storage failures
  }
  return {
    ok: true as const,
    id: `offline-${Date.now()}`,
    status: 'queued_offline' as const,
    offline: true as const,
  };
}

/**
 * Submit via same-origin Next proxy → public marketing form API.
 * 404 / timeout / network → honest offline queue (form slug may not be published yet).
 */
export async function submitSiteLead(
  intent: SiteFormIntent,
  values: LeadSubmitValues,
  consent?: { email?: boolean; phone?: boolean },
): Promise<LeadSubmitResult> {
  const slug = SITE_FORM_SLUGS[intent];
  const payload = {
    values,
    consent: {
      consent_email: consent?.email ?? true,
      consent_phone: consent?.phone ?? false,
    },
    tracking: trackingFromBrowser(),
    idempotency_key: idempotencyKey(),
    hp_website: '',
    ...(process.env.NODE_ENV === 'production'
      ? {}
      : { cf_turnstile_response: 'dev-bypass' }),
  };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);

  try {
    const response = await fetch(`/api/public/forms/${encodeURIComponent(slug)}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
      cache: 'no-store',
    });

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`;
      try {
        const body = (await response.json()) as {
          detail?: string;
          error?: { message?: string };
        };
        message = body.error?.message || (typeof body.detail === 'string' ? body.detail : message);
      } catch {
        // keep default
      }
      throw new ApiError(message, response.status);
    }

    const result = (await response.json()) as { id: string; status: string };
    return { ok: true, id: result.id, status: result.status };
  } catch (err) {
    const aborted =
      (err instanceof DOMException && err.name === 'AbortError') ||
      (err instanceof Error && /abort|timeout/i.test(err.message));
    if (
      aborted ||
      (err instanceof ApiError &&
        (err.status === 404 || err.status === 422 || err.status === 502 || err.status === 504 || err.status >= 500)) ||
      !(err instanceof ApiError)
    ) {
      return queueOffline(intent, slug, values);
    }
    const message = err instanceof Error ? err.message : 'Submission failed';
    return { ok: false, message, status: err instanceof ApiError ? err.status : undefined };
  } finally {
    clearTimeout(timer);
  }
}

export function buildShareUrl(path: string, params?: Record<string, string>): string {
  const base =
    typeof window !== 'undefined'
      ? window.location.origin
      : process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';
  const url = new URL(path, base.startsWith('http') ? base : `http://${base}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, v);
    }
  }
  return url.toString();
}
