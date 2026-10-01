'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { ApiError } from '@/lib/api/client';
import { mapMfaHttpError } from '@/lib/auth/mfa-flow';

export function MfaVerifyForm({
  onVerify,
  onBack,
}: {
  onVerify: (code: string) => Promise<void>;
  onBack: () => void;
}) {
  const t = useTranslations('auth.mfa');
  const [code, setCode] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const submitted = code.trim();
    setCode('');
    try {
      await onVerify(submitted);
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      setError(t(`errors.${mapMfaHttpError(status)}`));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-card__mfa" data-testid="mfa-verify-screen">
      <h1 className="auth-card__title">{t('title')}</h1>
      <p className="auth-card__subtitle">{t('subtitle')}</p>

      <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
        <label className="auth-form__field">
          <span>{t('codeLabel')}</span>
          <input
            data-testid="mfa-verify-code"
            name="mfa_code"
            type="text"
            inputMode="text"
            autoComplete="one-time-code"
            autoCapitalize="characters"
            spellCheck={false}
            required
            minLength={6}
            maxLength={32}
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </label>

        {error && (
          <p className="auth-form__error" data-testid="mfa-verify-error" role="alert">
            {error}
          </p>
        )}

        <button className="auth-form__submit" type="submit" disabled={submitting} data-testid="mfa-verify-submit">
          {submitting ? t('submitting') : t('submit')}
        </button>
      </form>

      <button className="auth-form__back" type="button" onClick={onBack} data-testid="mfa-verify-back">
        {t('back')}
      </button>
    </div>
  );
}
