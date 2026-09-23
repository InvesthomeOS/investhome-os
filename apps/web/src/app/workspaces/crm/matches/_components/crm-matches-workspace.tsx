'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, SegmentedControl, Select } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import type {
  MatchAiActionKey,
  MatchCard,
  MatchViewMode,
  MatchWorkspacePreview,
} from '../matches-model';

const AI_ACTIONS: ReadonlyArray<{ key: MatchAiActionKey; icon: IhIconName }> = [
  { key: 'best', icon: 'sparkles' },
  { key: 'roi', icon: 'trendingUp' },
  { key: 'rent', icon: 'finance' },
  { key: 'safest', icon: 'admin' },
  { key: 'newProjects', icon: 'projects' },
];

type FilterKey =
  | 'city'
  | 'project'
  | 'price'
  | 'roi'
  | 'capRate'
  | 'delivery'
  | 'rooms'
  | 'status';

function ProjectScene({ scene }: { scene: MatchCard['scene'] }) {
  return (
    <span className={`crm-matches__scene is-${scene}`} aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
    </span>
  );
}

function MatchScoreBadge({ score, label }: { score: number; label: string }) {
  return (
    <span className="crm-matches__score" aria-label={`${label} ${score}%`}>
      <strong>{score}%</strong>
      <small>{label}</small>
    </span>
  );
}

const WHY_PREVIEW_COUNT = 3;

function MatchProjectCard({
  match,
  compared,
  onToggleCompare,
  detailHref,
}: {
  match: MatchCard;
  compared: boolean;
  onToggleCompare: () => void;
  detailHref: string;
}) {
  const t = useTranslations('crm.matches');
  const [whyExpanded, setWhyExpanded] = useState(false);
  const hiddenWhyCount = Math.max(0, match.whyKeys.length - WHY_PREVIEW_COUNT);
  const visibleWhyKeys = whyExpanded
    ? match.whyKeys
    : match.whyKeys.slice(0, WHY_PREVIEW_COUNT);

  return (
    <article className="crm-matches__card" data-testid={`match-card-${match.id}`}>
      <div className="crm-matches__card-media">
        <ProjectScene scene={match.scene} />
        <MatchScoreBadge score={match.matchScore} label={t('scoreLabel')} />
        <button
          type="button"
          className={`crm-matches__favorite${match.favorite ? ' is-active' : ''}`}
          aria-label={t('favorite')}
          aria-pressed={Boolean(match.favorite)}
        >
          <IhIcon name="target" size={14} />
        </button>
      </div>

      <div className="crm-matches__card-body">
        <header className="crm-matches__card-identity">
          <h3>{match.projectName}</h3>
          <p>
            <IhIcon name="projects" size={12} />
            <span>{match.location}</span>
          </p>
          <p className="crm-matches__developer">{match.developer}</p>
        </header>

        <div className="crm-matches__price-row">
          <strong>{match.price}</strong>
          <span>{match.unitType}</span>
          <span>{match.area}</span>
        </div>

        <dl className="crm-matches__metrics">
          <div>
            <dt>{t('metrics.roi')}</dt>
            <dd>{match.roi}</dd>
          </div>
          <div>
            <dt>{t('metrics.monthlyRent')}</dt>
            <dd>{match.monthlyRent}</dd>
          </div>
          <div>
            <dt>{t('metrics.cashFlow')}</dt>
            <dd>{match.monthlyCashFlow}</dd>
          </div>
          <div>
            <dt>{t('metrics.delivery')}</dt>
            <dd>{match.deliveryDate}</dd>
          </div>
        </dl>

        <p className="crm-matches__status">
          {t('statusLabel')}: <strong>{t(`status.${match.status}`)}</strong>
        </p>

        <section className="crm-matches__why" aria-label={t('whyTitle')}>
          <h4>{t('whyTitle')}</h4>
          <ul>
            {visibleWhyKeys.map((key) => (
              <li key={key}>
                <IhIcon name="check" size={12} />
                <span>{t(`why.${key}`)}</span>
              </li>
            ))}
          </ul>
          {hiddenWhyCount > 0 ? (
            <button
              type="button"
              className="crm-matches__why-more"
              aria-expanded={whyExpanded}
              onClick={() => setWhyExpanded((open) => !open)}
            >
              <span>{whyExpanded ? t('whyShowLess') : t('whyMore', { count: hiddenWhyCount })}</span>
              <IhIcon name="chevronDown" size={12} />
            </button>
          ) : null}
        </section>

        <footer className="crm-matches__card-actions">
          <Link href={detailHref as Route} className="ih-btn ih-btn--secondary ih-btn--sm">
            {t('viewDetails')}
          </Link>
          <Button
            variant="secondary"
            size="sm"
            className={compared ? 'is-pressed' : undefined}
            onClick={onToggleCompare}
            aria-pressed={compared}
          >
            {compared ? t('inComparison') : t('addToCompare')}
          </Button>
        </footer>
      </div>
    </article>
  );
}

