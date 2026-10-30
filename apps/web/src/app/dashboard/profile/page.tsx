'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { MfaEnrollCard } from '@/components/auth/mfa-enroll-card';
import { changePassword, updateMyProfile } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { profileNameParts } from '@/lib/auth/greeting';

const TIMEZONES = [
  'Europe/Istanbul',
  'Europe/London',
  'Europe/Berlin',
  'Europe/Paris',
  'Europe/Moscow',
  'Asia/Dubai',
  'Asia/Riyadh',
  'America/New_York',
  'America/Chicago',
  'America/Los_Angeles',
  'UTC',
] as const;

export default function ProfilePage() {
  const t = useTranslations('profile');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { user, refresh } = useAuth();
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [appliedKey, setAppliedKey] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [language, setLanguage] = useState<'tr' | 'en'>('tr');
  const [timezone, setTimezone] = useState('Europe/Istanbul');
  const loadedKey = user
    ? `${user.id}|${user.full_name}|${user.preferred_language}|${user.timezone}`
    : '';
  if (user && !saving && appliedKey !== loadedKey) {
    const parts = profileNameParts(user.full_name);
    setAppliedKey(loadedKey);
    setFirstName(parts.first);
    setLastName(parts.last);
    setLanguage(user.preferred_language === 'en' ? 'en' : 'tr');
    setTimezone(user.timezone || 'Europe/Istanbul');
  }

  const handlePasswordChange = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPasswordMessage(null);
    setPasswordError(null);
    const form = new FormData(event.currentTarget);
    try {
      await changePassword(String(form.get('current_password')), String(form.get('new_password')));
      setPasswordMessage(t('passwordUpdated'));
      event.currentTarget.reset();
      await refresh();
    } catch (err) {
      setPasswordError(err instanceof ApiError ? err.message : t('passwordUpdateFailed'));
    }
  };

  const handleProfileSave = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (saving) return;
    setProfileMessage(null);
    setProfileError(null);
    const nextFirst = firstName.trim();
    const nextLast = lastName.trim();
    if (!nextFirst && !nextLast) {
      setProfileError(t('nameRequired'));
      return;
    }
    setSaving(true);
    try {
      await updateMyProfile({
        first_name: nextFirst,
        last_name: nextLast,
        preferred_language: language,
        timezone,
      });
      setFirstName(nextFirst);
      setLastName(nextLast);
      setProfileMessage(t('saved'));
      await refresh();
      router.refresh();
    } catch {
      setProfileError(t('saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  if (!user) {
    return (
      <main className="dashboard">
        <p>{tCommon('loading')}</p>
      </main>
    );
  }

  const roleNames = user.roles.map((role) => role.name).filter(Boolean);
  const languageLabel = user.preferred_language === 'en' ? t('languageEn') : t('languageTr');
  const timezoneOptions = (TIMEZONES as readonly string[]).includes(timezone)
    ? TIMEZONES
    : [timezone, ...TIMEZONES];

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{user.full_name}</h1>
        <p>{user.email}</p>
      </header>

      <section className="admin-detail">
        {roleNames.length > 0 ? (
          <p>
            {t('role')}: {roleNames.join(', ')}
          </p>
        ) : null}
        {user.department ? (
          <p>
            {t('department')}: {user.department}
          </p>
        ) : null}
        {user.job_title ? (
          <p>
            {t('jobTitle')}: {user.job_title}
          </p>
        ) : null}
        <p>
          {t('language')}: {languageLabel}
        </p>
        <p>
          {t('timezone')}: {user.timezone}
        </p>
        <p>
          {t('permissions')}: {t('permissionsManaged')}
        </p>
      </section>

      <section className="admin-detail">
        <h2>{t('personal')}</h2>
        <form className="auth-form" onSubmit={(event) => void handleProfileSave(event)}>
          <label className="auth-form__field">
            <span>{t('firstName')}</span>
            <input
              name="first_name"
              value={firstName}
              maxLength={120}
              autoComplete="given-name"
              onChange={(event) => setFirstName(event.target.value)}
            />
          </label>
          <label className="auth-form__field">
            <span>{t('lastName')}</span>
            <input
              name="last_name"
              value={lastName}
              maxLength={120}
              autoComplete="family-name"
              onChange={(event) => setLastName(event.target.value)}
            />
          </label>
          <label className="auth-form__field">
            <span>{t('language')}</span>
            <select
              name="preferred_language"
              value={language}
              onChange={(event) => setLanguage(event.target.value === 'en' ? 'en' : 'tr')}
            >
              <option value="tr">{t('languageTr')}</option>
              <option value="en">{t('languageEn')}</option>
            </select>
          </label>
          <label className="auth-form__field">
            <span>{t('timezone')}</span>
            <select name="timezone" value={timezone} onChange={(event) => setTimezone(event.target.value)}>
              {timezoneOptions.map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
          </label>
          {profileMessage ? <p className="auth-form__success">{profileMessage}</p> : null}
          {profileError ? <p className="auth-form__error">{profileError}</p> : null}
          <button className="auth-form__submit" type="submit" disabled={saving}>
            {saving ? t('saving') : t('save')}
          </button>
        </form>
      </section>

      <MfaEnrollCard mfaEnabled={Boolean(user.mfa_enabled)} onEnabled={refresh} />

      <section className="admin-detail">
        <h2>{t('changePassword')}</h2>
        <form className="auth-form" onSubmit={(event) => void handlePasswordChange(event)}>
          <label className="auth-form__field">
            <span>{t('currentPassword')}</span>
            <input name="current_password" type="password" minLength={8} required />
          </label>
          <label className="auth-form__field">
            <span>{t('newPassword')}</span>
            <input name="new_password" type="password" minLength={12} maxLength={256} required />
          </label>
          {passwordMessage ? <p className="auth-form__success">{passwordMessage}</p> : null}
          {passwordError ? <p className="auth-form__error">{passwordError}</p> : null}
          <button className="auth-form__submit" type="submit">
            {t('updatePassword')}
          </button>
        </form>
      </section>
    </main>
  );
}
