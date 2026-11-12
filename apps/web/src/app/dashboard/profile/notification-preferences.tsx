'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  fetchNotificationPreferences,
  fetchPushConfig,
  saveNotificationPreferences,
  savePushSubscription,
  type NotificationPreference,
} from '@/lib/api/notifications';
import { uiError } from '@/lib/i18n/ui-error';

const EVENT_KEYS = [
  'instagram_message',
  'facebook_message',
  'new_lead',
  'task_reminder',
  'task_overdue',
  'meeting_reminder',
  'agreement_event',
  'social_publish',
] as const;

export function NotificationPreferences() {
  const t = useTranslations('profile');
  const [items, setItems] = useState<NotificationPreference[] | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    void fetchNotificationPreferences()
      .then((response) => {
        if (active) setItems(response.items);
      })
      .catch(() => {
        if (!active) return;
        setItems(EVENT_KEYS.map((event_key) => ({ event_key, in_app: true, email: false })));
      });
    return () => {
      active = false;
    };
  }, []);

  const update = (eventKey: string, field: 'in_app' | 'email', value: boolean) => {
    setItems((current) =>
      (current || []).map((item) => (item.event_key === eventKey ? { ...item, [field]: value } : item)),
    );
  };

  const save = async () => {
    if (!items || saving) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const response = await saveNotificationPreferences(items);
      setItems(response.items);
      setMessage(t('notificationsSaved'));
    } catch (err) {
      setError(uiError(err, t('notificationsSaveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const enableDesktop = async () => {
    if (typeof Notification === 'undefined') return;
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return;
    const config = await fetchPushConfig().catch(() => ({ configured: false, public_key: null }));
    if (!config.configured || !config.public_key || !('serviceWorker' in navigator)) return;
    const registration = await navigator.serviceWorker.register('/notification-sw.js');
    const key = Uint8Array.from(atob(config.public_key.replace(/-/g, '+').replace(/_/g, '/')), (char) => char.charCodeAt(0));
    const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key });
    await savePushSubscription(subscription.toJSON());
  };

  return (
    <section className="admin-detail">
      <h2>{t('notificationsTitle')}</h2>
      <p>{t('notificationsHint')}</p>
      <button type="button" className="notification-item__open" data-testid="desktop-notifications-enable" onClick={() => void enableDesktop()}>
        Masaüstü bildirimleri
      </button>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t('notificationsTitle')}</th>
              <th>{t('channelInApp')}</th>
              <th>{t('channelEmail')}</th>
            </tr>
          </thead>
          <tbody>
            {(items || []).map((item) => (
              <tr key={item.event_key}>
                <td>{t(`event.${item.event_key}` as 'event.new_lead')}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={item.in_app}
                    aria-label={`${t(`event.${item.event_key}` as 'event.new_lead')} ${t('channelInApp')}`}
                    onChange={(event) => update(item.event_key, 'in_app', event.target.checked)}
                  />
                </td>
                <td>
                  <input
                    type="checkbox"
                    checked={item.email}
                    aria-label={`${t(`event.${item.event_key}` as 'event.new_lead')} ${t('channelEmail')}`}
                    onChange={(event) => update(item.event_key, 'email', event.target.checked)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {message ? <p className="auth-form__success">{message}</p> : null}
      {error ? <p className="auth-form__error">{error}</p> : null}
      <button className="auth-form__submit" type="button" disabled={saving || !items} onClick={() => void save()}>
        {saving ? t('saving') : t('save')}
      </button>
    </section>
  );
}
