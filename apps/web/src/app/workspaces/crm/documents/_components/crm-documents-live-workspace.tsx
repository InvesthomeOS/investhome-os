'use client';

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { documentDownloadUrl } from '@/lib/api/documents';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { PreviewBody } from '@/workspaces/crm/contact-card/document-gallery';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import type { CrmDocumentFeedItem } from '@/workspaces/crm/api/crm-documents';
import { crmDocumentQueries, hideCrmDocument } from '@/workspaces/crm/hooks/use-crm-documents';

import '../../contacts/_components/ds/contacts-ds.css';

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

type FileKind = 'pdf' | 'excel' | 'image' | 'word' | 'other';
type StatusKey = 'visible' | 'hidden' | 'review';

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
  return new Date(value).toLocaleDateString(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function formatSize(bytes: number, locale: string): string | null {
  if (!bytes) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toLocaleString(locale, { maximumFractionDigits: 1 })} KB`;
  return `${(bytes / (1024 * 1024)).toLocaleString(locale, { maximumFractionDigits: 1 })} MB`;
}

function fileKind(item: CrmDocumentFeedItem): FileKind {
  const mime = (item.mime_type || '').toLowerCase();
  const name = (item.filename || '').toLowerCase();
  const kind = (item.file_kind || '').toLowerCase();
  if (kind === 'pdf' || mime.includes('pdf') || name.endsWith('.pdf')) return 'pdf';
  if (kind === 'excel' || mime.includes('spreadsheet') || mime.includes('excel') || /\.xlsx?$/.test(name)) return 'excel';
  if (kind === 'image' || mime.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg)$/.test(name)) return 'image';
  if (kind === 'word' || mime.includes('word') || /\.docx?$/.test(name)) return 'word';
  return 'other';
}

function fileKindLabel(kind: FileKind): string {
  if (kind === 'pdf') return 'PDF';
  if (kind === 'excel') return 'XLS';
  if (kind === 'image') return 'IMG';
  if (kind === 'word') return 'DOC';
  return 'FILE';
}

function statusKey(item: CrmDocumentFeedItem): StatusKey {
  if (item.status === 'inceleme' || item.scope === 'unresolved') return 'review';
  if (item.hidden || item.status === 'gizli') return 'hidden';
  return 'visible';
}

function projectDisplay(item: CrmDocumentFeedItem): { title: string; unit: string | null } {
  if (item.project_group === 'reit') {
    return { title: item.project_label || 'REIT', unit: item.unit_number || null };
  }
  if (item.project_label) {
    return { title: item.project_label, unit: item.unit_number || null };
  }
  return { title: item.project_unit || '', unit: item.project_label ? item.unit_number : null };
}

function visiblePages(page: number, pages: number): Array<number | 'ellipsis'> {
  if (pages <= 7) return Array.from({ length: pages }, (_, index) => index + 1);
  const wanted = new Set([1, pages, page - 1, page, page + 1]);
  const nums = [...wanted].filter((value) => value >= 1 && value <= pages).sort((a, b) => a - b);
  const next: Array<number | 'ellipsis'> = [];
  for (const value of nums) {
    const last = next[next.length - 1];
    if (typeof last === 'number' && value - last > 1) next.push('ellipsis');
    next.push(value);
  }
  return next;
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
  const [pageSize, setPageSize] = useState(10);
  const [selected, setSelected] = useState<CrmDocumentFeedItem | null>(null);
  const [menuId, setMenuId] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchDraft.trim());
      setPerson(personDraft.trim());
      setUnit(unitDraft.trim());
      setPage(1);
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft, personDraft, unitDraft]);

  useEffect(() => {
    const close = () => setMenuId(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, []);

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
      page_size: pageSize,
      ...dateRange(date),
    }),
    [search, person, projectGroup, unit, category, source, visibility, scope, date, page, pageSize],
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
      setMenuId(null);
    },
  });

  const stats = feedQuery.data?.stats ?? { total: 0, person: 0, purchase: 0, hidden: 0, unresolved: 0 };
  const items = feedQuery.data?.items ?? [];
  const total = feedQuery.data?.total ?? 0;
  const pages = feedQuery.data?.pages ?? 1;
  const from = total ? (page - 1) * pageSize + 1 : 0;
  const to = Math.min(page * pageSize, total);
  const hasFilters = Boolean(
    searchDraft || personDraft || unitDraft || projectGroup || category || source || date || visibility !== 'visible' || scope,
  );

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

  const openRow = (item: CrmDocumentFeedItem) => {
    setSelected(item);
    setMenuId(null);
  };

  const shell = (content: ReactNode) => (
    <div className="ctc-ds crm-docs" data-testid="crm-documents-live">
      {content}
    </div>
  );

  if (authLoading || feedQuery.isLoading) {
    return shell(
      <div className="crm-docs-skeleton" aria-hidden="true">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} />
        ))}
      </div>,
    );
  }

  if (!canRead) {
    return <ErrorState title={t('title')} message={tCommon('retry')} />;
  }

  return shell(
    <>
      <header className="crm-docs__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="crm-docs-kpis" aria-label={t('kpis.aria')}>
        {(
          [
            { id: 'all', value: stats.total, label: t('kpis.total'), icon: 'documents' as const, testId: 'crm-docs-total', active: !scope && visibility === 'visible', onClick: () => selectKpi('', 'visible'), warn: false },
            { id: 'person', value: stats.person, label: t('kpis.person'), icon: 'user' as const, testId: 'crm-docs-person', active: scope === 'person', onClick: () => selectKpi('person'), warn: false },
            { id: 'purchase', value: stats.purchase, label: t('kpis.purchase'), icon: 'inventory' as const, testId: 'crm-docs-purchase', active: scope === 'purchase', onClick: () => selectKpi('purchase'), warn: false },
            { id: 'hidden', value: stats.hidden, label: t('kpis.hidden'), icon: 'empty' as const, testId: 'crm-docs-hidden', active: visibility === 'hidden', onClick: () => selectKpi('', 'hidden'), warn: false },
            { id: 'unresolved', value: stats.unresolved, label: t('kpis.unresolved'), icon: 'alert' as const, testId: 'crm-docs-unresolved', active: scope === 'unresolved', onClick: () => selectKpi('unresolved'), warn: true },
          ] as const
        ).map((item) => (
          <button
            key={item.id}
            type="button"
            className={`${item.active ? 'is-active' : ''}${item.warn ? ' is-warn' : ''}`}
            onClick={item.onClick}
            data-testid={item.id === 'unresolved' ? 'crm-docs-unresolved-tab' : undefined}
          >
            <span className="crm-docs-kpis__icon" aria-hidden>
              <IhIcon name={item.icon} size={16} />
            </span>
            <strong data-testid={item.testId}>{item.value.toLocaleString(locale)}</strong>
            <span>{item.label}</span>
          </button>
        ))}
      </section>

      <section className="crm-docs-filtercard" aria-label={t('filters.aria')}>
        <Input
          label={t('filters.search')}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={t('filters.searchPlaceholder')}
        />
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
        <div className="crm-docs-filtercard__actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters} disabled={!hasFilters}>
            {t('filters.clear')}
          </Button>
          <p className="crm-docs-count">{t('count', { count: total })}</p>
        </div>
      </section>

      {feedQuery.isError ? (
        <ErrorState title={t('title')} message={feedQuery.error.message} />
      ) : items.length === 0 ? (
        <div className="crm-docs-empty">{t('empty')}</div>
      ) : (
        <section className="crm-docs-tablecard" aria-label={t('tableAria')}>
          <div className="crm-docs-table-wrap">
            <table className="crm-docs-table">
              <thead>
                <tr>
                  <th className="is-document">{t('columns.document')}</th>
                  <th>{t('columns.type')}</th>
                  <th>{t('columns.person')}</th>
                  <th>{t('columns.project')}</th>
                  <th>{t('columns.source')}</th>
                  <th>{t('columns.date')}</th>
                  <th>{t('columns.status')}</th>
                  <th className="is-actions">{t('columns.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const kind = fileKind(item);
                  const size = formatSize(item.file_size, locale);
                  const project = projectDisplay(item);
                  const status = statusKey(item);
                  return (
                    <tr
                      key={item.source_key}
                      className={`crm-docs-row${selected?.id === item.id ? ' is-selected' : ''}${item.hidden ? ' is-muted' : ''}`}
                      onClick={() => openRow(item)}
                      data-testid={`doc-row-${item.id}`}
                    >
                      <td className="is-document">
                        <div className="crm-docs-file">
                          <span className={`crm-docs-file__icon is-${kind}`} aria-hidden>
                            {fileKindLabel(kind)}
                          </span>
                          <div>
                            <strong title={item.filename}>{item.filename}</strong>
                            {size ? <small>{size}</small> : null}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="crm-docs-type">{item.category_label}</span>
                      </td>
                      <td>
                        {item.contact_id ? (
                          <button
                            type="button"
                            className="crm-docs-link"
                            title={item.contact_name || undefined}
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
                        {project.title || project.unit ? (
                          <div className="crm-docs-project" title={[project.title, project.unit].filter(Boolean).join(' · ')}>
                            {item.agreement_id && item.contact_id ? (
                              <a
                                href={salesDetailUrl(item.contact_id, item.agreement_id)}
                                className="crm-docs-link"
                                onClick={(event) => event.stopPropagation()}
                              >
                                <strong>{project.title || project.unit}</strong>
                                {project.title && project.unit ? <span>{project.unit}</span> : null}
                              </a>
                            ) : (
                              <>
                                <strong>{project.title || project.unit}</strong>
                                {project.title && project.unit ? <span>{project.unit}</span> : null}
                              </>
                            )}
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>{item.source || '—'}</td>
                      <td className="is-nowrap">{formatWhen(item.occurred_at, locale)}</td>
                      <td>
                        <span className={`crm-docs-status is-${status}`}>{t(`status.${status}`)}</span>
                      </td>
                      <td className="is-actions">
                        <div className="crm-docs-actions">
                          <button
                            type="button"
                            className="crm-docs-action"
                            onClick={(event) => {
                              event.stopPropagation();
                              openRow(item);
                            }}
                          >
                            {t('open')}
                          </button>
                          <a
                            className="crm-docs-action"
                            href={documentDownloadUrl(item.id)}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(event) => event.stopPropagation()}
                          >
                            {t('download')}
                          </a>
                          {canUpdate ? (
                            <div className="crm-docs-more">
                              <button
                                type="button"
                                className="crm-docs-action is-more"
                                aria-label={t('more')}
                                onClick={(event) => {
                                  event.stopPropagation();
                                  setMenuId((current) => (current === item.id ? null : item.id));
                                }}
                              >
                                …
                              </button>
                              {menuId === item.id ? (
                                <div className="crm-docs-more__panel">
                                  <button
                                    type="button"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      hideMutation.mutate({ id: item.id, hidden: !item.hidden });
                                    }}
                                  >
                                    {item.hidden ? t('restore') : t('hide')}
                                  </button>
                                </div>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <footer className="crm-docs-pager">
            <p>{t('pager', { total, from, to })}</p>
            <div>
              <button type="button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>
                ‹
              </button>
              {visiblePages(page, pages).map((item, index) =>
                item === 'ellipsis' ? (
                  <span key={`e${index}`}>…</span>
                ) : (
                  <button
                    key={item}
                    type="button"
                    className={item === page ? 'is-active' : undefined}
                    onClick={() => setPage(item)}
                  >
                    {item}
                  </button>
                ),
              )}
              <button type="button" disabled={page >= pages} onClick={() => setPage((value) => Math.min(pages, value + 1))}>
                ›
              </button>
            </div>
            <label>
              {t('pageSize')}
              <select
                value={pageSize}
                onChange={(event) => {
                  setPageSize(Number(event.target.value));
                  setPage(1);
                }}
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
            </label>
          </footer>
        </section>
      )}

      {selected ? (
        <>
          <button type="button" className="crm-docs-drawer-backdrop" aria-label={tCommon('close')} onClick={() => setSelected(null)} />
          <aside className="crm-docs-drawer" role="dialog" aria-label={t('drawerTitle')} data-testid="crm-docs-drawer">
            <div className="crm-docs-drawer__head">
              <h3>{t('drawerTitle')}</h3>
              <button type="button" className="crm-docs-link" onClick={() => setSelected(null)}>
                {tCommon('close')}
              </button>
            </div>
            <div className="crm-docs-drawer__body">
              <dl className="crm-docs-kv">
                <dt>{t('drawer.filename')}</dt>
                <dd>{selected.filename}</dd>
                <dt>{t('drawer.category')}</dt>
                <dd>{selected.category_label}</dd>
                <dt>{t('drawer.size')}</dt>
                <dd>{formatSize(selected.file_size, locale) || '—'}</dd>
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
              <div className="crm-docs-drawer__actions">
                <a className="crm-docs-action" href={documentDownloadUrl(selected.id)} target="_blank" rel="noreferrer">
                  {selected.previewable ? t('preview') : t('open')}
                </a>
                {selected.contact_id ? (
                  <Button type="button" size="sm" onClick={() => openContact(selected.contact_id!)}>
                    {t('openPerson')}
                  </Button>
                ) : null}
                {selected.agreement_id && selected.contact_id ? (
                  <a className="crm-docs-link" href={salesDetailUrl(selected.contact_id, selected.agreement_id)}>
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
              <div className="crm-docs-preview">
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
    </>,
  );
}
