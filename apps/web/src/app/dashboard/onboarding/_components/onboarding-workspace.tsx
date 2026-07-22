'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale } from 'next-intl';
import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import { useAdoptionTour } from '@/components/adoption/tour-provider';
import { getPathForRole, PRODUCT_TOURS } from '@/lib/adoption/content';
import { lt } from '@/lib/adoption/locale';
import { primaryAdoptionRole, resolveAdoptionRoles } from '@/lib/adoption/permissions';
import { updateAdoptionState } from '@/lib/adoption/progress-store';
import { useAuth } from '@/lib/auth/auth-context';

const STEPS = [
  { id: 'profile', en: 'Confirm profile', tr: 'Profili doğrula' },
  { id: 'language', en: 'Confirm language', tr: 'Dili doğrula' },
  { id: 'timezone', en: 'Confirm timezone', tr: 'Saat dilimini doğrula' },
  { id: 'role', en: 'Review assigned role', tr: 'Atanan rolü incele' },
  { id: 'workspaces', en: 'Review workspace access', tr: 'Çalışma alanı erişimini incele' },
  { id: 'security', en: 'Complete security setup', tr: 'Güvenlik kurulumunu tamamla' },
  { id: 'mfa', en: 'Enable MFA where required', tr: 'Gerektiğinde MFA etkinleştir' },
  { id: 'tour', en: 'Start role-based tour', tr: 'Role dayalı turu başlat' },
  { id: 'first-task', en: 'Complete first real task', tr: 'İlk gerçek görevi tamamla' },
  { id: 'checklist', en: 'Review daily checklist', tr: 'Günlük listeyi incele' },
] as const;

