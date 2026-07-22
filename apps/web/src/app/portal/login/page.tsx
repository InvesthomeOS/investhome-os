'use client';

import { Suspense, useState } from 'react';
import type { Route } from 'next';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';

function PortalLoginForm() {
  const t = useTranslations('portalG9');
  const router = useRouter();
  const search = useSearchParams();
  const [email, setEmail] = useState('investor.a@investhome.demo');
  const [password, setPassword] = useState('Portal123!');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const res = await fetch('/api/portal/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        setError(t('login.error'));
        return;
      }
      const next = (search.get('next') || '/portal') as Route;
      router.replace(next);
      router.refresh();
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="portal-login__card" onSubmit={onSubmit}>
      <h1 className="portal-login__brand">{t('brand')}</h1>
      <p className="portal-login__sub">{t('login.subtitle')}</p>
      <h2 style={{ margin: '0 0 0.85rem', fontSize: '1.05rem' }}>{t('login.title')}</h2>
      {error ? <p className="portal-login__error">{error}</p> : null}
      <label>
        {t('login.email')}
        <input
          type="email"
          name="email"
          autoComplete="username"
          value={email}
          onChange={(ev) => setEmail(ev.target.value)}
          required
          data-testid="portal-login-email"
        />
      </label>
      <label>
        {t('login.password')}
        <input
          type="password"
          name="password"
          autoComplete="current-password"
          value={password}
          onChange={(ev) => setPassword(ev.target.value)}
          required
          data-testid="portal-login-password"
        />
      </label>
      <button
        type="submit"
        className="portal-login__submit"
        disabled={pending}
        data-testid="portal-login-submit"
      >
        {t('login.submit')}
      </button>
      <div className="portal-login__hint" data-testid="portal-login-hint">
        {t('login.hint')}
      </div>
    </form>
  );
}

export default function PortalLoginPage() {
  return (
    <div className="portal-login" data-testid="portal-login">
      <Suspense fallback={<div className="portal-login__card">…</div>}>
        <PortalLoginForm />
      </Suspense>
    </div>
  );
}
