'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useParams, useRouter } from 'next/navigation';

import { BrandLogo } from '@/components/brand/brand-logo';
import { ApiError } from '@/lib/api/client';
import {
  acceptInvite,
  combinePersonName,
  fetchInvitePreview,
  splitPersonName,
  type InvitePreview,
} from '@/lib/api/auth';
import { PublicBrandingProvider } from '@/lib/company/company-context';

const HERO_SRC = '/brand/images/washington-dc-capitol.jpg';

function passwordContainsIdentity(password: string, firstName: string, lastName: string, email: string): boolean {
  const lowered = password.toLowerCase();
  const parts = [firstName, lastName, email.split('@')[0] ?? ''].map((part) => part.trim().toLowerCase());
  return parts.some((part) => part.length >= 4 && lowered.includes(part));
}

function InviteAcceptForm() {
  const t = useTranslations('auth');
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const token = typeof params.token === 'string' ? params.token : '';
  const [preview, setPreview] = useState<InvitePreview | null>(null);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchInvitePreview(token)
      .then((body) => {
        if (!cancelled) {
          const names = splitPersonName(body.full_name);
          setPreview(body);
          setFirstName(names.firstName);
          setLastName(names.lastName);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setPreview(null);
          setError(err instanceof ApiError && err.status === 404 ? t('invite.invalid') : t('invite.failed'));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [t, token]);

  const lengthOk = password.length >= 12;
  const identityOk = password.length === 0 || !passwordContainsIdentity(password, firstName, lastName, preview?.email ?? '');
  const requirementItems = [
    { ok: lengthOk, label: t('invite.ruleLength') },
    { ok: password.length > 0 && identityOk, label: t('invite.ruleIdentity') },
    { ok: null, label: t('invite.ruleCommon') },
  ];

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (password !== confirm) {
      setError(t('invite.mismatch'));
      return;
    }
    const fullName = combinePersonName(firstName, lastName);
    if (!fullName) {
      setError(t('invite.nameRequired'));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await acceptInvite(token, password, fullName);
      router.replace('/login');
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError(err.message);
      } else if (err instanceof ApiError && err.status === 404) {
        setError(t('invite.invalid'));
      } else {
        setError(t('invite.failed'));
      }
    } finally {
      setSubmitting(false);
      setPassword('');
      setConfirm('');
    }
  };

  return (
    <div className="invite-page">
      <aside className="invite-page__visual" style={{ backgroundImage: `url(${HERO_SRC})` }}>
        <div className="invite-page__visual-scrim">
          <div className="invite-page__brand">
            <BrandLogo tone="white" layout="full" className="invite-page__logo" priority />
            <p className="invite-page__product">Investhome OS</p>
            <p className="invite-page__tagline">{t('invite.tagline')}</p>
          </div>
          <div className="invite-page__story">
            <h2>{t('invite.visualTitle')}</h2>
            <p>{t('invite.visualBody')}</p>
          </div>
          <ul className="invite-page__points">
            <li>
              <strong>{t('invite.pointProjectsTitle')}</strong>
              <span>{t('invite.pointProjectsBody')}</span>
            </li>
            <li>
              <strong>{t('invite.pointTeamTitle')}</strong>
              <span>{t('invite.pointTeamBody')}</span>
            </li>
            <li>
              <strong>{t('invite.pointGrowthTitle')}</strong>
              <span>{t('invite.pointGrowthBody')}</span>
            </li>
          </ul>
        </div>
      </aside>
      <main className="invite-page__panel">
        <div className="invite-page__form-wrap">
          <h1>{t('invite.title')}</h1>
          <p className="invite-page__subtitle">{t('invite.subtitle')}</p>
          {loading ? <p className="invite-page__hint">{t('submitting')}</p> : null}
          {error && !preview ? <p className="auth-form__error">{error}</p> : null}
          {preview ? (
            <form className="invite-form" onSubmit={(event) => void handleSubmit(event)}>
              <label className="invite-form__field">
                <span>{t('invite.firstNameLabel')}</span>
                <input
                  name="first_name"
                  autoComplete="given-name"
                  required
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                />
              </label>
              <label className="invite-form__field">
                <span>{t('invite.lastNameLabel')}</span>
                <input
                  name="last_name"
                  autoComplete="family-name"
                  required
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                />
              </label>
              <label className="invite-form__field">
                <span>{t('invite.emailLabel')}</span>
                <input type="email" value={preview.email} readOnly aria-readonly="true" />
              </label>
              <label className="invite-form__field">
                <span>{t('invite.passwordLabel')}</span>
                <div className="invite-form__secret">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    minLength={12}
                    maxLength={256}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                  <button type="button" onClick={() => setShowPassword((current) => !current)}>
                    {showPassword ? t('invite.hidePassword') : t('invite.showPassword')}
                  </button>
                </div>
              </label>
              <ul className="invite-form__rules" aria-live="polite">
                {requirementItems.map((item) => (
                  <li key={item.label} data-ok={item.ok == null ? 'info' : item.ok ? 'true' : 'false'}>
                    {item.label}
                  </li>
                ))}
              </ul>
              <label className="invite-form__field">
                <span>{t('invite.confirmLabel')}</span>
                <div className="invite-form__secret">
                  <input
                    type={showConfirm ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    minLength={12}
                    maxLength={256}
                    value={confirm}
                    onChange={(event) => setConfirm(event.target.value)}
                  />
                  <button type="button" onClick={() => setShowConfirm((current) => !current)}>
                    {showConfirm ? t('invite.hidePassword') : t('invite.showPassword')}
                  </button>
                </div>
              </label>
              {error ? <p className="auth-form__error">{error}</p> : null}
              <button className="invite-form__submit" type="submit" disabled={submitting}>
                {submitting ? t('invite.submitting') : t('invite.submit')}
              </button>
            </form>
          ) : null}
        </div>
      </main>
    </div>
  );
}

export default function InviteAcceptPage() {
  return (
    <PublicBrandingProvider>
      <InviteAcceptForm />
    </PublicBrandingProvider>
  );
}
