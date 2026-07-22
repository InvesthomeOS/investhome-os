'use client';

import { useLocale } from 'next-intl';
import { useState } from 'react';

import { useAdoptionTour } from '@/components/adoption/tour-provider';
import { PRODUCT_TOURS } from '@/lib/adoption/content';
import { updateAdoptionState } from '@/lib/adoption/progress-store';
import type { BuilderDraft, ContentStatus } from '@/lib/adoption/types';

function emptyDraft(): BuilderDraft {
  return {
    id: `draft-${Date.now()}`,
    title: '',
    description: '',
    contentType: 'tour',
    workspace: 'dashboard',
    route: '/dashboard/onboarding',
    role: 'admin',
    language: 'tr',
    version: '1.0.0',
    owner: 'Admin',
    status: 'draft',
    targetSelector: '[data-tour="onboarding-welcome"]',
    completionCondition: 'viewed',
    prerequisite: '',
    deadline: '',
    mandatory: false,
    estimatedDuration: 10,
  };
}

export function TrainingBuilderWorkspace() {
  const locale = useLocale();
  const { userId, state, refreshState } = useAdoptionTour();
  const [draft, setDraft] = useState<BuilderDraft>(emptyDraft);
  const [message, setMessage] = useState<string | null>(null);
  const [preview, setPreview] = useState(false);

  const validateSelectors = (): string[] => {
    const errors: string[] = [];
    if (!draft.targetSelector.trim()) {
      errors.push(locale === 'en' ? 'Target selector required' : 'Hedef seçici gerekli');
      return errors;
    }
    if (typeof document !== 'undefined') {
      const el = document.querySelector(draft.targetSelector);
      // Builder page may not contain target — also accept known tour selectors
      const known = PRODUCT_TOURS.flatMap((t) => t.steps.map((s) => s.selector));
      if (!el && !known.includes(draft.targetSelector) && !draft.targetSelector.startsWith('[data-tour=')) {
        errors.push(locale === 'en' ? 'Selector not stable / not found' : 'Seçici kararlı değil / bulunamadı');
      }
      if (draft.targetSelector.includes('nth-child') || draft.targetSelector.includes(' > div >')) {
        errors.push(locale === 'en' ? 'Fragile CSS selector blocked' : 'Kırılgan CSS seçici engellendi');
      }
    }
    return errors;
  };

  const saveDraft = (status: ContentStatus) => {
    if (status === 'published') {
      const errors = validateSelectors();
      if (errors.length) {
        setMessage(errors.join(' · '));
        return;
      }
    }
    const next = { ...draft, status };
    updateAdoptionState(userId, (prev) => ({
      ...prev,
      drafts: [...prev.drafts.filter((d) => (d as BuilderDraft).id !== next.id), next],
    }));
    refreshState();
    setDraft(next);
    setMessage(
      status === 'published'
        ? locale === 'en'
          ? 'Published (versioned).'
          : 'Yayınlandı (sürümlendi).'
        : locale === 'en'
          ? 'Draft saved.'
          : 'Taslak kaydedildi.',
    );
  };

  return (
    <main className="adop-g13" data-testid="adop-training-builder" data-tour="training-builder">
      <header className="adop-g13__top">
        <div>
          <p className="adop-g13__eyebrow">G13 · Admin</p>
          <h1 className="adop-g13__title">
            {locale === 'en' ? 'Training builder' : 'Eğitim oluşturucu'}
          </h1>
          <p className="adop-g13__subtitle">
            {locale === 'en'
              ? 'Create tours, checklists, articles, paths. Publish blocked if selectors are broken.'
              : 'Tur, liste, makale, yol oluşturun. Bozuk seçicilerde yayın engellenir.'}
          </p>
        </div>
        <div className="adop-g13__top-actions">
          <button type="button" className="adop-g13__btn" onClick={() => setPreview((v) => !v)} data-testid="adop-builder-preview">
            {locale === 'en' ? 'Preview' : 'Önizleme'}
          </button>
          <button type="button" className="adop-g13__btn" onClick={() => saveDraft('draft')} data-testid="adop-builder-save">
            {locale === 'en' ? 'Save draft' : 'Taslak kaydet'}
          </button>
          <button type="button" className="adop-g13__btn adop-g13__btn--primary" onClick={() => saveDraft('published')} data-testid="adop-builder-publish">
            {locale === 'en' ? 'Publish' : 'Yayınla'}
          </button>
        </div>
      </header>

      <div className="adop-g13__body">
        <div className="adop-g13__grid">
          <section className="adop-g13__panel adop-g13__panel--8">
            <h2 className="adop-g13__panel-title">{locale === 'en' ? 'Content fields' : 'İçerik alanları'}</h2>
            <div className="adop-g13__form-grid">
              {(
                [
                  ['title', 'Title', 'Başlık'],
                  ['description', 'Description', 'Açıklama'],
                  ['contentType', 'Content type', 'İçerik tipi'],
                  ['workspace', 'Workspace', 'Çalışma alanı'],
                  ['route', 'Route', 'Rota'],
                  ['targetSelector', 'Target selector', 'Hedef seçici'],
                  ['completionCondition', 'Completion condition', 'Tamamlanma koşulu'],
                  ['prerequisite', 'Prerequisite', 'Önkoşul'],
                  ['deadline', 'Deadline', 'Son tarih'],
                  ['version', 'Version', 'Sürüm'],
                  ['owner', 'Owner', 'Sahip'],
                ] as const
              ).map(([key, en, tr]) => (
                <label key={key} className="adop-g13__label">
                  {locale === 'en' ? en : tr}
                  <input
                    className="adop-g13__field"
                    value={String(draft[key])}
                    data-testid={`adop-builder-${key}`}
                    onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))}
                  />
                </label>
              ))}
              <label className="adop-g13__label">
                {locale === 'en' ? 'Language' : 'Dil'}
                <select
                  className="adop-g13__field"
                  value={draft.language}
                  onChange={(e) => setDraft((d) => ({ ...d, language: e.target.value as 'tr' | 'en' }))}
                >
                  <option value="tr">tr</option>
                  <option value="en">en</option>
                </select>
              </label>
              <label className="adop-g13__label">
                {locale === 'en' ? 'Estimated duration (min)' : 'Tahmini süre (dk)'}
                <input
                  className="adop-g13__field"
                  type="number"
                  value={draft.estimatedDuration}
                  onChange={(e) => setDraft((d) => ({ ...d, estimatedDuration: Number(e.target.value) }))}
                />
              </label>
              <label className="adop-g13__check" style={{ border: 0 }}>
                <input
                  type="checkbox"
                  checked={draft.mandatory}
                  onChange={(e) => setDraft((d) => ({ ...d, mandatory: e.target.checked }))}
                />
                <span>{locale === 'en' ? 'Mandatory' : 'Zorunlu'}</span>
              </label>
            </div>
            {message ? (
              <div className="adop-g13__banner" style={{ marginTop: '0.75rem' }} data-testid="adop-builder-msg">
                {message}
              </div>
            ) : null}
          </section>

          <section className="adop-g13__panel adop-g13__panel--4">
            <h2 className="adop-g13__panel-title">{locale === 'en' ? 'Version history' : 'Sürüm geçmişi'}</h2>
            <ul className="adop-g13__list">
              <li className="adop-g13__list-item">
                <span>v{draft.version}</span>
                <span className="adop-g13__pill">{draft.status}</span>
              </li>
              {state.drafts.slice(-5).map((d) => {
                const item = d as BuilderDraft;
                return (
                  <li key={item.id} className="adop-g13__list-item">
                    <span>{item.title || item.id}</span>
                    <span className="adop-g13__pill">{item.status}</span>
                  </li>
                );
              })}
            </ul>
            {preview ? (
              <div style={{ marginTop: '0.75rem' }} data-testid="adop-builder-preview-pane">
                <h3 className="adop-g13__panel-title">{draft.title || (locale === 'en' ? 'Untitled' : 'Başlıksız')}</h3>
                <p className="adop-g13__muted">{draft.description}</p>
                <code className="adop-g13__muted">{draft.targetSelector}</code>
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </main>
  );
}
