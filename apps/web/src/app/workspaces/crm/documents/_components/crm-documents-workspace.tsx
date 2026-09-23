'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Input, KpiCard, SegmentedControl, Select, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import type {
  DocumentAiActionKey,
  DocumentCard,
  DocumentFileType,
  DocumentKpiKey,
  DocumentStatusKey,
  DocumentViewMode,
  DocumentWorkspacePreview,
} from '../documents-model';

const AI_ACTIONS: ReadonlyArray<{ key: DocumentAiActionKey; icon: IhIconName }> = [
  { key: 'summarize', icon: 'sparkles' },
  { key: 'missing', icon: 'alert' },
  { key: 'awaitingSignature', icon: 'documents' },
  { key: 'recent', icon: 'clock' },
];

const KPI_ICONS: Record<DocumentKpiKey, IhIconName> = {
  total: 'documents',
  awaitingSignature: 'clock',
  addedLast7Days: 'inbox',
  shared: 'activity',
};

const STATUS_TONE: Record<DocumentStatusKey, 'success' | 'warning' | 'info' | 'default' | 'danger'> = {
  signed: 'success',
  awaitingSignature: 'warning',
  shared: 'info',
  draft: 'default',
  rejected: 'danger',
};

const FILE_LABEL: Record<DocumentFileType, string> = {
  pdf: 'PDF',
  docx: 'DOCX',
  xlsx: 'XLSX',
};

type FilterKey = 'customer' | 'project' | 'type' | 'status' | 'date' | 'search';

function FileTypeIcon({ type }: { type: DocumentFileType }) {
  return (
    <span className={`crm-documents__file-icon is-${type}`} aria-hidden="true">
      <IhIcon name="documents" size={14} />
      <small>{FILE_LABEL[type]}</small>
    </span>
  );
}

function DocumentCardView({ doc, detailHref }: { doc: DocumentCard; detailHref: string }) {
  const t = useTranslations('crm.documents');

  return (
    <article className="crm-documents__card" data-testid={`document-card-${doc.id}`}>
      <header className="crm-documents__card-header">
        <FileTypeIcon type={doc.fileType} />
        <div className="crm-documents__card-identity">
          <h3 title={doc.name}>{doc.name}</h3>
          <p>
            <IhIcon name="user" size={12} />
            <span title={doc.owner}>{doc.owner}</span>
          </p>
          <p>
            <IhIcon name="projects" size={12} />
            <span title={doc.project}>{doc.project}</span>
          </p>
        </div>
        <StatusChip tone={STATUS_TONE[doc.status]} className="crm-documents__status">
          {t(`status.${doc.status}`)}
        </StatusChip>
      </header>

      <dl className="crm-documents__meta">
        <div>
          <dt>{t('meta.size')}</dt>
          <dd>{doc.size}</dd>
        </div>
        <div>
          <dt>{t('meta.version')}</dt>
          <dd>{doc.version}</dd>
        </div>
        <div>
          <dt>{t('meta.date')}</dt>
          <dd>{doc.date}</dd>
        </div>
      </dl>

      <footer className="crm-documents__card-actions">
        <Link href={detailHref as Route} className="ih-btn ih-btn--secondary ih-btn--sm">
          {t('viewDocument')}
        </Link>
        <Link href={detailHref as Route} className="ih-btn ih-btn--secondary ih-btn--sm">
          {t('share')}
        </Link>
      </footer>
    </article>
  );
}

function SignatureDonut({
  signed,
  awaiting,
  rejected,
  unitLabel,
}: {
  signed: number;
  awaiting: number;
  rejected: number;
  unitLabel: string;
}) {
  const total = Math.max(1, signed + awaiting + rejected);
  const signedPct = (signed / total) * 100;
  const awaitingPct = (awaiting / total) * 100;
  const rejectedPct = (rejected / total) * 100;

  return (
    <div
      className="crm-documents__donut"
      style={{
        background: `conic-gradient(
          #2f8a5b 0 ${signedPct}%,
          #d4a017 ${signedPct}% ${signedPct + awaitingPct}%,
          #c45c5c ${signedPct + awaitingPct}% ${signedPct + awaitingPct + rejectedPct}%
        )`,
      }}
      aria-hidden="true"
    >
      <span>
        <strong>{awaiting}</strong>
        <small>{unitLabel}</small>
      </span>
    </div>
  );
}

