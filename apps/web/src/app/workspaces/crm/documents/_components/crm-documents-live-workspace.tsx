'use client';

import { useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select, StatusChip } from '@investhome/ui';

import { documentDownloadUrl } from '@/lib/api/documents';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { PreviewBody } from '@/workspaces/crm/contact-card/document-gallery';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import type { CrmDocumentFeedItem } from '@/workspaces/crm/api/crm-documents';
import { crmDocumentQueries, hideCrmDocument } from '@/workspaces/crm/hooks/use-crm-documents';

const PAGE_SIZE = 25;

const PROJECTS = [
  { value: '1307_k_st', label: '1307 K St' },
  { value: '1313_penn', label: '1313 Penn' },
  { value: '1812_h_pl', label: '1812 H Pl' },
  { value: '2319_ontario', label: '2319 Ontario' },
  { value: 'reit', label: 'REIT' },
  { value: 'the_temple', label: 'The Temple' },
  { value: 'uniloft', label: 'Uniloft' },
] as const;

const CATEGORIES = [
  'passport',
  'reservation',
  'operating_agreement',
  'llc',
  'payment',
  'closing',
  'offer',
  'warranty',
  'correspondence',
  'other',
] as const;

const SOURCES = [
  { value: 'deal_uf', labelKey: 'sources.sale' },
  { value: 'activity', labelKey: 'sources.activity' },
  { value: 'comment', labelKey: 'sources.comment' },
  { value: 'manual_import_1812', labelKey: 'sources.import1812' },
  { value: 'manual_import', labelKey: 'sources.manual' },
] as const;

function dateRange(value: string): { date_from?: string; date_to?: string } {
  if (!value) return {};
  const now = new Date();
  const end = now.toISOString();
  if (value === 'today') {
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return { date_from: start.toISOString(), date_to: end };
  }
  const days = value === '7d' ? 7 : value === '30d' ? 30 : value === '90d' ? 90 : 0;
  if (!days) return {};
  return { date_from: new Date(now.getTime() - days * 86_400_000).toISOString(), date_to: end };
}

