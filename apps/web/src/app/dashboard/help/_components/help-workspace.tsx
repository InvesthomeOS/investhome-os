'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale } from 'next-intl';
import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import {
  CONTEXTUAL_GUIDANCE,
  HELP_ARTICLES,
  PRODUCT_TOURS,
  WORKFLOW_TUTORIALS,
} from '@/lib/adoption/content';
import { lt } from '@/lib/adoption/locale';
import {
  canViewAdminOnlyHelp,
  filterHelpForUser,
  resolveAdoptionRoles,
} from '@/lib/adoption/permissions';
import { updateAdoptionState } from '@/lib/adoption/progress-store';
import type { FeedbackType, SupportCategory } from '@/lib/adoption/types';
import { canViewAiWorkspace } from '@/lib/ai/ai-permissions';
import { useAuth } from '@/lib/auth/auth-context';
import { useAdoptionTour } from '@/components/adoption/tour-provider';

const FEEDBACK_TYPES: FeedbackType[] = [
  'helpful',
  'not_helpful',
  'confusing',
  'missing_information',
  'broken_tour',
  'outdated_content',
  'feature_request',
  'bug_report',
];

const SUPPORT_CATS: SupportCategory[] = [
  'access',
  'data',
  'crm',
  'investor',
  'project',
  'finance',
  'marketing',
  'ai',
  'document',
  'portal',
  'bug',
  'training',
  'security',
  'other',
];

