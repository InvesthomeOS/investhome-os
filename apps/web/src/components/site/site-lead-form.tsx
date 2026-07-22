'use client';

import { FormEvent, useState } from 'react';
import { useTranslations } from 'next-intl';

import { trackSiteEvent } from '@/components/site/site-analytics';
import { submitSiteLead } from '@/features/site/lib/lead-submit';
import type { SiteFormIntent } from '@/features/site/lib/site-config';

type Field = {
  name: string;
  type?: 'text' | 'email' | 'tel' | 'textarea' | 'select';
  required?: boolean;
  options?: { value: string; label: string }[];
};

const INTENT_FIELDS: Record<SiteFormIntent, Field[]> = {
  consultation: [
    { name: 'full_name', required: true },
    { name: 'email', type: 'email', required: true },
    { name: 'phone', type: 'tel' },
    { name: 'message', type: 'textarea' },
  ],
  guide: [
    { name: 'full_name', required: true },
    { name: 'email', type: 'email', required: true },
  ],
  brochure: [
    { name: 'full_name', required: true },
    { name: 'email', type: 'email', required: true },
    { name: 'project', type: 'text' },
  ],
  analysis: [
    { name: 'full_name', required: true },
    { name: 'email', type: 'email', required: true },
    { name: 'phone', type: 'tel' },
    { name: 'budget', type: 'text' },
    { name: 'message', type: 'textarea' },
  ],
  newsletter: [{ name: 'email', type: 'email', required: true }, { name: 'full_name' }],
  meeting: [
    { name: 'full_name', required: true },
    { name: 'email', type: 'email', required: true },
    { name: 'phone', type: 'tel' },
    { name: 'preferred_time', type: 'text' },
    { name: 'message', type: 'textarea' },
  ],
  calculator: [
    { name: 'full_name', required: true },
    { name: 'email', type: 'email', required: true },
    { name: 'calculator', type: 'text' },
    { name: 'results_summary', type: 'textarea' },
  ],
  contact: [
    { name: 'full_name', required: true },
    { name: 'email', type: 'email', required: true },
    { name: 'phone', type: 'tel' },
    { name: 'message', type: 'textarea', required: true },
  ],
};

export function SiteLeadForm({
  intent,
  defaults,
  compact,
  onSuccess,
}: {
  intent: SiteFormIntent;
  defaults?: Record<string, string>;
  compact?: boolean;
  onSuccess?: () => void;
}) {
  const t = useTranslations('site.forms');
  const fields = INTENT_FIELDS[intent];
  const [values, setValues] = useState<Record<string, string>>(() => ({ ...(defaults || {}) }));
  const [marketing, setMarketing] = useState(false);
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'offline' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setStatus('submitting');
    setError(null);
    try {
      const payload: Record<string, string | boolean | null> = {};
      for (const f of fields) {
        payload[f.name] = values[f.name]?.trim() || null;
      }
      payload.source = `site:${intent}`;
      if (marketing) payload.marketing_opt_in = true;
      const result = await submitSiteLead(intent, payload, { email: true });
      if (!result.ok) {
        setStatus('error');
        setError(result.message);
        return;
      }
      trackSiteEvent('site_lead_submit', { intent, offline: Boolean(result.offline) });
      setStatus(result.offline ? 'offline' : 'success');
      onSuccess?.();
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Submission failed');
    }
  };

  if (status === 'success' || status === 'offline') {
    return (
      <div className="site-form__success" role="status">
        <p>{status === 'offline' ? t('offlineSuccess') : t('success')}</p>
      </div>
    );
  }

  return (
    <form className={compact ? 'site-form site-form--compact' : 'site-form'} onSubmit={onSubmit} noValidate>
      {fields.map((field) => (
        <label key={field.name} className="site-form__field">
          <span>
            {t(`fields.${field.name}`)}
            {field.required ? ' *' : ''}
          </span>
          {field.type === 'textarea' ? (
            <textarea
              name={field.name}
              rows={4}
              required={field.required}
              value={values[field.name] || ''}
              onChange={(ev) => setValues((v) => ({ ...v, [field.name]: ev.target.value }))}
            />
          ) : (
            <input
              name={field.name}
              type={field.type || 'text'}
              required={field.required}
              value={values[field.name] || ''}
              onChange={(ev) => setValues((v) => ({ ...v, [field.name]: ev.target.value }))}
            />
          )}
        </label>
      ))}

      <label className="site-form__check">
        <input
          type="checkbox"
          checked={marketing}
          onChange={(ev) => setMarketing(ev.target.checked)}
        />
        <span>{t('marketingConsent')}</span>
      </label>

      {error ? <p className="site-form__error">{error}</p> : null}

      <button type="submit" className="site-btn site-btn--primary" disabled={status === 'submitting'}>
        {status === 'submitting' ? t('submitting') : t(`submit.${intent}`)}
      </button>
    </form>
  );
}
