'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale } from 'next-intl';
import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import { useAdoptionTour } from '@/components/adoption/tour-provider';
import {
  CERTIFICATIONS,
  CHECKLISTS,
  HELP_ARTICLES,
  KNOWLEDGE_CHECKS,
  LEARNING_PATHS,
  PRODUCT_TOURS,
  SIMULATIONS,
  WORKFLOW_TUTORIALS,
} from '@/lib/adoption/content';
import { lt } from '@/lib/adoption/locale';
import { primaryAdoptionRole } from '@/lib/adoption/permissions';
import { updateAdoptionState } from '@/lib/adoption/progress-store';
import { assertSimulationSafe, TRAINING_LABELS } from '@/lib/adoption/simulation';
import { useAuth } from '@/lib/auth/auth-context';

type View =
  | 'paths'
  | 'daily'
  | 'weekly'
  | 'monthly'
  | 'tutorials'
  | 'library'
  | 'simulation'
  | 'knowledge'
  | 'certs';

export function TrainingWorkspace() {
  const locale = useLocale();
  const { user } = useAuth();
  const { startTour, state, refreshState, userId } = useAdoptionTour();
  const search = useSearchParams();
  const initial = (search.get('view') as View) || 'paths';
  const [view, setView] = useState<View>(initial);
  const role = primaryAdoptionRole(user);
  const path = LEARNING_PATHS.find((p) => p.roleId === role) ?? LEARNING_PATHS[0]!;
  const [simMessage, setSimMessage] = useState<string | null>(null);
  const [kcAnswers, setKcAnswers] = useState<Record<string, number>>({});
  const [kcResult, setKcResult] = useState<string | null>(null);

  const daily =
    CHECKLISTS.find(
      (c) => c.cadence === 'daily' && (c.roleId === role || c.roleId === 'sales_rep' || c.roleId === 'ceo'),
    ) ??
    CHECKLISTS.find((c) => c.cadence === 'daily') ??
    CHECKLISTS[0]!;
  const weekly = CHECKLISTS.find((c) => c.cadence === 'weekly') ?? CHECKLISTS[0]!;
  const monthly = CHECKLISTS.find((c) => c.cadence === 'monthly') ?? CHECKLISTS[0]!;

  const checklistForView =
    view === 'weekly' ? weekly : view === 'monthly' ? monthly : daily;

  const checklistProgress = state.checklists[checklistForView.id]?.completedItemIds ?? [];

  const toggleItem = (itemId: string) => {
    updateAdoptionState(userId, (prev) => {
      const existing = prev.checklists[checklistForView.id]?.completedItemIds ?? [];
      const next = existing.includes(itemId)
        ? existing.filter((id) => id !== itemId)
        : [...existing, itemId];
      return {
        ...prev,
        checklists: {
          ...prev.checklists,
          [checklistForView.id]: {
            checklistId: checklistForView.id,
            completedItemIds: next,
            updatedAt: new Date().toISOString(),
          },
        },
      };
    });
    refreshState();
  };

  const simulationMode = state.simulationMode;

  const setSimulation = (on: boolean) => {
    updateAdoptionState(userId, (prev) => ({ ...prev, simulationMode: on }));
    refreshState();
    setSimMessage(null);
  };

  const tryBlocked = (action: Parameters<typeof assertSimulationSafe>[1]) => {
    const result = assertSimulationSafe(true, action);
    setSimMessage(result.reason ?? (locale === 'en' ? 'Allowed' : 'İzinli'));
  };

  const kc = useMemo(
    () => KNOWLEDGE_CHECKS.find((k) => k.roleId === role) ?? KNOWLEDGE_CHECKS[0]!,
    [role],
  );

  const submitKc = () => {
    let correct = 0;
    kc.questions.forEach((q) => {
      if (kcAnswers[q.id] === q.correctIndex) correct += 1;
    });
    const score = Math.round((correct / kc.questions.length) * 100);
    const passed = score >= kc.passScore;
    updateAdoptionState(userId, (prev) => ({
      ...prev,
      knowledge: {
        ...prev.knowledge,
        [kc.id]: {
          checkId: kc.id,
          score,
          passed,
          attempts: (prev.knowledge[kc.id]?.attempts ?? 0) + 1,
          updatedAt: new Date().toISOString(),
        },
      },
    }));
    refreshState();
    setKcResult(
      locale === 'en'
        ? `Score ${score}% — ${passed ? 'Passed' : 'Retry allowed'}`
        : `Skor ${score}% — ${passed ? 'Geçti' : 'Yeniden denenebilir'}`,
    );
  };

  const tabs: { id: View; en: string; tr: string }[] = [
    { id: 'paths', en: 'Learning path', tr: 'Öğrenme yolu' },
    { id: 'daily', en: 'Daily', tr: 'Günlük' },
    { id: 'weekly', en: 'Weekly', tr: 'Haftalık' },
    { id: 'monthly', en: 'Monthly', tr: 'Aylık' },
    { id: 'tutorials', en: 'Tutorials', tr: 'Eğitimler' },
    { id: 'library', en: 'Library', tr: 'Kütüphane' },
    { id: 'simulation', en: 'Simulation', tr: 'Simülasyon' },
    { id: 'knowledge', en: 'Knowledge check', tr: 'Bilgi kontrolü' },
    { id: 'certs', en: 'Certification', tr: 'Sertifika' },
  ];

  return (
    <main className="adop-g13" data-testid="adop-training" data-tour="training-root">
      <header className="adop-g13__top">
        <div>
          <p className="adop-g13__eyebrow">G13 · {locale === 'en' ? 'Training' : 'Eğitim'}</p>
          <h1 className="adop-g13__title">
            {locale === 'en' ? 'Training & operational excellence' : 'Eğitim ve operasyonel mükemmellik'}
          </h1>
          <p className="adop-g13__subtitle">
            {locale === 'en'
              ? 'Paths, checklists, tutorials, safe simulation, certifications.'
              : 'Yollar, listeler, eğitimler, güvenli simülasyon, sertifikalar.'}
          </p>
        </div>
        <div className="adop-g13__top-actions">
          {simulationMode ? (
            <span className="adop-g13__pill adop-g13__pill--info" data-testid="adop-training-mode-badge">
              TRAINING MODE
            </span>
          ) : null}
          <Link href={'/dashboard/help' as Route} className="adop-g13__btn">
            {locale === 'en' ? 'Help' : 'Yardım'}
          </Link>
        </div>
      </header>

      <div className="adop-g13__tabs" role="tablist" aria-label="Training views">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            className="adop-g13__tab"
            aria-selected={view === t.id}
            data-testid={`adop-tab-${t.id}`}
            onClick={() => setView(t.id)}
          >
            {locale === 'en' ? t.en : t.tr}
          </button>
        ))}
      </div>

      <div className="adop-g13__body">
        {view === 'paths' ? (
          <div className="adop-g13__grid">
            <section className="adop-g13__panel adop-g13__panel--8" data-testid="adop-learning-path">
              <h2 className="adop-g13__panel-title">{lt(locale, path.title)}</h2>
              <p className="adop-g13__muted">{lt(locale, path.description)}</p>
              <div className="adop-g13__kpi-row" style={{ marginTop: '0.75rem' }}>
                <div className="adop-g13__kpi">
                  <p className="adop-g13__kpi-label">{locale === 'en' ? 'Status' : 'Durum'}</p>
                  <p className="adop-g13__kpi-value">
                    {state.paths[path.id]?.status ?? 'not_started'}
                  </p>
                </div>
                <div className="adop-g13__kpi">
                  <p className="adop-g13__kpi-label">{locale === 'en' ? 'Deadline' : 'Son tarih'}</p>
                  <p className="adop-g13__kpi-value">{path.deadlineDays}d</p>
                </div>
                <div className="adop-g13__kpi">
                  <p className="adop-g13__kpi-label">{locale === 'en' ? 'Modules' : 'Modüller'}</p>
                  <p className="adop-g13__kpi-value">{path.modules.length}</p>
                </div>
              </div>
              <ul className="adop-g13__list" style={{ marginTop: '0.75rem' }}>
                {path.modules.map((m) => (
                  <li key={m.id} className="adop-g13__list-item">
                    <span>
                      {lt(locale, m.title)}
                      {m.mandatory ? (
                        <span className="adop-g13__pill adop-g13__pill--warn" style={{ marginLeft: 8 }}>
                          {locale === 'en' ? 'Mandatory' : 'Zorunlu'}
                        </span>
                      ) : null}
                    </span>
                    {m.tourId ? (
                      <button
                        type="button"
                        className="adop-g13__btn"
                        onClick={() => startTour(m.tourId!)}
                      >
                        {locale === 'en' ? 'Tour' : 'Tur'}
                      </button>
                    ) : (
                      <span className="adop-g13__muted">{m.estimatedMinutes} min</span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
            <section className="adop-g13__panel adop-g13__panel--4">
              <h2 className="adop-g13__panel-title">
                {locale === 'en' ? 'Practical tasks' : 'Pratik görevler'}
              </h2>
              <ul className="adop-g13__list">
                {path.practicalTasks.map((t, i) => (
                  <li key={i} className="adop-g13__list-item">
                    <span>{lt(locale, t)}</span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        ) : null}

        {view === 'daily' || view === 'weekly' || view === 'monthly' ? (
          <section
            className="adop-g13__panel"
            data-testid={`adop-checklist-${view}`}
          >
            <h2 className="adop-g13__panel-title">{lt(locale, checklistForView.title)}</h2>
            <p className="adop-g13__muted">
              {locale === 'en' ? 'Owner · due · evidence · escalation' : 'Sahip · vade · kanıt · yükseltme'}
            </p>
            {checklistForView.items.map((item) => {
              const done = checklistProgress.includes(item.id);
              return (
                <label key={item.id} className="adop-g13__check">
                  <input
                    type="checkbox"
                    checked={done}
                    onChange={() => toggleItem(item.id)}
                    data-testid={`adop-check-${item.id}`}
                  />
                  <div>
                    <strong>{lt(locale, item.title)}</strong>
                    <p className="adop-g13__muted">{lt(locale, item.description)}</p>
                    <p className="adop-g13__muted">
                      {item.relatedWorkspace} · {lt(locale, item.escalationRule)}
                    </p>
                  </div>
                </label>
              );
            })}
          </section>
        ) : null}

        {view === 'tutorials' ? (
          <section className="adop-g13__panel" data-testid="adop-tutorials">
            <h2 className="adop-g13__panel-title">
              {locale === 'en' ? 'Workflow tutorials (20)' : 'İş akışı eğitimleri (20)'}
            </h2>
            <table className="adop-g13__table">
              <thead>
                <tr>
                  <th>{locale === 'en' ? 'Tutorial' : 'Eğitim'}</th>
                  <th>{locale === 'en' ? 'Role' : 'Rol'}</th>
                  <th>{locale === 'en' ? 'Steps' : 'Adımlar'}</th>
                </tr>
              </thead>
              <tbody>
                {WORKFLOW_TUTORIALS.map((t) => (
                  <tr key={t.id} id={t.id}>
                    <td>
                      <strong>{lt(locale, t.title)}</strong>
                      <div className="adop-g13__muted">{lt(locale, t.purpose)}</div>
                    </td>
                    <td>{t.responsibleRole}</td>
                    <td>
                      <ol style={{ margin: 0, paddingLeft: '1rem' }}>
                        {t.steps.slice(0, 4).map((s, i) => (
                          <li key={i}>{lt(locale, s)}</li>
                        ))}
                      </ol>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ) : null}

        {view === 'library' ? (
          <section className="adop-g13__panel" data-testid="adop-library">
            <h2 className="adop-g13__panel-title">
              {locale === 'en' ? 'Training library' : 'Eğitim kütüphanesi'}
            </h2>
            <ul className="adop-g13__list">
              {[
                ...HELP_ARTICLES.map((a) => ({
                  id: a.id,
                  title: lt(locale, a.title),
                  category: a.category,
                  type: a.contentType,
                  status: a.status,
                  duration: a.durationMinutes ?? 5,
                })),
                ...PRODUCT_TOURS.map((t) => ({
                  id: t.id,
                  title: lt(locale, t.title),
                  category: 'Getting Started',
                  type: 'interactive tour',
                  status: t.status,
                  duration: t.estimatedMinutes,
                })),
              ].map((item) => (
                <li key={item.id} className="adop-g13__list-item">
                  <div>
                    <strong>{item.title}</strong>
                    <p className="adop-g13__muted">
                      {item.category} · {item.type} · {item.duration} min · v published
                    </p>
                  </div>
                  <span className="adop-g13__pill adop-g13__pill--ok">{item.status}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {view === 'simulation' ? (
          <section className="adop-g13__panel" data-testid="adop-simulation">
            <h2 className="adop-g13__panel-title">
              {locale === 'en' ? 'Guided task simulation' : 'Rehberli görev simülasyonu'}
            </h2>
            <div className="adop-g13__banner adop-g13__banner--training">
              <div>
                <strong>{TRAINING_LABELS.join(' · ')}</strong>
                <p className="adop-g13__muted" style={{ marginTop: 4 }}>
                  {locale === 'en'
                    ? 'Isolated training mode — no real emails, payments, campaigns, contracts, or automations.'
                    : 'İzole eğitim modu — gerçek e-posta, ödeme, kampanya, sözleşme veya otomasyon yok.'}
                </p>
              </div>
              <button
                type="button"
                className="adop-g13__btn adop-g13__btn--primary"
                data-testid="adop-toggle-simulation"
                onClick={() => setSimulation(!simulationMode)}
              >
                {simulationMode
                  ? locale === 'en'
                    ? 'Exit training mode'
                    : 'Eğitim modundan çık'
                  : locale === 'en'
                    ? 'Enter training mode'
                    : 'Eğitim moduna gir'}
              </button>
            </div>
            <ul className="adop-g13__list" style={{ marginTop: '0.75rem' }}>
              {SIMULATIONS.map((s) => (
                <li key={s.id} className="adop-g13__list-item" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                  <strong>{lt(locale, s.title)}</strong>
                  <p className="adop-g13__muted">{lt(locale, s.description)}</p>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {s.labels.map((l) => (
                      <span key={l} className="adop-g13__pill adop-g13__pill--info">
                        {l}
                      </span>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
            <div className="adop-g13__top-actions" style={{ marginTop: '0.75rem' }}>
              <button type="button" className="adop-g13__btn adop-g13__btn--danger" data-testid="adop-try-payment" onClick={() => tryBlocked('payment')}>
                {locale === 'en' ? 'Try real payment' : 'Gerçek ödeme dene'}
              </button>
              <button type="button" className="adop-g13__btn adop-g13__btn--danger" onClick={() => tryBlocked('email')}>
                {locale === 'en' ? 'Try real email' : 'Gerçek e-posta dene'}
              </button>
              <button type="button" className="adop-g13__btn adop-g13__btn--danger" onClick={() => tryBlocked('campaign_publish')}>
                {locale === 'en' ? 'Try campaign publish' : 'Kampanya yayını dene'}
              </button>
            </div>
            {simMessage ? (
              <div className="adop-g13__banner" style={{ marginTop: '0.65rem' }} data-testid="adop-sim-block-msg">
                {simMessage}
              </div>
            ) : null}
          </section>
        ) : null}

        {view === 'knowledge' ? (
          <section className="adop-g13__panel" data-testid="adop-knowledge-check">
            <h2 className="adop-g13__panel-title">{lt(locale, kc.title)}</h2>
            {kc.questions.map((q) => (
              <div key={q.id} style={{ marginBottom: '0.85rem' }}>
                <strong>{lt(locale, q.prompt)}</strong>
                <div style={{ display: 'grid', gap: 4, marginTop: 6 }}>
                  {q.options.map((opt, idx) => (
                    <label key={idx} className="adop-g13__check" style={{ border: 0, padding: '0.25rem 0' }}>
                      <input
                        type="radio"
                        name={q.id}
                        checked={kcAnswers[q.id] === idx}
                        onChange={() => setKcAnswers((prev) => ({ ...prev, [q.id]: idx }))}
                      />
                      <span>{lt(locale, opt)}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <button type="button" className="adop-g13__btn adop-g13__btn--primary" data-testid="adop-submit-kc" onClick={submitKc}>
              {locale === 'en' ? 'Submit' : 'Gönder'}
            </button>
            {kcResult ? <p className="adop-g13__muted" style={{ marginTop: 8 }}>{kcResult}</p> : null}
          </section>
        ) : null}

        {view === 'certs' ? (
          <section className="adop-g13__panel" data-testid="adop-certs">
            <h2 className="adop-g13__panel-title">
              {locale === 'en' ? 'Certification (competency tracking)' : 'Sertifika (yetkinlik takibi)'}
            </h2>
            <p className="adop-g13__muted">
              {locale === 'en'
                ? 'No decorative certificates — competency status only.'
                : 'Dekoratif sertifika yok — yalnızca yetkinlik durumu.'}
            </p>
            <ul className="adop-g13__list" style={{ marginTop: '0.65rem' }}>
              {CERTIFICATIONS.map((c) => (
                <li key={c.id} className="adop-g13__list-item">
                  <div>
                    <strong>{lt(locale, c.title)}</strong>
                    <p className="adop-g13__muted">
                      {c.roleIds.join(', ')} · renewal {c.renewalMonths ?? '—'} mo
                    </p>
                  </div>
                  <span className="adop-g13__pill">{locale === 'en' ? 'Not started' : 'Başlamadı'}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </main>
  );
}