export function HelpWorkspace() {
  const locale = useLocale();
  const { user } = useAuth();
  const { userId, refreshState, state } = useAdoptionTour();
  const search = useSearchParams();
  const initialQ = search.get('q') ?? '';
  const view = search.get('view') ?? 'search';
  const [q, setQ] = useState(initialQ);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [supportOpen, setSupportOpen] = useState(view === 'support');
  const [supportCat, setSupportCat] = useState<SupportCategory>('training');
  const [supportIssue, setSupportIssue] = useState('');
  const [feedbackType, setFeedbackType] = useState<FeedbackType>('helpful');
  const [feedbackComment, setFeedbackComment] = useState('');
  const aiAvailable = canViewAiWorkspace(user);
  const roles = resolveAdoptionRoles(user);

  const articles = useMemo(
    () => filterHelpForUser(HELP_ARTICLES, user, roles),
    [roles, user],
  );

  const results = useMemo(() => {
    const query = q.trim().toLowerCase();
    const base = [
      ...articles.map((a) => ({
        id: a.id,
        title: lt(locale, a.title),
        type: a.contentType,
        role: a.adminOnly ? 'admin' : a.roles[0],
        workspace: a.workspaces[0],
        updated: a.lastUpdated,
        href: `/dashboard/help?article=${a.id}` as Route,
        body: lt(locale, a.body),
      })),
      ...WORKFLOW_TUTORIALS.filter((t) => !t.responsibleRole || roles.includes(t.responsibleRole) || canViewAdminOnlyHelp(user)).map(
        (t) => ({
          id: t.id,
          title: lt(locale, t.title),
          type: 'tutorial',
          role: t.responsibleRole,
          workspace: 'training',
          updated: '2026-07-20',
          href: `/dashboard/training?view=tutorials&id=${t.id}` as Route,
          body: lt(locale, t.purpose),
        }),
      ),
      ...PRODUCT_TOURS.filter((t) => !t.adminOnly || canViewAdminOnlyHelp(user)).map((t) => ({
        id: t.id,
        title: lt(locale, t.title),
        type: 'tour',
        role: t.roles[0],
        workspace: 'onboarding',
        updated: '2026-07-20',
        href: `/dashboard/onboarding` as Route,
        body: lt(locale, t.description),
      })),
    ];
    if (!query) return base;
    return base.filter(
      (r) =>
        r.title.toLowerCase().includes(query) ||
        r.body.toLowerCase().includes(query) ||
        r.type.toLowerCase().includes(query),
    );
  }, [articles, locale, q, roles, user]);

  const selected = articles.find((a) => a.id === (selectedId ?? search.get('article')));

  const submitFeedback = () => {
    updateAdoptionState(userId, (prev) => ({
      ...prev,
      feedback: [
        ...prev.feedback,
        {
          type: feedbackType,
          comment: feedbackComment,
          route: '/dashboard/help',
          content: selected?.id ?? 'search',
          createdAt: new Date().toISOString(),
          status: 'new',
        },
      ],
    }));
    setFeedbackComment('');
    refreshState();
  };

  const submitSupport = () => {
    updateAdoptionState(userId, (prev) => ({
      ...prev,
      support: [
        ...prev.support,
        {
          category: supportCat,
          issue: supportIssue,
          severity: supportCat === 'security' ? 'critical' : 'medium',
          route: typeof window !== 'undefined' ? window.location.pathname : '/dashboard/help',
          role: roles[0] ?? 'operations',
          browser: typeof navigator !== 'undefined' ? navigator.userAgent.slice(0, 80) : 'n/a',
          release: 'g13',
          status: supportCat === 'security' ? 'triaged' : 'new',
          createdAt: new Date().toISOString(),
        },
      ],
    }));
    setSupportIssue('');
    refreshState();
  };

  return (
    <main className="adop-g13" data-testid="adop-help" data-tour="help-root">
      <header className="adop-g13__top">
        <div>
          <p className="adop-g13__eyebrow">G13 · {locale === 'en' ? 'Help Center' : 'Yardım Merkezi'}</p>
          <h1 className="adop-g13__title">
            {locale === 'en' ? 'Searchable help' : 'Aranabilir yardım'}
          </h1>
          <p className="adop-g13__subtitle">
            {locale === 'en'
              ? 'Articles, tours, tutorials, FAQs — filtered by your permissions.'
              : 'Makaleler, turlar, eğitimler, SSS — izinlerinize göre filtrelenir.'}
          </p>
        </div>
        <div className="adop-g13__top-actions">
          <button
            type="button"
            className="adop-g13__btn"
            data-testid="adop-open-support"
            onClick={() => setSupportOpen(true)}
          >
            {locale === 'en' ? 'Support request' : 'Destek talebi'}
          </button>
          <Link href={'/dashboard/training' as Route} className="adop-g13__btn adop-g13__btn--primary">
            {locale === 'en' ? 'Training' : 'Eğitim'}
          </Link>
        </div>
      </header>

      <div className="adop-g13__body">
        <div className="adop-g13__grid">
          <section className="adop-g13__panel adop-g13__panel--8" data-testid="adop-help-search">
            <h2 className="adop-g13__panel-title">{locale === 'en' ? 'Search' : 'Ara'}</h2>
            <div className="adop-g13__search">
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={
                  locale === 'en'
                    ? 'How do I create a reservation?'
                    : 'Rezervasyon nasıl oluştururum?'
                }
                aria-label={locale === 'en' ? 'Help search' : 'Yardım araması'}
                data-testid="adop-help-query"
              />
              <button type="button" className="adop-g13__btn adop-g13__btn--primary">
                {locale === 'en' ? 'Search' : 'Ara'}
              </button>
            </div>
            <div
              className="adop-g13__banner"
              style={{ marginTop: '0.75rem' }}
              data-testid="adop-ai-help-status"
            >
              {aiAvailable
                ? locale === 'en'
                  ? 'AI Help available via AI Workspace for natural-language questions.'
                  : 'Doğal dil soruları için YZ Yardımı AI Workspace üzerinden kullanılabilir.'
                : locale === 'en'
                  ? 'AI Help unavailable for your role — use catalog search.'
                  : 'Rolünüz için YZ Yardımı kullanılamıyor — katalog aramasını kullanın.'}
            </div>
            <ul className="adop-g13__list" style={{ marginTop: '0.75rem' }}>
              {results.map((r) => (
                <li key={r.id} className="adop-g13__list-item">
                  <div>
                    <strong>{r.title}</strong>
                    <p className="adop-g13__muted">
                      {r.type} · {r.workspace} · {r.updated}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="adop-g13__btn"
                    onClick={() => {
                      if (r.id.startsWith('help-')) setSelectedId(r.id);
                    }}
                  >
                    {locale === 'en' ? 'Open' : 'Aç'}
                  </button>
                </li>
              ))}
              {results.length === 0 ? (
                <li className="adop-g13__list-item">
                  <span className="adop-g13__muted">
                    {locale === 'en' ? 'No results — logged as unresolved search.' : 'Sonuç yok — çözülmemiş arama olarak kaydedildi.'}
                  </span>
                </li>
              ) : null}
            </ul>
          </section>

          <section className="adop-g13__panel adop-g13__panel--4">
            <h2 className="adop-g13__panel-title">
              {locale === 'en' ? 'Contextual guidance' : 'Bağlamsal rehberlik'}
            </h2>
            <ul className="adop-g13__list">
              {CONTEXTUAL_GUIDANCE.map((g) => (
                <li key={g.id} className="adop-g13__list-item" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                  <strong>{lt(locale, g.title)}</strong>
                  <p className="adop-g13__muted">{g.routePattern}</p>
                  <ul style={{ margin: '0.35rem 0 0', paddingLeft: '1rem', fontSize: '0.75rem' }}>
                    {g.tips.map((tip, i) => (
                      <li key={i}>{lt(locale, tip)}</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </section>

          {selected ? (
            <section className="adop-g13__panel" data-testid="adop-help-article">
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
                <h2 className="adop-g13__panel-title">{lt(locale, selected.title)}</h2>
                <span className="adop-g13__pill">{selected.version}</span>
              </div>
              <p>{lt(locale, selected.body)}</p>
              <div className="adop-g13__form-grid" style={{ marginTop: '0.85rem' }}>
                <label className="adop-g13__label">
                  {locale === 'en' ? 'Feedback' : 'Geri bildirim'}
                  <select
                    className="adop-g13__field"
                    value={feedbackType}
                    onChange={(e) => setFeedbackType(e.target.value as FeedbackType)}
                  >
                    {FEEDBACK_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="adop-g13__label">
                  {locale === 'en' ? 'Comment' : 'Yorum'}
                  <input
                    className="adop-g13__field"
                    value={feedbackComment}
                    onChange={(e) => setFeedbackComment(e.target.value)}
                  />
                </label>
              </div>
              <button
                type="button"
                className="adop-g13__btn adop-g13__btn--primary"
                style={{ marginTop: '0.55rem' }}
                data-testid="adop-submit-feedback"
                onClick={submitFeedback}
              >
                {locale === 'en' ? 'Submit feedback' : 'Geri bildirim gönder'}
              </button>
              <p className="adop-g13__muted" style={{ marginTop: '0.45rem' }}>
                {locale === 'en' ? 'Feedback logged:' : 'Kayıtlı geri bildirim:'} {state.feedback.length}
              </p>
            </section>
          ) : null}

          {supportOpen ? (
            <section className="adop-g13__panel" data-testid="adop-support-form">
              <h2 className="adop-g13__panel-title">
                {locale === 'en' ? 'Support & escalation' : 'Destek ve yükseltme'}
              </h2>
              <div className="adop-g13__form-grid">
                <label className="adop-g13__label">
                  {locale === 'en' ? 'Category' : 'Kategori'}
                  <select
                    className="adop-g13__field"
                    value={supportCat}
                    onChange={(e) => setSupportCat(e.target.value as SupportCategory)}
                  >
                    {SUPPORT_CATS.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="adop-g13__label">
                  {locale === 'en' ? 'Issue' : 'Sorun'}
                  <input
                    className="adop-g13__field"
                    value={supportIssue}
                    onChange={(e) => setSupportIssue(e.target.value)}
                    data-testid="adop-support-issue"
                  />
                </label>
              </div>
              {supportCat === 'security' ? (
                <div className="adop-g13__banner" style={{ marginTop: '0.65rem' }}>
                  {locale === 'en'
                    ? 'Security requests escalate immediately to the security process.'
                    : 'Güvenlik talepleri derhal güvenlik sürecine yükseltilir.'}
                </div>
              ) : null}
              <button
                type="button"
                className="adop-g13__btn adop-g13__btn--primary"
                style={{ marginTop: '0.65rem' }}
                data-testid="adop-submit-support"
                onClick={submitSupport}
              >
                {locale === 'en' ? 'Create support request' : 'Destek talebi oluştur'}
              </button>
              <p className="adop-g13__muted" style={{ marginTop: '0.45rem' }}>
                {locale === 'en' ? 'Open requests:' : 'Açık talepler:'} {state.support.length}
              </p>
            </section>
          ) : null}
        </div>
      </div>
    </main>
  );
}
