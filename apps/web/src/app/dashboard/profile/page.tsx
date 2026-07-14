'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { DashboardHeaderActions } from '@/app/dashboard/_components/dashboard-header-actions';
import { changePassword } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';

export default function ProfilePage() {
  const t = useTranslations('profile');
  const tCommon = useTranslations('common');
  const { user, refresh } = useAuth();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handlePasswordChange = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage(null);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      await changePassword(String(form.get('current_password')), String(form.get('new_password')));
      setMessage(t('passwordUpdated'));
      event.currentTarget.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('passwordUpdateFailed'));
    }
  };

  if (!user) {
    return (
      <main className="dashboard">
        <p>{tCommon('loading')}</p>
      </main>
    );
  }

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <div>
          <p className="dashboard__eyebrow">{t('eyebrow')}</p>
          <h1 className="dashboard__title">{t('title')}</h1>
        </div>
        <DashboardHeaderActions />
      </header>

      <section className="admin-detail">
        <h2>{user.full_name}</h2>
        <p>{user.email}</p>
        <p>{user.job_title ?? tCommon('noValue')}</p>
        <p>{user.department ?? tCommon('noValue')}</p>
        <p>{t('roles')}: {user.roles.map((role) => role.name).join(', ')}</p>
        <p>{t('language')}: {user.preferred_language}</p>
        <p>{t('timezone')}: {user.timezone}</p>
      </section>

      <section className="admin-detail">
        <h2>{t('changePassword')}</h2>
        <form className="auth-form" onSubmit={(event) => void handlePasswordChange(event)}>
          <label className="auth-form__field">
            <span>{t('currentPassword')}</span>
            <input name="current_password" type="password" minLength={8} required />
          </label>
          <label className="auth-form__field">
            <span>{t('newPassword')}</span>
            <input name="new_password" type="password" minLength={8} required />
          </label>
          {message && <p className="auth-form__success">{message}</p>}
          {error && <p className="auth-form__error">{error}</p>}
          <button className="auth-form__submit" type="submit">
            {t('updatePassword')}
          </button>
        </form>
      </section>
    </main>
  );
}