export function OnboardingWorkspace() {
  const locale = useLocale();
  const { user } = useAuth();
  const { startTour, state, refreshState, userId } = useAdoptionTour();
  const search = useSearchParams();
  const forceStep = search.get('step');
  const role = primaryAdoptionRole(user);
  const roles = resolveAdoptionRoles(user);
  const path = getPathForRole(role);
  const [stepIdx, setStepIdx] = useState(() => {
    if (forceStep === 'role') return 3;
    if (forceStep === 'welcome') return 0;
    return Math.min(state.onboarding.completedSteps.length, STEPS.length - 1);
  });

  const progress = useMemo(() => {
    const done = state.onboarding.completedSteps.length;
    return Math.round((done / STEPS.length) * 100);
  }, [state.onboarding.completedSteps.length]);

  const mark = (id: string) => {
    updateAdoptionState(userId, (prev) => ({
      ...prev,
      onboarding: {
        ...prev.onboarding,
        completedSteps: Array.from(new Set([...prev.onboarding.completedSteps, id])),
        languageConfirmed: id === 'language' ? true : prev.onboarding.languageConfirmed,
        timezoneConfirmed: id === 'timezone' ? true : prev.onboarding.timezoneConfirmed,
        roleReviewed: id === 'role' ? true : prev.onboarding.roleReviewed,
        tourStarted: id === 'tour' ? true : prev.onboarding.tourStarted,
        finished: id === 'checklist' ? true : prev.onboarding.finished,
        updatedAt: new Date().toISOString(),
      },
    }));
    refreshState();
  };

  const current = STEPS[stepIdx] ?? STEPS[0];
  const recommendedTour =
    PRODUCT_TOURS.find((t) => t.roles.includes(role) && t.id !== 'tour-portal') ??
    PRODUCT_TOURS[0]!;

  return (
    <main className="adop-g13" data-testid="adop-onboarding" data-tour="onboarding-root">
      <header className="adop-g13__top">
        <div>
          <p className="adop-g13__eyebrow">G13 · {locale === 'en' ? 'Onboarding' : 'Oryantasyon'}</p>
          <h1 className="adop-g13__title" data-tour="onboarding-welcome">
            {locale === 'en' ? `Welcome, ${user?.full_name ?? 'User'}` : `Hoş geldiniz, ${user?.full_name ?? 'Kullanıcı'}`}
          </h1>
          <p className="adop-g13__subtitle">
            {locale === 'en'
              ? 'Role-based interactive onboarding — learn inside the product, not from long PDFs.'
              : 'Role dayalı etkileşimli oryantasyon — uzun PDF’ler yerine ürün içinde öğrenin.'}
          </p>
        </div>
        <div className="adop-g13__top-actions">
          <span className="adop-g13__pill adop-g13__pill--brand" data-tour="onboarding-progress">
            {progress}% {locale === 'en' ? 'complete' : 'tamamlandı'}
          </span>
          <Link href={'/dashboard/training' as Route} className="adop-g13__btn">
            {locale === 'en' ? 'Training hub' : 'Eğitim merkezi'}
          </Link>
          <Link href={'/dashboard/help' as Route} className="adop-g13__btn adop-g13__btn--primary">
            {locale === 'en' ? 'Open help' : 'Yardımı aç'}
          </Link>
        </div>
      </header>

      <div className="adop-g13__body">
        <div className="adop-g13__grid">
          <section className="adop-g13__panel adop-g13__panel--6" data-testid="adop-role-setup">
            <h2 className="adop-g13__panel-title">
              {locale === 'en' ? 'Role & access' : 'Rol ve erişim'}
            </h2>
            <div className="adop-g13__kpi-row">
              <div className="adop-g13__kpi">
                <p className="adop-g13__kpi-label">{locale === 'en' ? 'Assigned role' : 'Atanan rol'}</p>
                <p className="adop-g13__kpi-value">{role.replaceAll('_', ' ')}</p>
              </div>
              <div className="adop-g13__kpi">
                <p className="adop-g13__kpi-label">{locale === 'en' ? 'Department' : 'Departman'}</p>
                <p className="adop-g13__kpi-value">{user?.department ?? '—'}</p>
              </div>
              <div className="adop-g13__kpi">
                <p className="adop-g13__kpi-label">{locale === 'en' ? 'Language' : 'Dil'}</p>
                <p className="adop-g13__kpi-value">{locale.toUpperCase()}</p>
              </div>
              <div className="adop-g13__kpi">
                <p className="adop-g13__kpi-label">{locale === 'en' ? 'Timezone' : 'Saat dilimi'}</p>
                <p className="adop-g13__kpi-value">{user?.timezone ?? 'Europe/Istanbul'}</p>
              </div>
            </div>
            <p className="adop-g13__muted" style={{ marginTop: '0.75rem' }}>
              {locale === 'en'
                ? 'Permissions come from admin-assigned roles. You cannot configure permissions yourself.'
                : 'İzinler yönetici tarafından atanan rollerden gelir. İzinleri kendiniz yapılandıramazsınız.'}
            </p>
            <ul className="adop-g13__list" style={{ marginTop: '0.75rem' }}>
              <li className="adop-g13__list-item">
                <span>{locale === 'en' ? 'Available roles mapped' : 'Eşlenen roller'}</span>
                <span className="adop-g13__pill">{roles.join(', ')}</span>
              </li>
              <li className="adop-g13__list-item">
                <span>{locale === 'en' ? 'Restricted workspaces' : 'Kısıtlı alanlar'}</span>
                <span className="adop-g13__pill adop-g13__pill--warn">
                  {locale === 'en' ? 'Hidden by RBAC' : 'RBAC ile gizli'}
                </span>
              </li>
              <li className="adop-g13__list-item">
                <span>{locale === 'en' ? 'Estimated time' : 'Tahmini süre'}</span>
                <span className="adop-g13__pill adop-g13__pill--info">
                  {path ? `${path.modules.reduce((a, m) => a + m.estimatedMinutes, 0)} min` : '45 min'}
                </span>
              </li>
            </ul>
          </section>

          <section className="adop-g13__panel adop-g13__panel--6" data-testid="adop-welcome-flow">
            <h2 className="adop-g13__panel-title">
              {locale === 'en' ? 'First-login flow' : 'İlk giriş akışı'}
            </h2>
            <div className="adop-g13__progress" aria-hidden>
              <span style={{ width: `${((stepIdx + 1) / STEPS.length) * 100}%` }} />
            </div>
            <p className="adop-g13__muted" style={{ margin: '0.55rem 0' }}>
              {locale === 'en' ? 'Step' : 'Adım'} {stepIdx + 1}/{STEPS.length}:{' '}
              <strong>{locale === 'en' ? current.en : current.tr}</strong>
            </p>
            <div className="adop-g13__steps">
              {STEPS.map((s) => (
                <div
                  key={s.id}
                  className="adop-g13__step"
                  data-complete={state.onboarding.completedSteps.includes(s.id) ? 'true' : 'false'}
                >
                  <div>
                    <strong>{locale === 'en' ? s.en : s.tr}</strong>
                    {state.onboarding.completedSteps.includes(s.id) ? (
                      <span className="adop-g13__pill adop-g13__pill--ok" style={{ marginLeft: 8 }}>
                        {locale === 'en' ? 'Done' : 'Tamam'}
                      </span>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
            <div className="adop-g13__top-actions" style={{ marginTop: '0.85rem' }}>
              <button
                type="button"
                className="adop-g13__btn"
                disabled={stepIdx === 0}
                onClick={() => setStepIdx((v) => Math.max(0, v - 1))}
              >
                {locale === 'en' ? 'Back' : 'Geri'}
              </button>
              <button
                type="button"
                className="adop-g13__btn adop-g13__btn--primary"
                data-testid="adop-onboarding-continue"
                onClick={() => {
                  mark(current.id);
                  if (current.id === 'tour') startTour(recommendedTour.id);
                  if (stepIdx < STEPS.length - 1) setStepIdx((v) => v + 1);
                }}
              >
                {locale === 'en' ? 'Continue' : 'Devam'}
              </button>
            </div>
          </section>

          <section className="adop-g13__panel adop-g13__panel--8">
            <h2 className="adop-g13__panel-title">
              {locale === 'en' ? 'Recommended learning path' : 'Önerilen öğrenme yolu'}
            </h2>
            {path ? (
              <>
                <p className="adop-g13__muted">{lt(locale, path.description)}</p>
                <ul className="adop-g13__list" style={{ marginTop: '0.65rem' }}>
                  {path.modules.map((m) => (
                    <li key={m.id} className="adop-g13__list-item">
                      <span>
                        {lt(locale, m.title)}
                        {m.mandatory ? (
                          <span className="adop-g13__pill adop-g13__pill--warn" style={{ marginLeft: 8 }}>
                            {locale === 'en' ? 'Mandatory' : 'Zorunlu'}
                          </span>
                        ) : (
                          <span className="adop-g13__pill" style={{ marginLeft: 8 }}>
                            {locale === 'en' ? 'Optional' : 'Opsiyonel'}
                          </span>
                        )}
                      </span>
                      <span className="adop-g13__muted">{m.estimatedMinutes} min</span>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="adop-g13__muted">{locale === 'en' ? 'No path mapped' : 'Yol eşlenmedi'}</p>
            )}
          </section>

          <section className="adop-g13__panel adop-g13__panel--4">
            <h2 className="adop-g13__panel-title">
              {locale === 'en' ? 'First recommended action' : 'İlk önerilen aksiyon'}
            </h2>
            <p className="adop-g13__muted">{lt(locale, recommendedTour.description)}</p>
            <button
              type="button"
              className="adop-g13__btn adop-g13__btn--primary"
              style={{ marginTop: '0.75rem' }}
              data-testid="adop-start-tour"
              onClick={() => {
                mark('tour');
                startTour(recommendedTour.id);
              }}
            >
              {locale === 'en' ? 'Start tour' : 'Turu başlat'}
            </button>
            <Link
              href={'/dashboard/training?view=daily' as Route}
              className="adop-g13__btn"
              style={{ marginTop: '0.45rem', display: 'inline-block' }}
            >
              {locale === 'en' ? 'Open daily checklist' : 'Günlük listeyi aç'}
            </Link>
          </section>
        </div>
      </div>
    </main>
  );
}