export function CrmDocumentsWorkspace({
  preview,
  onOpenAi,
  detailBasePath = '/workspaces/crm/documents',
}: {
  preview: DocumentWorkspacePreview;
  /** Opens Dashboard Freeze AI drawer when provided by the shell. */
  onOpenAi?: (prompt?: string) => void;
  detailBasePath?: string;
}) {
  const t = useTranslations('crm.documents');
  const [view, setView] = useState<DocumentViewMode>('card');
  const [aiAction, setAiAction] = useState<DocumentAiActionKey>('summarize');
  const [filters, setFilters] = useState<Record<FilterKey, string>>({
    customer: '',
    project: '',
    type: '',
    status: '',
    date: '',
    search: '',
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const filteredDocuments = useMemo(() => {
    let items = [...preview.documents];

    if (aiAction === 'awaitingSignature') {
      items = items.filter((d) => d.status === 'awaitingSignature');
    } else if (aiAction === 'recent') {
      items = [...items].sort((a, b) => b.date.localeCompare(a.date));
    } else if (aiAction === 'missing') {
      // Presentation-only highlight — keep full list, rail shows missing.
      items = items;
    }

    return items.filter((doc) => {
      if (filters.customer && doc.owner !== filters.customer) return false;
      if (filters.project && doc.project !== filters.project) return false;
      if (filters.type && doc.fileType !== filters.type) return false;
      if (filters.status && doc.status !== filters.status) return false;
      if (
        filters.search &&
        !doc.name.toLowerCase().includes(filters.search.trim().toLowerCase())
      ) {
        return false;
      }
      return true;
    });
  }, [aiAction, filters, preview.documents]);

  const totalPages = Math.max(1, Math.ceil(preview.totalDocuments / pageSize));
  const pageItems = filteredDocuments.slice(0, Math.min(pageSize, filteredDocuments.length));

  const clearFilters = () => {
    setFilters({
      customer: '',
      project: '',
      type: '',
      status: '',
      date: '',
      search: '',
    });
    setPage(1);
  };

  const signatureTotal =
    preview.signatureDistribution.signed +
    preview.signatureDistribution.awaiting +
    preview.signatureDistribution.rejected;

  return (
    <div className="crm-documents" data-testid="crm-documents-workspace">
      <header className="crm-documents__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-documents__header-actions">
          <SegmentedControl
            ariaLabel={t('viewAria')}
            value={view}
            onChange={setView}
            options={[
              { value: 'card', label: t('view.card') },
              { value: 'table', label: t('view.table') },
            ]}
          />
          <Link
            href={`${detailBasePath}/${preview.documents[0]?.id ?? ''}` as Route}
            className="ih-btn ih-btn--primary ih-btn--sm crm-documents__upload"
          >
            <IhIcon name="plus" size={14} />
            {t('uploadNew')}
          </Link>
        </div>
      </header>

      <section className="crm-documents__kpi-row" aria-label={t('kpis.aria')}>
        {preview.kpis.map((kpi) => (
          <KpiCard
            key={kpi.key}
            className="crm-documents__kpi"
            label={t(`kpis.${kpi.key}`)}
            value={kpi.value}
            hint={t(`kpis.hints.${kpi.hintKey}`, { count: kpi.value })}
            delta={`${kpi.delta} ${t('kpis.thisMonth')}`}
            deltaTone={kpi.deltaTone}
            tone={kpi.key === 'awaitingSignature' ? 'warning' : 'default'}
            icon={<IhIcon name={KPI_ICONS[kpi.key]} size={18} />}
          />
        ))}
      </section>

      <nav className="screenshot-dashboard__intro-ai crm-documents__ai" aria-label={t('ai.aria')}>
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

      <section className="crm-documents__filters" aria-label={t('filters.aria')}>
        <Select
          label={t('filters.customer')}
          value={filters.customer}
          onChange={(e) => setFilters((prev) => ({ ...prev, customer: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.customers.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.project')}
          value={filters.project}
          onChange={(e) => setFilters((prev) => ({ ...prev, project: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.projects.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.type')}
          value={filters.type}
          onChange={(e) => setFilters((prev) => ({ ...prev, type: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.documentTypes.map((type) => (
            <option key={type} value={type}>
              {FILE_LABEL[type]}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.status')}
          value={filters.status}
          onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          <option value="signed">{t('status.signed')}</option>
          <option value="awaitingSignature">{t('status.awaitingSignature')}</option>
          <option value="shared">{t('status.shared')}</option>
          <option value="draft">{t('status.draft')}</option>
          <option value="rejected">{t('status.rejected')}</option>
        </Select>
        <Select
          label={t('filters.date')}
          value={filters.date}
          onChange={(e) => setFilters((prev) => ({ ...prev, date: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          <option value="7d">{t('filters.dateRanges.last7')}</option>
          <option value="30d">{t('filters.dateRanges.last30')}</option>
          <option value="90d">{t('filters.dateRanges.last90')}</option>
        </Select>
        <Input
          label={t('filters.search')}
          value={filters.search}
          onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
          placeholder={t('filters.searchPlaceholder')}
        />
        <Button variant="secondary" size="sm" onClick={clearFilters}>
          <IhIcon name="refresh" size={13} />
          {t('filters.clear')}
        </Button>
      </section>

      <div className="crm-documents__layout">
        <div className="crm-documents__main">
          {view === 'card' ? (
            <div className="crm-documents__grid" role="list">
              {pageItems.map((doc) => (
                <div key={doc.id} role="listitem">
                  <DocumentCardView doc={doc} detailHref={`${detailBasePath}/${doc.id}`} />
                </div>
              ))}
            </div>
          ) : (
            <div className="crm-documents__table-wrap" role="region" aria-label={t('view.table')}>
              <table className="crm-documents__table">
                <thead>
                  <tr>
                    <th>{t('table.name')}</th>
                    <th>{t('table.owner')}</th>
                    <th>{t('table.project')}</th>
                    <th>{t('table.status')}</th>
                    <th>{t('table.size')}</th>
                    <th>{t('table.version')}</th>
                    <th>{t('table.date')}</th>
                    <th>{t('table.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((doc) => (
                    <tr key={doc.id}>
                      <td>
                        <Link href={`${detailBasePath}/${doc.id}` as Route}>
                          <strong title={doc.name}>{doc.name}</strong>
                          <span>{FILE_LABEL[doc.fileType]}</span>
                        </Link>
                      </td>
                      <td>{doc.owner}</td>
                      <td>{doc.project}</td>
                      <td>
                        <StatusChip tone={STATUS_TONE[doc.status]}>
                          {t(`status.${doc.status}`)}
                        </StatusChip>
                      </td>
                      <td>{doc.size}</td>
                      <td>{doc.version}</td>
                      <td>{doc.date}</td>
                      <td>
                        <Link
                          href={`${detailBasePath}/${doc.id}` as Route}
                          className="ih-btn ih-btn--secondary ih-btn--sm"
                        >
                          {t('viewDocument')}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <footer className="crm-documents__pagination" aria-label={t('pagination.aria')}>
            <p>{t('pagination.total', { count: preview.totalDocuments })}</p>
            <div className="crm-documents__page-numbers" role="navigation">
              {Array.from({ length: Math.min(totalPages, 3) }, (_, i) => i + 1).map((n) => (
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
              {totalPages > 4 ? <span className="crm-documents__page-ellipsis">…</span> : null}
              {totalPages > 3 ? (
                <button
                  type="button"
                  className={page === totalPages ? 'is-active' : undefined}
                  onClick={() => setPage(totalPages)}
                  aria-current={page === totalPages ? 'page' : undefined}
                >
                  {totalPages}
                </button>
              ) : null}
            </div>
            <label className="ih-field crm-documents__page-size">
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
                <option value="20">20 / {t('pagination.pageUnit')}</option>
                <option value="40">40 / {t('pagination.pageUnit')}</option>
              </select>
            </label>
          </footer>
        </div>

        <aside className="crm-documents__rail" aria-label={t('rail.aria')}>
          <section className="crm-documents__rail-card crm-documents__rail-card--ai">
            <h3>{t('rail.aiSummary')}</h3>
            <h4>{preview.aiSummary.title}</h4>
            <p className="crm-documents__ai-summary-body">
              {t(`rail.summaries.${preview.aiSummary.bodyKey}`)}
            </p>
            <dl className="crm-documents__ai-status">
              <div>
                <dt>{t('rail.signed')}</dt>
                <dd>{preview.signatureDistribution.signed}</dd>
              </div>
              <div>
                <dt>{t('rail.awaiting')}</dt>
                <dd className="is-warning">{preview.signatureDistribution.awaiting}</dd>
              </div>
              <div>
                <dt>{t('rail.rejected')}</dt>
                <dd>{preview.signatureDistribution.rejected}</dd>
              </div>
            </dl>
            {preview.missingCount > 0 ? (
              <p className="crm-documents__ai-missing-warn">
                <IhIcon name="alert" size={12} />
                <span>{t('rail.missingCount', { count: preview.missingCount })}</span>
              </p>
            ) : null}
            <p className="crm-documents__ai-updated">
              {t('rail.lastUpdated', { date: preview.aiSummary.lastUpdated })}
            </p>
            <Link
              href={`${detailBasePath}/${preview.documents[0]?.id ?? ''}` as Route}
              className="ih-btn ih-btn--secondary ih-btn--sm"
            >
              {t('rail.viewSummary')}
            </Link>
          </section>

          <section className="crm-documents__rail-card">
            <h3>{t('rail.signatureStatus')}</h3>
            <div className="crm-documents__signature">
              <SignatureDonut
                signed={preview.signatureDistribution.signed}
                awaiting={preview.signatureDistribution.awaiting}
                rejected={preview.signatureDistribution.rejected}
                unitLabel={t('rail.donutUnit')}
              />
              <ul className="crm-documents__legend">
                <li className="is-signed">
                  <span />
                  {t('rail.signed')} · {preview.signatureDistribution.signed}
                </li>
                <li className="is-awaiting">
                  <span />
                  {t('rail.awaiting')} · {preview.signatureDistribution.awaiting}
                </li>
                <li className="is-rejected">
                  <span />
                  {t('rail.rejected')} · {preview.signatureDistribution.rejected}
                </li>
              </ul>
            </div>
            <p className="crm-documents__signature-total">
              {t('rail.signatureTotal', { count: signatureTotal })}
            </p>
          </section>

          <section className="crm-documents__rail-card">
            <h3>{t('rail.recentlyOpened')}</h3>
            <ul className="crm-documents__recent">
              {preview.recentlyOpened.map((item) => (
                <li key={item.id}>
                  <FileTypeIcon type={item.fileType} />
                  <div>
                    <strong title={item.name}>{item.name}</strong>
                    <span>{t(`rail.openedAt.${item.openedAtKey}`)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="crm-documents__rail-card crm-documents__rail-card--warn">
            <h3>{t('rail.missing')}</h3>
            <div className="crm-documents__missing">
              <span className="crm-documents__missing-icon" aria-hidden="true">
                <IhIcon name="alert" size={14} />
              </span>
              <div>
                <strong>{t('rail.missingCount', { count: preview.missingCount })}</strong>
                <p>{t('rail.missingHint')}</p>
              </div>
            </div>
            <ul className="crm-documents__missing-list">
              {preview.missingItems.map((item) => (
                <li key={item.id}>{t(`rail.missingItems.${item.labelKey}`)}</li>
              ))}
            </ul>
          </section>

          <section className="crm-documents__rail-card">
            <h3>{t('rail.recentActivity')}</h3>
            <ul className="crm-documents__activity">
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