function formatWhen(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  return new Date(value).toLocaleString(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function formatSize(bytes: number, locale: string): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toLocaleString(locale, { maximumFractionDigits: 1 })} KB`;
  return `${(bytes / (1024 * 1024)).toLocaleString(locale, { maximumFractionDigits: 1 })} MB`;
}

function statusTone(status: string): 'default' | 'info' | 'warning' {
  if (status === 'inceleme') return 'warning';
  if (status === 'gizli') return 'default';
  return 'info';
}

export function CrmDocumentsLiveWorkspace() {
  const t = useTranslations('crm.documentHub');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const { authLoading, canRead, has } = useCrmAccess();
  const canUpdate = has('update');
  const { openContact } = useContactCard();
  const searchParams = useSearchParams();
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [personDraft, setPersonDraft] = useState('');
  const [person, setPerson] = useState('');
  const [unitDraft, setUnitDraft] = useState('');
  const [unit, setUnit] = useState('');
  const [projectGroup, setProjectGroup] = useState(searchParams.get('project') || '');
  const [category, setCategory] = useState('');
  const [source, setSource] = useState('');
  const [visibility, setVisibility] = useState(searchParams.get('visibility') || 'visible');
  const [scope, setScope] = useState(searchParams.get('scope') || '');
  const [date, setDate] = useState('');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<CrmDocumentFeedItem | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchDraft.trim());
      setPerson(personDraft.trim());
      setUnit(unitDraft.trim());
      setPage(1);
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft, personDraft, unitDraft]);

  const listParams = useMemo(
    () => ({
      search: search || undefined,
      person: person || undefined,
      project_group: projectGroup || undefined,
      unit: unit || undefined,
      category: category || undefined,
      source: source || undefined,
      visibility,
      scope: scope || undefined,
      page,
      page_size: PAGE_SIZE,
      ...dateRange(date),
    }),
    [search, person, projectGroup, unit, category, source, visibility, scope, date, page],
  );

  const feedQuery = useQuery({
    ...crmDocumentQueries.feed(listParams),
    enabled: !authLoading && canRead,
  });

  const hideMutation = useMutation({
    mutationFn: ({ id, hidden }: { id: string; hidden: boolean }) => hideCrmDocument(id, hidden),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['crm', 'documents', 'feed'] });
      setSelected((current) => (current && current.id === variables.id ? { ...current, hidden: variables.hidden } : current));
    },
  });

  const stats = feedQuery.data?.stats ?? { total: 0, person: 0, purchase: 0, hidden: 0, unresolved: 0 };
  const items = feedQuery.data?.items ?? [];
  const pages = feedQuery.data?.pages ?? 1;

  const clearFilters = () => {
    setSearchDraft('');
    setSearch('');
    setPersonDraft('');
    setPerson('');
    setUnitDraft('');
    setUnit('');
    setProjectGroup('');
    setCategory('');
    setSource('');
    setVisibility('visible');
    setScope('');
    setDate('');
    setPage(1);
  };

  const selectKpi = (nextScope: string, nextVisibility = 'visible') => {
    setScope(nextScope);
    setVisibility(nextVisibility);
    setPage(1);
  };

  if (authLoading || feedQuery.isLoading) {
    return (
      <div className="crm-tasks crm-tasks--ops crm-comm-live crm-docs-live" data-testid="crm-documents-live">
        <div className="crm-tasks__skeleton" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="crm-tasks__skeleton-row" />
          ))}
        </div>
      </div>
    );
  }

  if (!canRead) {
    return <ErrorState title={t('title')} message={tCommon('retry')} />;
  }

  return (
    <div className="crm-tasks crm-tasks--ops crm-comm-live crm-docs-live" data-testid="crm-documents-live">
      <header className="crm-tasks__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="crm-comm-live__kpi-row crm-docs-live__kpi-row" aria-label={t('kpis.aria')}>
        <button
          type="button"
          className={`crm-comm-live__kpi crm-comm-live__kpi--btn${!scope && visibility === 'visible' ? ' is-active' : ''}`}
          onClick={() => selectKpi('', 'visible')}
        >
          <span>{t('kpis.total')}</span>
          <strong data-testid="crm-docs-total">{stats.total.toLocaleString(locale)}</strong>
        </button>
        <button
          type="button"
          className={`crm-comm-live__kpi crm-comm-live__kpi--btn${scope === 'person' ? ' is-active' : ''}`}
          onClick={() => selectKpi('person')}
        >
          <span>{t('kpis.person')}</span>
          <strong data-testid="crm-docs-person">{stats.person.toLocaleString(locale)}</strong>
        </button>
        <button
          type="button"
          className={`crm-comm-live__kpi crm-comm-live__kpi--btn${scope === 'purchase' ? ' is-active' : ''}`}
          onClick={() => selectKpi('purchase')}
        >
          <span>{t('kpis.purchase')}</span>
          <strong data-testid="crm-docs-purchase">{stats.purchase.toLocaleString(locale)}</strong>
        </button>
        <button
          type="button"
          className={`crm-comm-live__kpi crm-comm-live__kpi--btn${visibility === 'hidden' ? ' is-active' : ''}`}
          onClick={() => selectKpi('', 'hidden')}
        >
          <span>{t('kpis.hidden')}</span>
          <strong data-testid="crm-docs-hidden">{stats.hidden.toLocaleString(locale)}</strong>
        </button>
        <button
          type="button"
          className={`crm-comm-live__kpi crm-comm-live__kpi--btn${scope === 'unresolved' ? ' is-active' : ''}`}
          onClick={() => selectKpi('unresolved')}
          data-testid="crm-docs-unresolved-tab"
        >
          <span>{t('kpis.unresolved')}</span>
          <strong data-testid="crm-docs-unresolved">{stats.unresolved.toLocaleString(locale)}</strong>
        </button>
      </section>

      <section className="crm-tasks__filters" aria-label={t('filters.aria')}>
        <div className="crm-tasks__search">
          <Input
            label={t('filters.search')}
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder={t('filters.searchPlaceholder')}
          />
        </div>
        <Input
          label={t('filters.person')}
          value={personDraft}
          onChange={(event) => setPersonDraft(event.target.value)}
          placeholder={t('filters.personPlaceholder')}
        />
        <Select
          label={t('filters.project')}
          value={projectGroup}
          onChange={(event) => {
            setProjectGroup(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{t('filters.anyProject')}</option>
          {PROJECTS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </Select>
        <Input
          label={t('filters.unit')}
          value={unitDraft}
          onChange={(event) => setUnitDraft(event.target.value)}
          placeholder={t('filters.unitPlaceholder')}
        />
        <Select
          label={t('filters.category')}
          value={category}
          onChange={(event) => {
            setCategory(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{t('filters.anyCategory')}</option>
          {CATEGORIES.map((item) => (
            <option key={item} value={item}>
              {t(`categories.${item}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.source')}
          value={source}
          onChange={(event) => {
            setSource(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{t('filters.anySource')}</option>
          {SOURCES.map((item) => (
            <option key={item.value} value={item.value}>
              {t(item.labelKey)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.date')}
          value={date}
          onChange={(event) => {
            setDate(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{t('filters.anyDate')}</option>
          <option value="today">{t('filters.today')}</option>
          <option value="7d">{t('filters.d7')}</option>
          <option value="30d">{t('filters.d30')}</option>
          <option value="90d">{t('filters.d90')}</option>
        </Select>
        <Select
          label={t('filters.visibility')}
          value={visibility}
          onChange={(event) => {
            setVisibility(event.target.value);
            setPage(1);
          }}
        >
          <option value="visible">{t('filters.visible')}</option>
          <option value="hidden">{t('filters.hidden')}</option>
          <option value="all">{t('filters.allVisibility')}</option>
        </Select>
        <div className="crm-tasks__filter-actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {t('filters.clear')}
          </Button>
        </div>
      </section>

      {feedQuery.isError ? (
        <ErrorState title={t('title')} message={feedQuery.error.message} />
      ) : items.length === 0 ? (
        <div className="crm-tasks__empty">{t('empty')}</div>
      ) : (
        <div className="crm-tasks__table-wrap" role="region" aria-label={t('tableAria')}>
          <table className="crm-tasks__table crm-tasks__table--ops">
            <thead>
              <tr>
                <th>{t('columns.document')}</th>
                <th>{t('columns.type')}</th>
                <th>{t('columns.person')}</th>
                <th>{t('columns.project')}</th>
                <th>{t('columns.source')}</th>
                <th>{t('columns.date')}</th>
                <th>{t('columns.status')}</th>
                <th>{t('columns.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.source_key}
                  className={`crm-tasks__row${selected?.id === item.id ? ' is-selected' : ''}${item.hidden ? ' is-muted' : ''}`}
                  onClick={() => setSelected(item)}
                  data-testid={`doc-row-${item.id}`}
                >
                  <td>
                    <strong>{item.filename}</strong>
                    {item.historical_unit ? <div className="crm-docs-live__hint">{t('historicalHint', { unit: item.historical_unit })}</div> : null}
                  </td>
                  <td>{item.category_label}</td>
                  <td>
                    {item.contact_id ? (
                      <button
                        type="button"
                        className="crm-tasks__link-btn"
                        onClick={(event) => {
                          event.stopPropagation();
                          openContact(item.contact_id!);
                        }}
                      >
                        {item.contact_name || t('openPerson')}
                      </button>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>
                    {item.agreement_id && item.contact_id ? (
                      <a
                        href={salesDetailUrl(item.contact_id, item.agreement_id)}
                        className="crm-tasks__link-btn"
                        onClick={(event) => event.stopPropagation()}
                      >
                        {item.project_unit || t('openPurchase')}
                      </a>
                    ) : (
                      item.project_unit || '—'
                    )}
                  </td>
                  <td>{item.source || '—'}</td>
                  <td>{formatWhen(item.occurred_at, locale)}</td>
                  <td>
                    <StatusChip tone={statusTone(item.status)}>
                      {item.status === 'inceleme' ? t('status.review') : item.hidden ? t('status.hidden') : t('status.visible')}
                    </StatusChip>
                  </td>
                  <td>
                    <div className="crm-docs-live__actions">
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={(event) => {
                          event.stopPropagation();
                          window.open(documentDownloadUrl(item.id), '_blank', 'noopener');
                        }}
                      >
                        {t('open')}
                      </Button>
                      {canUpdate ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          onClick={(event) => {
                            event.stopPropagation();
                            hideMutation.mutate({ id: item.id, hidden: !item.hidden });
                          }}
                        >
                          {item.hidden ? t('restore') : t('hide')}
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="crm-tasks__pagination">
        <Button type="button" variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
          {t('previous')}
        </Button>
        <span>
          {page} / {pages}
        </span>
        <Button type="button" variant="secondary" size="sm" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>
          {t('next')}
        </Button>
      </div>

      {selected ? (
        <>
          <button type="button" className="crm-tasks__drawer-backdrop" aria-label={tCommon('close')} onClick={() => setSelected(null)} />
          <aside className="crm-tasks__drawer" role="dialog" aria-label={t('drawerTitle')} data-testid="crm-docs-drawer">
            <div className="crm-tasks__drawer-head">
              <h3>{t('drawerTitle')}</h3>
              <button type="button" className="crm-tasks__link-btn" onClick={() => setSelected(null)}>
                {tCommon('close')}
              </button>
            </div>
            <div className="crm-tasks__drawer-body">
              <dl className="crm-tasks__kv">
                <dt>{t('drawer.filename')}</dt>
                <dd>{selected.filename}</dd>
                <dt>{t('drawer.category')}</dt>
                <dd>{selected.category_label}</dd>
                <dt>{t('drawer.size')}</dt>
                <dd>{formatSize(selected.file_size, locale)}</dd>
                <dt>{t('drawer.date')}</dt>
                <dd>{formatWhen(selected.occurred_at, locale)}</dd>
                <dt>{t('drawer.source')}</dt>
                <dd>{selected.source || '—'}</dd>
                <dt>{t('drawer.person')}</dt>
                <dd>{selected.contact_name || '—'}</dd>
                <dt>{t('drawer.purchase')}</dt>
                <dd>{selected.project_unit || '—'}</dd>
                {selected.historical_unit ? (
                  <>
                    <dt>{t('drawer.historicalUnit')}</dt>
                    <dd>{selected.historical_unit}</dd>
                    <dt>{t('drawer.currentUnit')}</dt>
                    <dd>{selected.current_unit || '—'}</dd>
                  </>
                ) : selected.unit_number ? (
                  <>
                    <dt>{t('drawer.unit')}</dt>
                    <dd>{selected.unit_number}</dd>
                  </>
                ) : null}
              </dl>
              <p className="crm-docs-live__internal">
                {t('drawer.checksum')}: {selected.checksum || '—'}
                {selected.bitrix_file_id ? ` · ${t('drawer.sourceFile')}: ${selected.bitrix_file_id}` : ''}
              </p>
              <div className="crm-tasks__drawer-actions">
                <a className="crm-tasks__link-btn" href={documentDownloadUrl(selected.id)} target="_blank" rel="noreferrer">
                  {selected.previewable ? t('preview') : t('open')}
                </a>
                {selected.contact_id ? (
                  <Button type="button" size="sm" onClick={() => openContact(selected.contact_id!)}>
                    {t('openPerson')}
                  </Button>
                ) : null}
                {selected.agreement_id && selected.contact_id ? (
                  <a className="crm-tasks__link-btn" href={salesDetailUrl(selected.contact_id, selected.agreement_id)}>
                    {t('openPurchase')}
                  </a>
                ) : null}
                {canUpdate ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => hideMutation.mutate({ id: selected.id, hidden: !selected.hidden })}
                  >
                    {selected.hidden ? t('restore') : t('hide')}
                  </Button>
                ) : null}
              </div>
              <div className="crm-docs-live__preview">
                <PreviewBody
                  doc={{
                    id: selected.id,
                    title: selected.filename,
                    original_file_name: selected.filename,
                    mime_type: selected.mime_type,
                    checksum: selected.checksum,
                    bitrix_file_id: selected.bitrix_file_id,
                  }}
                />
              </div>
            </div>
          </aside>
        </>
      ) : null}
    </div>
  );
}
