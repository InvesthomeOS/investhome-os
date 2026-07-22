'use client';

import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  createKnowledgeCategory,
  fetchKnowledgeCategories,
  fetchKnowledgePlaceholders,
  fetchKnowledgeSettings,
  updateKnowledgeSettings,
  type KnowledgeCategory,
  type KnowledgePlaceholder,
  type KnowledgeSettings,
} from '@/lib/api/knowledge';
import { useAuth } from '@/lib/auth/auth-context';
import { canManageKnowledge } from '@/lib/knowledge/knowledge-permissions';
import { KnowledgeHubShell } from '../_components/knowledge-hub-shell';
import { KnowledgeProviderBadge } from '../_components/knowledge-provider-badge';

export default function KnowledgeSettingsPage() {
  const t = useTranslations('knowledge');
  const locale = useLocale();
  const { user } = useAuth();
  const canManage = canManageKnowledge(user);
  const [settings, setSettings] = useState<KnowledgeSettings | null>(null);
  const [categories, setCategories] = useState<KnowledgeCategory[]>([]);
  const [placeholders, setPlaceholders] = useState<KnowledgePlaceholder[]>([]);
  const [catCode, setCatCode] = useState('');
  const [catEn, setCatEn] = useState('');
  const [catTr, setCatTr] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, c, p] = await Promise.all([
        fetchKnowledgeSettings(),
        fetchKnowledgeCategories(),
        fetchKnowledgePlaceholders(),
      ]);
      setSettings(s);
      setCategories(c);
      setPlaceholders(p);
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    try {
      const updated = await updateKnowledgeSettings({
        auto_enqueue_review_on_low_confidence: settings.auto_enqueue_review_on_low_confidence,
        expiration_alert_days: settings.expiration_alert_days,
        enable_duplicate_detection: settings.enable_duplicate_detection,
      });
      setSettings(updated);
    } catch {
      setError(t('settings.saveError'));
    }
  };

  const handleAddCategory = async () => {
    if (!catCode.trim() || !catEn.trim() || !catTr.trim()) return;
    try {
      await createKnowledgeCategory({
        code: catCode.trim(),
        name_en: catEn.trim(),
        name_tr: catTr.trim(),
      });
      setCatCode('');
      setCatEn('');
      setCatTr('');
      await load();
    } catch {
      setError(t('settings.categoryError'));
    }
  };

  return (
    <KnowledgeHubShell title={t('nav.settings')} subtitle={t('settings.subtitle')}>
      {loading && <p>{t('loading')}</p>}
      {error && <p role="alert">{error}</p>}

      {settings && (
        <>
          <section className="knowledge-hub__settings" aria-label={t('settings.hub')}>
            <h2 className="knowledge-hub__section-title">{t('settings.hub')}</h2>
            <label className="knowledge-hub__check">
              <input
                type="checkbox"
                checked={settings.auto_enqueue_review_on_low_confidence}
                disabled={!canManage}
                onChange={(e) =>
                  setSettings({ ...settings, auto_enqueue_review_on_low_confidence: e.target.checked })
                }
              />
              {t('settings.autoReview')}
            </label>
            <label className="knowledge-hub__check">
              <input
                type="checkbox"
                checked={settings.enable_duplicate_detection}
                disabled={!canManage}
                onChange={(e) =>
                  setSettings({ ...settings, enable_duplicate_detection: e.target.checked })
                }
              />
              {t('settings.duplicates')}
            </label>
            <label>
              {t('settings.expirationDays')}
              <input
                type="number"
                min={1}
                max={365}
                value={settings.expiration_alert_days}
                disabled={!canManage}
                onChange={(e) =>
                  setSettings({ ...settings, expiration_alert_days: Number(e.target.value) || 30 })
                }
              />
            </label>
            {canManage && (
              <button type="button" className="button" onClick={() => void handleSave()}>
                {t('settings.save')}
              </button>
            )}
          </section>

          <section aria-label={t('providers.title')}>
            <h2 className="knowledge-hub__section-title">{t('providers.title')}</h2>
            <div className="knowledge-hub__provider-grid">
              {Object.entries(settings.providers).map(([key, status]) => (
                <KnowledgeProviderBadge
                  key={key}
                  label={t(`providers.${key}` as 'providers.ai')}
                  status={status}
                />
              ))}
            </div>
          </section>
        </>
      )}

      <section aria-label={t('settings.categories')}>
        <h2 className="knowledge-hub__section-title">{t('settings.categories')}</h2>
        {canManage && (
          <div className="knowledge-hub__form-row">
            <input value={catCode} onChange={(e) => setCatCode(e.target.value)} placeholder="code" aria-label="code" />
            <input value={catEn} onChange={(e) => setCatEn(e.target.value)} placeholder="EN" aria-label="EN" />
            <input value={catTr} onChange={(e) => setCatTr(e.target.value)} placeholder="TR" aria-label="TR" />
            <button type="button" className="button" onClick={() => void handleAddCategory()}>
              {t('settings.addCategory')}
            </button>
          </div>
        )}
        <ul className="knowledge-hub__list">
          {categories.map((c) => (
            <li key={c.id} className="knowledge-hub__list-item">
              <strong>{locale.startsWith('tr') ? c.name_tr : c.name_en}</strong>
              <span>{c.code}</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-label={t('settings.placeholders')}>
        <h2 className="knowledge-hub__section-title">{t('settings.placeholders')}</h2>
        <ul className="knowledge-hub__list">
          {placeholders.map((p) => (
            <li key={p.feature} className="knowledge-hub__list-item">
              <div>
                <strong>{p.feature}</strong>
                <p>{p.description}</p>
                {p.required_env.length > 0 && (
                  <p className="knowledge-hub__provider-env">{p.required_env.join(', ')}</p>
                )}
              </div>
              <span>{p.status}</span>
            </li>
          ))}
        </ul>
      </section>
    </KnowledgeHubShell>
  );
}