export function CrmMatchesWorkspace({
  preview,
  onOpenAi,
  detailBasePath = '/workspaces/crm/matches',
}: {
  preview: MatchWorkspacePreview;
  /** Opens Dashboard Freeze AI drawer when provided by the shell. */
  onOpenAi?: (prompt?: string) => void;
  detailBasePath?: string;
}) {
  const t = useTranslations('crm.matches');
  const router = useRouter();
  const [view, setView] = useState<MatchViewMode>('card');
  const [aiAction, setAiAction] = useState<MatchAiActionKey>('best');
  const [filters, setFilters] = useState<Record<FilterKey, string>>({
    city: '',
    project: '',
    price: '',
    roi: '',
    capRate: '',
    delivery: '',
    rooms: '',
    status: '',
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);
  const [compareIds, setCompareIds] = useState<string[]>([]);

  const customer = preview.customer;
  const recommendation = preview.matches.find((m) => m.id === preview.recommendationId);
  const newAnalysisHref = recommendation
    ? `${detailBasePath}/${recommendation.id}`
    : detailBasePath;

  const sortedMatches = useMemo(() => {
    const items = [...preview.matches];
    if (aiAction === 'roi') {
      return items.sort((a, b) => parseFloat(b.roi.replace('%', '')) - parseFloat(a.roi.replace('%', '')));
    }
    if (aiAction === 'rent') {
      return items.sort(
        (a, b) =>
          Number(b.monthlyRent.replace(/[^\d.]/g, '')) - Number(a.monthlyRent.replace(/[^\d.]/g, '')),
      );
    }
    if (aiAction === 'safest') {
      return items.sort((a, b) => a.matchScore - b.matchScore).reverse();
    }
    if (aiAction === 'newProjects') {
      return items.sort((a, b) => a.deliveryDate.localeCompare(b.deliveryDate));
    }
    return items.sort((a, b) => b.matchScore - a.matchScore);
  }, [aiAction, preview.matches]);

  const filteredMatches = useMemo(() => {
    return sortedMatches.filter((match) => {
      if (filters.city && !match.location.toLowerCase().includes(filters.city.toLowerCase())) {
        return false;
      }
      if (filters.project && !match.projectName.toLowerCase().includes(filters.project.toLowerCase())) {
        return false;
      }
      if (filters.status && match.status !== filters.status) return false;
      if (filters.rooms && match.unitType !== filters.rooms) return false;
      return true;
    });
  }, [filters, sortedMatches]);

  const totalPages = Math.max(1, Math.ceil(preview.totalMatches / pageSize));
  const pageItems = filteredMatches.slice(0, pageSize);

  const clearFilters = () => {
    setFilters({
      city: '',
      project: '',
      price: '',
      roi: '',
      capRate: '',
      delivery: '',
      rooms: '',
      status: '',
    });
    setPage(1);
  };

  const toggleCompare = (id: string) => {
    setCompareIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  return (
    <div className="crm-matches" data-testid="crm-matches-workspace">
      <header className="crm-matches__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle', { count: preview.totalMatches })}</p>
        </div>
        <div className="crm-matches__header-actions">
          <SegmentedControl
            ariaLabel={t('viewAria')}
            value={view}
            onChange={setView}
            options={[
              { value: 'card', label: t('view.card') },
              { value: 'table', label: t('view.table') },
            ]}
          />
          <Button
            variant="primary"
            size="sm"
            className="crm-matches__create"
            onClick={() => {
              onOpenAi?.(t('ai.openPrompt'));
              router.push(newAnalysisHref as Route);
            }}
          >
            <IhIcon name="plus" size={14} />
            {t('newAnalysis')}
          </Button>
        </div>
      </header>

      <section className="crm-matches__customer" aria-label={t('customer.aria')}>
        <div className="crm-matches__customer-identity">
          <span
            className={`crm-matches__avatar is-${customer.photoTone}`}
            aria-hidden="true"
          >
            {customer.initials}
          </span>
          <div>
            <div className="crm-matches__customer-name">
              <h2>{customer.displayName}</h2>
              {customer.verified ? (
                <span className="crm-matches__verified">{t('customer.verified')}</span>
              ) : null}
            </div>
            <p>{customer.email}</p>
            <p>{customer.phone}</p>
            <Link href={customer.profileHref as Route} className="crm-matches__profile-link">
              {t('customer.viewProfile')}
              <IhIcon name="arrowRight" size={12} />
            </Link>
          </div>
        </div>

        <dl className="crm-matches__customer-grid">
          <div>
            <dt>{t('customer.budget')}</dt>
            <dd>{customer.budget}</dd>
          </div>
          <div>
            <dt>{t('customer.investmentGoal')}</dt>
            <dd>{t(`customer.goals.${customer.investmentGoalKey}`)}</dd>
          </div>
          <div>
            <dt>{t('customer.preferredAreas')}</dt>
            <dd>{customer.preferredAreas}</dd>
          </div>
          <div>
            <dt>{t('customer.riskProfile')}</dt>
            <dd>{t(`customer.risk.${customer.riskProfileKey}`)}</dd>
          </div>
          <div>
            <dt>{t('customer.investorType')}</dt>
            <dd>{t(`customer.investor.${customer.investorTypeKey}`)}</dd>
          </div>
          <div>
            <dt>{t('customer.preferredUnit')}</dt>
            <dd>{customer.preferredUnit}</dd>
          </div>
          <div>
            <dt>{t('customer.roiTarget')}</dt>
            <dd>{customer.roiTarget}</dd>
          </div>
          <div>
            <dt>{t('customer.language')}</dt>
            <dd>{t(`customer.languages.${customer.languageKey}`)}</dd>
          </div>
          <div>
            <dt>{t('customer.nationality')}</dt>
            <dd>{t(`customer.nationalities.${customer.nationalityKey}`)}</dd>
          </div>
          <div>
            <dt>{t('customer.investmentHorizon')}</dt>
            <dd>{t(`customer.horizons.${customer.investmentHorizonKey}`)}</dd>
          </div>
          <div>
            <dt>{t('customer.financing')}</dt>
            <dd>{t(`customer.financingOptions.${customer.financingKey}`)}</dd>
          </div>
        </dl>
      </section>

      <nav className="screenshot-dashboard__intro-ai crm-matches__ai" aria-label={t('ai.aria')}>
        {AI_ACTIONS.map((action) => (
          <button
            key={action.key}
            type="button"
            className={aiAction === action.key ? 'is-featured' : undefined}
            onClick={() => setAiAction(action.key)}
          >
            <IhIcon name={action.icon} size={14} />
            <span>{t(`ai.actions.${action.key}`)}</span>
          </button>
        ))}
        <button
          type="button"
          className="screenshot-dashboard__intro-ai-primary"
          onClick={() => onOpenAi?.(t('ai.openPrompt'))}
        >
          <IhIcon name="sparkles" size={13} />
          {t('ai.title')}
        </button>
      </nav>

      <section className="crm-matches__filters" aria-label={t('filters.aria')}>
        <Select
          label={t('filters.city')}
          value={filters.city}
          onChange={(e) => setFilters((prev) => ({ ...prev, city: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          <option value="Miami">Miami</option>
          <option value="Washington">Washington DC</option>
        </Select>
        <Select
          label={t('filters.project')}
          value={filters.project}
          onChange={(e) => setFilters((prev) => ({ ...prev, project: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.matches.map((m) => (
            <option key={m.id} value={m.projectName}>
              {m.projectName}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.price')}
          value={filters.price}
          onChange={(e) => setFilters((prev) => ({ ...prev, price: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          <option value="250-350">$250k – $350k</option>
          <option value="350-400">$350k – $400k</option>
        </Select>
        <Select
          label={t('filters.roi')}
          value={filters.roi}
          onChange={(e) => setFilters((prev) => ({ ...prev, roi: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          <option value="8+">%8+</option>
          <option value="10+">%10+</option>
        </Select>
        <Select
          label={t('filters.capRate')}
          value={filters.capRate}
          onChange={(e) => setFilters((prev) => ({ ...prev, capRate: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          <option value="5+">%5+</option>
          <option value="6+">%6+</option>
        </Select>
        <Select
          label={t('filters.delivery')}
          value={filters.delivery}
          onChange={(e) => setFilters((prev) => ({ ...prev, delivery: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          <option value="2026">2026</option>
          <option value="2027">2027</option>
        </Select>
        <Select
          label={t('filters.rooms')}
          value={filters.rooms}
          onChange={(e) => setFilters((prev) => ({ ...prev, rooms: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          <option value="1+1">1+1</option>
          <option value="2+1">2+1</option>
        </Select>
        <Select
          label={t('filters.status')}
          value={filters.status}
          onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          <option value="construction">{t('status.construction')}</option>
          <option value="ready">{t('status.ready')}</option>
          <option value="preSales">{t('status.preSales')}</option>
        </Select>
        <Button variant="secondary" size="sm" onClick={clearFilters}>
          {t('filters.clear')}
        </Button>
      </section>

      <div className="crm-matches__layout">
        <div className="crm-matches__main">
          {view === 'card' ? (
            <div className="crm-matches__grid" role="list">
              {pageItems.map((match) => (
                <div key={match.id} role="listitem">
                  <MatchProjectCard
                    match={match}
                    compared={compareIds.includes(match.id)}
                    onToggleCompare={() => toggleCompare(match.id)}
                    detailHref={`${detailBasePath}/${match.id}`}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="crm-matches__table-wrap" role="region" aria-label={t('view.table')}>
              <table className="crm-matches__table">
                <thead>
                  <tr>
                    <th>{t('table.project')}</th>
                    <th>{t('table.score')}</th>
                    <th>{t('table.price')}</th>
                    <th>{t('table.roi')}</th>
                    <th>{t('table.status')}</th>
                    <th>{t('table.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((match) => (
                    <tr key={match.id}>
                      <td>
                        <Link href={`${detailBasePath}/${match.id}` as Route}>
                          <strong>{match.projectName}</strong>
                          <span>{match.location}</span>
                        </Link>
                      </td>
                      <td>{match.matchScore}%</td>
                      <td>{match.price}</td>
                      <td>{match.roi}</td>
                      <td>{t(`status.${match.status}`)}</td>
                      <td>
                        <Link
                          href={`${detailBasePath}/${match.id}` as Route}
                          className="ih-btn ih-btn--secondary ih-btn--sm"
                        >
                          {t('viewDetails')}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <footer className="crm-matches__pagination" aria-label={t('pagination.aria')}>
            <p>{t('pagination.total', { count: preview.totalMatches })}</p>
            <div className="crm-matches__page-numbers" role="navigation">
              {Array.from({ length: Math.min(totalPages, 6) }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  type="button"
                  className={page === n ? 'is-active' : undefined}
                  onClick={() => setPage(n)}
                  aria-current={page === n ? 'page' : undefined}
                >
                  {n}
                </button>
              ))}
            </div>
            <label className="ih-field crm-matches__page-size">
              <span className="ih-field__label">{t('pagination.perPage')}</span>
              <select
                className="ih-select"
                value={String(pageSize)}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                aria-label={t('pagination.perPage')}
              >
                <option value="8">8 / {t('pagination.pageUnit')}</option>
                <option value="12">12 / {t('pagination.pageUnit')}</option>
                <option value="24">24 / {t('pagination.pageUnit')}</option>
              </select>
            </label>
          </footer>
        </div>

        <aside className="crm-matches__rail" aria-label={t('rail.aria')}>
          <section className="crm-matches__rail-card crm-matches__rail-card--ai">
            <h3>{t('rail.aiBest')}</h3>
            {recommendation ? (
              <>
                <div className="crm-matches__reco">
                  <div
                    className="crm-matches__reco-ring"
                    style={{ ['--score' as string]: recommendation.matchScore }}
                    aria-hidden="true"
                  >
                    <strong>{recommendation.matchScore}%</strong>
                  </div>
                  <div>
                    <h4>{recommendation.projectName}</h4>
                    <p>{recommendation.location}</p>
                    <p className="crm-matches__reco-price">{recommendation.price}</p>
                  </div>
                </div>
                <p className="crm-matches__reco-summary">
                  {t(`rail.summaries.${preview.recommendationSummaryKey}`)}
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => router.push(`${detailBasePath}/${recommendation.id}` as Route)}
                >
                  {t('viewDetails')}
                </Button>
              </>
            ) : null}
          </section>

          <section className="crm-matches__rail-card">
            <h3>{t('rail.customerSummary')}</h3>
            <dl>
              <div>
                <dt>{t('customer.budget')}</dt>
                <dd>{customer.budget}</dd>
              </div>
              <div>
                <dt>{t('customer.roiTarget')}</dt>
                <dd>{customer.roiTarget}</dd>
              </div>
              <div>
                <dt>{t('customer.investmentGoal')}</dt>
                <dd>{t(`customer.goals.${customer.investmentGoalKey}`)}</dd>
              </div>
              <div>
                <dt>{t('customer.riskProfile')}</dt>
                <dd>{t(`customer.risk.${customer.riskProfileKey}`)}</dd>
              </div>
              <div>
                <dt>{t('customer.preferredAreas')}</dt>
                <dd>{customer.preferredAreas}</dd>
              </div>
            </dl>
          </section>

          <section className="crm-matches__rail-card">
            <h3>{t('rail.riskAlerts')}</h3>
            <ul className="crm-matches__alerts">
              {preview.riskAlerts.map((alert) => (
                <li key={alert.id} className={`is-${alert.tone}`}>
                  <IhIcon name="alert" size={14} />
                  <div>
                    <strong>{t(`rail.alerts.${alert.titleKey}`)}</strong>
                    <p>{t(`rail.alerts.${alert.bodyKey}`)}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="crm-matches__rail-card">
            <h3>{t('rail.documents')}</h3>
            <ul className="crm-matches__docs">
              {preview.documents.map((doc) => (
                <li key={doc.id}>
                  <IhIcon name="documents" size={14} />
                  <div>
                    <strong>{t(`rail.docNames.${doc.nameKey}`)}</strong>
                    <span>{t(`rail.docMeta.${doc.metaKey}`)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="crm-matches__rail-card">
            <h3>{t('rail.recentActivity')}</h3>
            <ul className="crm-matches__activity">
              {preview.activities.map((item) => (
                <li key={item.id}>
                  <span aria-hidden="true" />
                  <div>
                    <strong>{t(`rail.activity.${item.titleKey}`)}</strong>
                    <time>{t(`rail.activity.${item.timeKey}`)}</time>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}
