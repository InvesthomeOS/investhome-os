'use client';

import { useLocale } from 'next-intl';
import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import { ADOPTION_KPI_DEMO, CAPABILITY_AUDIT } from '@/lib/adoption/content';

function LineChart({ values, label }: { values: number[]; label: string }) {
  const max = Math.max(...values, 1);
  const points = values
    .map((v, i) => {
      const x = (i / Math.max(values.length - 1, 1)) * 100;
      const y = 100 - (v / max) * 90 - 5;
      return `${x},${y}`;
    })
    .join(' ');
  return (
    <svg className="adop-g13__line-chart" viewBox="0 0 100 100" role="img" aria-label={label} preserveAspectRatio="none">
      <polyline fill="none" stroke="#2f6f6c" strokeWidth="1.5" points={points} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function AdoptionDashboard() {
  const locale = useLocale();
  const search = useSearchParams();
  const [tab, setTab] = useState<'overview' | 'features'>(
    search.get('view') === 'features' ? 'features' : 'overview',
  );
  const k = ADOPTION_KPI_DEMO;

  const kpis = useMemo(
    () => [
      { en: 'Invited', tr: 'Davet', v: k.invitedUsers },
      { en: 'Activated', tr: 'Aktifleştirilen', v: k.activatedUsers },
      { en: 'Active', tr: 'Aktif', v: k.activeUsers },
      { en: 'Onboarding started', tr: 'Oryantasyon başladı', v: k.onboardingStarted },
      { en: 'Onboarding done', tr: 'Oryantasyon bitti', v: k.onboardingCompleted },
      { en: 'Overdue training', tr: 'Gecikmiş eğitim', v: k.overdueTraining },
      { en: 'Avg completion (d)', tr: 'Ort. tamamlanma (g)', v: k.avgCompletionDays },
      { en: 'DAU', tr: 'GAU', v: k.dau },
      { en: 'WAU', tr: 'HAU', v: k.wau },
      { en: 'Training rate', tr: 'Eğitim oranı', v: `${Math.round(k.trainingCompletionRate * 100)}%` },
      { en: 'Workflow success', tr: 'İş akışı başarı', v: `${Math.round(k.workflowSuccessRate * 100)}%` },
      { en: 'Help searches', tr: 'Yardım araması', v: k.helpSearches },
      { en: 'Unresolved searches', tr: 'Çözülmemiş arama', v: k.unresolvedHelpSearches },
      { en: 'Support requests', tr: 'Destek talebi', v: k.supportRequests },
      { en: 'Checklist completion', tr: 'Liste tamamlanma', v: `${Math.round(k.checklistCompletion * 100)}%` },
    ],
    [k],
  );

  return (
    <main className="adop-g13" data-testid="adop-adoption-dashboard" data-tour="adoption-dashboard">
      <header className="adop-g13__top">
        <div>
          <p className="adop-g13__eyebrow">G13 · Admin</p>
          <h1 className="adop-g13__title">
            {locale === 'en' ? 'Adoption dashboard' : 'Benimsenme paneli'}
          </h1>
          <p className="adop-g13__subtitle">
            {locale === 'en'
              ? 'Privacy-respecting product adoption — not employee surveillance.'
              : 'Gizliliğe saygılı ürün benimsenmesi — çalışan gözetimi değil.'}
          </p>
        </div>
      </header>

      <div className="adop-g13__tabs" role="tablist">
        <button type="button" role="tab" className="adop-g13__tab" aria-selected={tab === 'overview'} onClick={() => setTab('overview')}>
          {locale === 'en' ? 'Overview' : 'Genel'}
        </button>
        <button
          type="button"
          role="tab"
          className="adop-g13__tab"
          aria-selected={tab === 'features'}
          data-testid="adop-features-tab"
          onClick={() => setTab('features')}
        >
          {locale === 'en' ? 'Feature adoption' : 'Özellik benimsenmesi'}
        </button>
      </div>

      <div className="adop-g13__body">
        {tab === 'overview' ? (
          <>
            <section className="adop-g13__panel">
              <div className="adop-g13__kpi-row">
                {kpis.map((item) => (
                  <div key={item.en} className="adop-g13__kpi">
                    <p className="adop-g13__kpi-label">{locale === 'en' ? item.en : item.tr}</p>
                    <p className="adop-g13__kpi-value">{item.v}</p>
                  </div>
                ))}
              </div>
            </section>
            <div className="adop-g13__grid">
              <section className="adop-g13__panel adop-g13__panel--4">
                <h2 className="adop-g13__panel-title">{locale === 'en' ? 'Activation trend' : 'Aktivasyon trendi'}</h2>
                <LineChart values={k.activationTrend} label="activation" />
              </section>
              <section className="adop-g13__panel adop-g13__panel--4">
                <h2 className="adop-g13__panel-title">{locale === 'en' ? 'Training completion' : 'Eğitim tamamlanma'}</h2>
                <LineChart values={k.trainingTrend.map((v) => v * 100)} label="training" />
              </section>
              <section className="adop-g13__panel adop-g13__panel--4">
                <h2 className="adop-g13__panel-title">{locale === 'en' ? 'Active users' : 'Aktif kullanıcılar'}</h2>
                <LineChart values={k.activeTrend} label="active" />
              </section>
              <section className="adop-g13__panel adop-g13__panel--6">
                <h2 className="adop-g13__panel-title">{locale === 'en' ? 'Completion by role' : 'Role göre tamamlanma'}</h2>
                <div className="adop-g13__bar-chart">
                  {k.completionByRole.map((r) => (
                    <div key={r.role} className="adop-g13__bar-row">
                      <span>{r.role}</span>
                      <div className="adop-g13__bar-track">
                        <div className="adop-g13__bar-fill" style={{ width: `${r.pct * 100}%` }} />
                      </div>
                      <span>{Math.round(r.pct * 100)}%</span>
                    </div>
                  ))}
                </div>
              </section>
              <section className="adop-g13__panel adop-g13__panel--6">
                <h2 className="adop-g13__panel-title">{locale === 'en' ? 'Capability audit' : 'Yetenek denetimi'}</h2>
                <table className="adop-g13__table">
                  <thead>
                    <tr>
                      <th>{locale === 'en' ? 'Capability' : 'Yetenek'}</th>
                      <th>{locale === 'en' ? 'Status' : 'Durum'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {CAPABILITY_AUDIT.map((c) => (
                      <tr key={c.id}>
                        <td>{c.name}</td>
                        <td>
                          <span className="adop-g13__pill">{c.status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            </div>
          </>
        ) : (
          <section className="adop-g13__panel" data-testid="adop-feature-adoption">
            <h2 className="adop-g13__panel-title">
              {locale === 'en' ? 'Feature adoption' : 'Özellik benimsenmesi'}
            </h2>
            <div className="adop-g13__bar-chart">
              {k.featureAdoption.map((f) => (
                <div key={f.name} className="adop-g13__bar-row">
                  <span>{f.name}</span>
                  <div className="adop-g13__bar-track">
                    <div className="adop-g13__bar-fill" style={{ width: `${f.pct * 100}%` }} />
                  </div>
                  <span>{Math.round(f.pct * 100)}%</span>
                </div>
              ))}
            </div>
            <p className="adop-g13__muted" style={{ marginTop: '0.75rem' }}>
              {locale === 'en'
                ? 'Metrics: access · opened · actioned · adoption %. Aggregates only.'
                : 'Metrikler: erişim · açılma · aksiyon · benimsenme %. Yalnızca toplamlar.'}
            </p>
          </section>
        )}
      </div>
    </main>
  );
}
