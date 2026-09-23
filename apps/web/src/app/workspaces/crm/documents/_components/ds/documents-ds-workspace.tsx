'use client';

import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import { Button, Input, SegmentedControl, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  DOC_CATEGORY_TABS,
  DOC_ENTITY_KINDS,
  DOC_FILE_TYPES,
  DOC_FOLDERS,
  DOC_SHORTCUTS,
  DOC_SORT_KEYS,
  EMPTY_DOC_FILTERS,
  FILE_TYPE_ICON,
  FOLDER_TONE,
  STORAGE_TOTAL_GB,
  STORAGE_USED_GB,
  countByEntity,
  countByFolder,
  countByShortcut,
  countByTab,
  fileTypeLabel,
  filterDocuments,
  makeDocumentsDsFixture,
  uniqueOwners,
  uniqueTags,
  type DocEntityKind,
  type DocFileType,
  type DocFilters,
  type DocPreviewKind,
  type DocPreviewTab,
  type DocRecord,
  type DocSortKey,
  type DocViewMode,
} from './documents-ds-model';

import './documents-ds.css';

const PAGE_SIZE = 12;

function FileTypeIcon({ type, size = 16 }: { type: DocFileType; size?: number }) {
  return (
    <span className={`documents-ds__type-icon is-${type}`} aria-hidden="true">
      <IhIcon name={FILE_TYPE_ICON[type]} size={size} />
    </span>
  );
}

function MockPreview({ kind, label }: { kind: DocPreviewKind; label: string }) {
  if (kind === 'xlsx') {
    return (
      <div className="documents-ds__mock documents-ds__mock--xlsx" aria-hidden="true">
        <div className="documents-ds__mock-sheet-head">
          <span />
          <span />
          <span />
          <span />
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="documents-ds__mock-sheet-row">
            <span />
            <span />
            <span />
            <span />
          </div>
        ))}
      </div>
    );
  }
  if (kind === 'pptx') {
    return (
      <div className="documents-ds__mock documents-ds__mock--pptx" aria-hidden="true">
        <div className="documents-ds__mock-slide">
          <strong>{label}</strong>
          <em />
          <em />
        </div>
      </div>
    );
  }
  if (kind === 'blueprint') {
    return (
      <div className="documents-ds__mock documents-ds__mock--blueprint" aria-hidden="true">
        <svg viewBox="0 0 160 100" preserveAspectRatio="none">
          <rect x="12" y="14" width="58" height="42" fill="none" stroke="currentColor" strokeWidth="1.2" />
          <rect x="78" y="14" width="70" height="72" fill="none" stroke="currentColor" strokeWidth="1.2" />
          <line x1="12" y1="35" x2="70" y2="35" stroke="currentColor" strokeWidth="0.8" />
          <line x1="41" y1="14" x2="41" y2="56" stroke="currentColor" strokeWidth="0.8" />
          <line x1="78" y1="50" x2="148" y2="50" stroke="currentColor" strokeWidth="0.8" />
          <circle cx="113" cy="32" r="8" fill="none" stroke="currentColor" strokeWidth="0.9" />
          <path d="M20 72h40M28 64v16M52 64v16" fill="none" stroke="currentColor" strokeWidth="0.9" />
        </svg>
      </div>
    );
  }
  if (kind === 'permit') {
    return (
      <div className="documents-ds__mock documents-ds__mock--permit" aria-hidden="true">
        <div className="documents-ds__mock-page">
          <header />
          <div className="documents-ds__mock-lines">
            <span />
            <span />
            <span />
            <span />
          </div>
          <div className="documents-ds__mock-stamp">RUHSAT</div>
        </div>
      </div>
    );
  }
  if (kind === 'docx') {
    return (
      <div className="documents-ds__mock documents-ds__mock--docx" aria-hidden="true">
        <div className="documents-ds__mock-page">
          <strong />
          <div className="documents-ds__mock-lines">
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>
    );
  }
  if (kind === 'pdf') {
    return (
      <div className="documents-ds__mock documents-ds__mock--pdf" aria-hidden="true">
        <div className="documents-ds__mock-page">
          <header />
          <div className="documents-ds__mock-lines">
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>
    );
  }
  if (kind === 'zip') {
    return (
      <div className="documents-ds__mock documents-ds__mock--zip" aria-hidden="true">
        <IhIcon name="inbox" size={28} />
        <small>ZIP</small>
      </div>
    );
  }
  return (
    <div className="documents-ds__mock documents-ds__mock--icon" aria-hidden="true">
      <IhIcon name="documents" size={28} />
    </div>
  );
}

function DocThumbVisual({ doc, large }: { doc: DocRecord; large?: boolean }) {
  const kind = doc.previewKind;
  const showPhoto = Boolean(doc.thumbnailUrl) && (kind === 'photo' || kind === 'video');

  if (showPhoto && doc.thumbnailUrl) {
    return (
      <div className={`documents-ds__thumb-media${large ? ' is-large' : ''}${kind === 'video' ? ' is-video' : ''}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={doc.thumbnailUrl} alt="" loading="lazy" />
        {kind === 'video' ? (
          <span className="documents-ds__video-badge" aria-hidden="true">
            ▶
          </span>
        ) : null}
      </div>
    );
  }

  if (kind === 'icon' || (!doc.hasThumbnail && !doc.thumbnailUrl && kind === 'zip')) {
    return (
      <span className="documents-ds__type-badge">
        <IhIcon name={FILE_TYPE_ICON[doc.fileType]} size={large ? 28 : 22} />
        <small>{fileTypeLabel(doc.fileType)}</small>
      </span>
    );
  }

  return <MockPreview kind={kind === 'video' ? 'pdf' : kind} label={fileTypeLabel(doc.fileType)} />;
}

function PreviewStage({ doc }: { doc: DocRecord }) {
  const t = useTranslations('crm.documents.ds');
  const isPhoto = Boolean(doc.thumbnailUrl) && (doc.previewKind === 'photo' || doc.previewKind === 'video');
  const isCad = doc.fileType === 'dwg' || doc.fileType === 'cad';

  return (
    <div
      className={`documents-ds__preview-stage is-${doc.previewKind}${isPhoto ? ' has-media' : ''}`}
      data-testid="documents-ds-preview-stage"
    >
      <div className="documents-ds__preview-hero">
        <DocThumbVisual doc={doc} large />
      </div>
      {!isPhoto ? (
        <div className="documents-ds__preview-caption">
          <strong>{fileTypeLabel(doc.fileType)}</strong>
          <p>
            {isCad
              ? t('preview.cadPlaceholder')
              : doc.fileType === 'video'
                ? t('preview.videoPlaceholder')
                : doc.previewHint}
          </p>
        </div>
      ) : null}
    </div>
  );
}

function DocumentCard({
  doc,
  selected,
  onSelect,
  onFavorite,
  onPreview,
  onDownload,
  onShare,
}: {
  doc: DocRecord;
  selected: boolean;
  onSelect: () => void;
  onFavorite: () => void;
  onPreview: () => void;
  onDownload: () => void;
  onShare: () => void;
}) {
  const t = useTranslations('crm.documents.ds');
  const rich = doc.hasThumbnail || Boolean(doc.thumbnailUrl) || doc.previewKind !== 'icon';

  return (
    <article
      className={`documents-ds__card${selected ? ' is-selected' : ''}`}
      data-testid={`documents-ds-card-${doc.id}`}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
      role="button"
      tabIndex={0}
    >
      <div className={`documents-ds__card-thumb${rich ? ' is-rich' : ''}${doc.thumbnailUrl ? ' is-image' : ''}`}>
        <DocThumbVisual doc={doc} />
        <span className={`documents-ds__file-pill is-${doc.fileType}`}>{fileTypeLabel(doc.fileType)}</span>
        <button
          type="button"
          className={`documents-ds__ghost-btn documents-ds__card-fav${doc.isFavorite ? ' is-active' : ''}`}
          aria-label={t('actions.favorite')}
          onClick={(e) => {
            e.stopPropagation();
            onFavorite();
          }}
        >
          <IhIcon name="sparkles" size={12} />
        </button>
        <div className="documents-ds__card-hover">
          <button
            type="button"
            className="documents-ds__icon-btn"
            aria-label={t('actions.preview')}
            onClick={(e) => {
              e.stopPropagation();
              onPreview();
            }}
          >
            <IhIcon name="search" size={12} />
          </button>
          <button
            type="button"
            className="documents-ds__icon-btn"
            aria-label={t('actions.download')}
            onClick={(e) => {
              e.stopPropagation();
              onDownload();
            }}
          >
            <IhIcon name="inbox" size={12} />
          </button>
          <button
            type="button"
            className="documents-ds__icon-btn"
            aria-label={t('actions.share')}
            onClick={(e) => {
              e.stopPropagation();
              onShare();
            }}
          >
            <IhIcon name="activity" size={12} />
          </button>
        </div>
      </div>
      <div className="documents-ds__card-body">
        <h3 className="documents-ds__card-name" title={doc.name}>
          {doc.name}
        </h3>
        <div className="documents-ds__card-footer">
          <StatusChip tone={FOLDER_TONE[doc.folder]}>{t(`folders.${doc.folder}`)}</StatusChip>
          {doc.related[0] ? (
            <StatusChip tone="info">{doc.related[0].name}</StatusChip>
          ) : (
            <span className="documents-ds__card-footer-spacer" aria-hidden="true" />
          )}
        </div>
        <div className="documents-ds__card-meta">
          <span>{doc.sizeLabel}</span>
          <span aria-hidden="true">·</span>
          <span>{doc.uploadedAt}</span>
        </div>
      </div>
    </article>
  );
}

function PreviewPanel({
  doc,
  tab,
  onTabChange,
  onClose,
  onFavorite,
  onAction,
  showClose,
}: {
  doc: DocRecord | null;
  tab: DocPreviewTab;
  onTabChange: (tab: DocPreviewTab) => void;
  onClose?: () => void;
  onFavorite: () => void;
  onAction: (key: string) => void;
  showClose?: boolean;
}) {
  const t = useTranslations('crm.documents.ds');
  const router = useRouter();

  if (!doc) {
    return (
      <div className="documents-ds__empty" style={{ flex: 1 }}>
        <IhIcon name="documents" size={22} />
        <strong>{t('preview.emptyTitle')}</strong>
        <p>{t('preview.emptyDescription')}</p>
      </div>
    );
  }

  return (
    <>
      <div className="documents-ds__preview-head">
        <div className="documents-ds__preview-heading">
          <h2 className="documents-ds__preview-title" title={doc.name}>
            {doc.name}
          </h2>
          <p className="documents-ds__preview-submeta">
            <span>{fileTypeLabel(doc.fileType)}</span>
            <span aria-hidden="true">·</span>
            <span>{doc.sizeLabel}</span>
            <span aria-hidden="true">·</span>
            <span>{doc.updatedAt}</span>
          </p>
        </div>
        <div className="documents-ds__preview-actions">
          <button
            type="button"
            className={`documents-ds__ghost-btn${doc.isFavorite ? ' is-active' : ''}`}
            aria-label={t('actions.favorite')}
            onClick={onFavorite}
          >
            <IhIcon name="sparkles" size={13} />
          </button>
          {showClose && onClose ? (
            <button
              type="button"
              className="documents-ds__ghost-btn"
              aria-label={t('preview.close')}
              onClick={onClose}
            >
              <IhIcon name="chevronRight" size={13} />
            </button>
          ) : null}
        </div>
      </div>

      <div className="documents-ds__viewer-tabs" role="tablist" aria-label={t('preview.tabsAria')}>
        {(
          [
            ['preview', t('preview.tabs.preview')],
            ['details', t('preview.tabs.details')],
            ['history', t('preview.tabs.history')],
            ['shares', t('preview.tabs.shares', { count: doc.shares.length })],
          ] as Array<[DocPreviewTab, string]>
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className={`documents-ds__tab${tab === key ? ' is-active' : ''}`}
            onClick={() => onTabChange(key)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="documents-ds__preview-body">
        {tab === 'preview' ? (
          <>
            <PreviewStage doc={doc} />

            <div className="documents-ds__panel-group">
              <section className="documents-ds__section" aria-label={t('details.fileInfo')}>
                <div className="documents-ds__section-head">
                  <h3>{t('details.fileInfo')}</h3>
                </div>
                <dl className="documents-ds__meta-grid">
                  <div className="documents-ds__meta-item">
                    <dt>{t('details.size')}</dt>
                    <dd>{doc.sizeLabel}</dd>
                  </div>
                  <div className="documents-ds__meta-item">
                    <dt>{t('details.type')}</dt>
                    <dd>{fileTypeLabel(doc.fileType)}</dd>
                  </div>
                  <div className="documents-ds__meta-item">
                    <dt>{t('details.version')}</dt>
                    <dd>
                      {doc.version}{' '}
                      <StatusChip tone="success">{t('details.current')}</StatusChip>
                    </dd>
                  </div>
                  <div className="documents-ds__meta-item">
                    <dt>{t('details.updated')}</dt>
                    <dd>{doc.updatedAt}</dd>
                  </div>
                  <div className="documents-ds__meta-item">
                    <dt>{t('details.createdBy')}</dt>
                    <dd>{doc.createdBy}</dd>
                  </div>
                  <div className="documents-ds__meta-item">
                    <dt>{t('details.owner')}</dt>
                    <dd>{doc.owner}</dd>
                  </div>
                  <div className="documents-ds__meta-item">
                    <dt>{t('details.folder')}</dt>
                    <dd>{t(`folders.${doc.folder}`)}</dd>
                  </div>
                  <div className="documents-ds__meta-item">
                    <dt>{t('details.language')}</dt>
                    <dd>{doc.language}</dd>
                  </div>
                </dl>
              </section>
            </div>

            <div className="documents-ds__panel-group">
              <section className="documents-ds__section" aria-label={t('details.related')}>
                <div className="documents-ds__section-head">
                  <h3>{t('details.related')}</h3>
                </div>
                {doc.related.length === 0 ? (
                  <p className="documents-ds__muted">{t('details.noRelated')}</p>
                ) : (
                  <div className="documents-ds__chip-row">
                    {doc.related.map((r) => (
                      <button
                        key={`${r.kind}-${r.id}`}
                        type="button"
                        className="documents-ds__related-chip"
                        onClick={() => router.push(r.href as Route)}
                        data-testid={`documents-ds-related-${r.kind}`}
                      >
                        <IhIcon
                          name={
                            r.kind === 'project'
                              ? 'projects'
                              : r.kind === 'company'
                                ? 'investors'
                                : r.kind === 'investor'
                                  ? 'trendingUp'
                                  : 'user'
                          }
                          size={11}
                        />
                        <span>
                          {t(`entities.${r.kind}`)}: {r.name}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </section>
            </div>

            <div className="documents-ds__panel-group">
              <section className="documents-ds__section" aria-label={t('details.tags')}>
                <div className="documents-ds__section-head">
                  <h3>{t('details.tags')}</h3>
                </div>
                <div className="documents-ds__chip-row">
                  {doc.tags.map((tag) => (
                    <StatusChip key={tag} tone="default">
                      {tag}
                    </StatusChip>
                  ))}
                </div>
              </section>
            </div>

            <div className="documents-ds__panel-group">
              <section className="documents-ds__section" aria-label={t('details.activity')}>
                <div className="documents-ds__section-head">
                  <h3>{t('details.activity')}</h3>
                </div>
                <div className="documents-ds__timeline">
                  {doc.activities.slice(0, 3).map((a) => (
                    <div key={a.id} className="documents-ds__timeline-item">
                      <span className="documents-ds__timeline-dot" aria-hidden="true" />
                      <div className="documents-ds__timeline-body">
                        <strong>
                          {a.actor} · {a.label}
                        </strong>
                        <span>{a.timeLabel}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </>
        ) : null}

        {tab === 'details' ? (
          <>
            <section className="documents-ds__section" aria-label={t('details.fileInfo')}>
              <div className="documents-ds__section-head">
                <h3>{t('details.fileInfo')}</h3>
              </div>
              <dl className="documents-ds__meta-grid">
                <div className="documents-ds__meta-item">
                  <dt>{t('details.size')}</dt>
                  <dd>{doc.sizeLabel}</dd>
                </div>
                <div className="documents-ds__meta-item">
                  <dt>{t('details.type')}</dt>
                  <dd>{fileTypeLabel(doc.fileType)}</dd>
                </div>
                <div className="documents-ds__meta-item">
                  <dt>{t('details.version')}</dt>
                  <dd>
                    {doc.version}{' '}
                    <StatusChip tone="success">{t('details.current')}</StatusChip>
                  </dd>
                </div>
                <div className="documents-ds__meta-item">
                  <dt>{t('details.updated')}</dt>
                  <dd>{doc.updatedAt}</dd>
                </div>
                <div className="documents-ds__meta-item">
                  <dt>{t('details.createdBy')}</dt>
                  <dd>{doc.createdBy}</dd>
                </div>
                <div className="documents-ds__meta-item">
                  <dt>{t('details.owner')}</dt>
                  <dd>{doc.owner}</dd>
                </div>
                <div className="documents-ds__meta-item">
                  <dt>{t('details.folder')}</dt>
                  <dd>{t(`folders.${doc.folder}`)}</dd>
                </div>
                <div className="documents-ds__meta-item">
                  <dt>{t('details.language')}</dt>
                  <dd>{doc.language}</dd>
                </div>
              </dl>
            </section>

            <section className="documents-ds__section" aria-label={t('details.related')}>
              <div className="documents-ds__section-head">
                <h3>{t('details.related')}</h3>
              </div>
              {doc.related.length === 0 ? (
                <p className="documents-ds__muted">{t('details.noRelated')}</p>
              ) : (
                <div className="documents-ds__chip-row">
                  {doc.related.map((r) => (
                    <button
                      key={`${r.kind}-${r.id}`}
                      type="button"
                      className="documents-ds__related-chip"
                      onClick={() => router.push(r.href as Route)}
                      data-testid={`documents-ds-related-${r.kind}`}
                    >
                      <IhIcon
                        name={
                          r.kind === 'project'
                            ? 'projects'
                            : r.kind === 'company'
                              ? 'investors'
                              : r.kind === 'investor'
                                ? 'trendingUp'
                                : 'user'
                        }
                        size={11}
                      />
                      <span>
                        {t(`entities.${r.kind}`)}: {r.name}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="documents-ds__section" aria-label={t('details.tags')}>
              <div className="documents-ds__section-head">
                <h3>{t('details.tags')}</h3>
              </div>
              <div className="documents-ds__chip-row">
                {doc.tags.map((tag) => (
                  <StatusChip key={tag} tone="default">
                    {tag}
                  </StatusChip>
                ))}
              </div>
            </section>
          </>
        ) : null}

        {tab === 'history' ? (
          <section className="documents-ds__section" aria-label={t('details.activity')}>
            <div className="documents-ds__section-head">
              <h3>{t('details.activity')}</h3>
            </div>
            <div className="documents-ds__timeline">
              {doc.activities.map((a) => (
                <div key={a.id} className="documents-ds__timeline-item">
                  <span className="documents-ds__timeline-dot" aria-hidden="true" />
                  <div className="documents-ds__timeline-body">
                    <strong>
                      {a.actor} · {a.label}
                    </strong>
                    <span>{a.timeLabel}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {tab === 'shares' ? (
          <section
            className="documents-ds__section"
            aria-label={t('preview.tabs.shares', { count: doc.shares.length })}
          >
            {doc.shares.length === 0 ? (
              <div className="documents-ds__empty" style={{ padding: 16 }}>
                <strong>{t('shares.emptyTitle')}</strong>
                <p>{t('shares.emptyDescription')}</p>
              </div>
            ) : (
              doc.shares.map((s) => (
                <div key={s.id} className="documents-ds__share-row">
                  <div style={{ minWidth: 0 }}>
                    <strong>{s.name}</strong>
                    <span>
                      {s.email} · {t(`shares.access.${s.access}`)} · {s.sharedAt}
                    </span>
                  </div>
                  <StatusChip tone="info">{t(`shares.access.${s.access}`)}</StatusChip>
                </div>
              ))
            )}
          </section>
        ) : null}

        <section className="documents-ds__section documents-ds__section--actions" aria-label={t('actions.quick')}>
          <div className="documents-ds__section-head">
            <h3>{t('actions.quick')}</h3>
          </div>
          <div className="documents-ds__actions">
            {(
              [
                ['open', 'documents', t('actions.open'), false],
                ['preview', 'search', t('actions.preview'), false],
                ['download', 'inbox', t('actions.download'), false],
                ['share', 'activity', t('actions.share'), false],
                ['copyLink', 'documents', t('actions.copyLink'), false],
                ['uploadVersion', 'plus', t('actions.uploadVersion'), false],
                ['move', 'projects', t('actions.move'), false],
                ['delete', 'alert', t('actions.delete'), true],
              ] as const
            ).map(([key, icon, label, danger]) => (
              <button
                key={key}
                type="button"
                className={`documents-ds__action-btn${danger ? ' is-danger' : ''}`}
                onClick={() => onAction(key)}
              >
                <IhIcon name={icon} size={12} />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}

export function DocumentsDsWorkspace() {
  const t = useTranslations('crm.documents.ds');
  const uploadRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<DocRecord[]>(() => makeDocumentsDsFixture());
  const [filters, setFilters] = useState<DocFilters>(EMPTY_DOC_FILTERS);
  const [searchDraft, setSearchDraft] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [previewTab, setPreviewTab] = useState<DocPreviewTab>('preview');
  const [page, setPage] = useState(1);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: searchDraft }));
      setPage(1);
    }, 200);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const owners = useMemo(() => uniqueOwners(docs), [docs]);
  const tags = useMemo(() => uniqueTags(docs), [docs]);
  const filtered = useMemo(() => filterDocuments(docs, filters), [docs, filters]);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageSafe = Math.min(page, totalPages);
  const pageItems = filtered.slice((pageSafe - 1) * PAGE_SIZE, pageSafe * PAGE_SIZE);
  const selected = docs.find((d) => d.id === selectedId) ?? pageItems[0] ?? filtered[0] ?? null;

  useEffect(() => {
    if (!selectedId && selected) setSelectedId(selected.id);
  }, [selected, selectedId]);

  const patchFilters = useCallback((patch: Partial<DocFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  }, []);

  const clearNavContext = useCallback(() => {
    setFilters((prev) => ({
      ...prev,
      shortcut: '',
      folder: '',
      entityNav: '',
    }));
  }, []);

  const selectDoc = (id: string) => {
    setSelectedId(id);
    setPreviewTab('preview');
    setMenuOpen(false);
    if (typeof window !== 'undefined' && window.innerWidth <= 1280) {
      setDrawerOpen(true);
    }
  };

  const toggleFavorite = (id: string) => {
    setDocs((prev) =>
      prev.map((d) => (d.id === id ? { ...d, isFavorite: !d.isFavorite } : d)),
    );
  };

  const showToast = (message: string) => setToast(message);

  const handleUploadClick = () => uploadRef.current?.click();

  const handleUploadChange = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0]!;
    const ext = file.name.split('.').pop()?.toLowerCase() ?? 'other';
    const typeMap: Record<string, DocFileType> = {
      pdf: 'pdf',
      doc: 'docx',
      docx: 'docx',
      xls: 'xlsx',
      xlsx: 'xlsx',
      ppt: 'pptx',
      pptx: 'pptx',
      dwg: 'dwg',
      jpg: 'jpg',
      jpeg: 'jpg',
      png: 'png',
      zip: 'zip',
      mp4: 'video',
      mov: 'video',
    };
    const fileType = typeMap[ext] ?? 'other';
    const id = `doc-upload-${Date.now()}`;
    const today = new Date();
    const label = `${String(today.getDate()).padStart(2, '0')}.${String(today.getMonth() + 1).padStart(2, '0')}.${today.getFullYear()}`;
    const newDoc: DocRecord = {
      id,
      name: file.name,
      fileType,
      folder: 'general',
      sizeLabel:
        file.size > 1_000_000
          ? `${(file.size / 1_000_000).toFixed(1)} MB`
          : `${Math.max(1, Math.round(file.size / 1000))} KB`,
      sizeBytes: file.size,
      version: 'v1.0',
      owner: 'Super Admin',
      createdBy: 'Super Admin',
      uploadedAt: label,
      updatedAt: label,
      language: 'TR',
      isFavorite: false,
      isShared: false,
      isMine: true,
      isFrequent: false,
      isTrashed: false,
      isRecent: true,
      hasThumbnail: fileType === 'jpg' || fileType === 'png',
      thumbnailUrl: null,
      previewKind:
        fileType === 'jpg' || fileType === 'png'
          ? 'photo'
          : fileType === 'xlsx'
            ? 'xlsx'
            : fileType === 'pptx'
              ? 'pptx'
              : fileType === 'docx'
                ? 'docx'
                : fileType === 'pdf'
                  ? 'pdf'
                  : fileType === 'dwg' || fileType === 'cad'
                    ? 'blueprint'
                    : fileType === 'zip'
                      ? 'zip'
                      : 'icon',
      tags: ['Yeni'],
      related: [],
      shares: [],
      activities: [
        {
          id: 'a1',
          kind: 'uploaded',
          actor: 'Super Admin',
          label: t('activity.uploaded'),
          timeLabel: t('activity.justNow'),
        },
      ],
      previewHint: file.name,
      source: 'documents',
    };
    setDocs((prev) => [newDoc, ...prev]);
    setSelectedId(id);
    showToast(t('toast.uploaded'));
    if (uploadRef.current) uploadRef.current.value = '';
  };

  const handleAction = (key: string) => {
    if (!selected) return;
    switch (key) {
      case 'download':
        showToast(t('toast.download'));
        break;
      case 'share':
        setPreviewTab('shares');
        showToast(t('toast.share'));
        break;
      case 'copyLink':
        void navigator.clipboard
          ?.writeText(`${window.location.origin}/workspaces/crm/documents?id=${selected.id}`)
          .catch(() => undefined);
        showToast(t('toast.linkCopied'));
        break;
      case 'uploadVersion':
        handleUploadClick();
        break;
      case 'move':
        showToast(t('toast.move'));
        break;
      case 'delete':
        setDocs((prev) =>
          prev.map((d) => (d.id === selected.id ? { ...d, isTrashed: true } : d)),
        );
        showToast(t('toast.deleted'));
        break;
      case 'open':
      case 'preview':
        setPreviewTab('preview');
        setDrawerOpen(true);
        break;
      case 'history':
        setPreviewTab('history');
        break;
      default:
        break;
    }
  };

  const storagePct = Math.min(100, Math.round((STORAGE_USED_GB / STORAGE_TOTAL_GB) * 100));

  return (
    <div className="documents-ds" data-testid="documents-ds-workspace">
      <input
        ref={uploadRef}
        type="file"
        className="documents-ds__upload-input"
        data-testid="documents-ds-upload-input"
        onChange={(e) => handleUploadChange(e.target.files)}
      />

      <header className="documents-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="documents-ds__header-actions">
          <span className="documents-ds__demo-badge">{t('demoBadge')}</span>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={handleUploadClick}
            data-testid="documents-ds-create"
          >
            <IhIcon name="plus" size={13} />
            {t('actions.create')}
          </Button>
        </div>
      </header>

      <section className="documents-ds__toolbar" aria-label={t('filters.aria')}>
        <div className="documents-ds__toolbar-filters">
          <div className="documents-ds__toolbar-search">
            <Input
              label={t('filters.search')}
              value={searchDraft}
              onChange={(e) => setSearchDraft(e.target.value)}
              placeholder={t('filters.searchPlaceholder')}
              data-testid="documents-ds-search"
            />
          </div>
          <Select
            label={t('filters.type')}
            value={filters.fileType}
            onChange={(e) => patchFilters({ fileType: e.target.value as DocFileType | '' })}
          >
            <option value="">{t('filters.allTypes')}</option>
            {DOC_FILE_TYPES.map((type) => (
              <option key={type} value={type}>
                {fileTypeLabel(type)}
              </option>
            ))}
          </Select>
          <Select
            label={t('filters.entity')}
            value={filters.entity}
            onChange={(e) => patchFilters({ entity: e.target.value as DocEntityKind | '' })}
          >
            <option value="">{t('filters.allEntities')}</option>
            {DOC_ENTITY_KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {t(`entities.${kind}`)}
              </option>
            ))}
          </Select>
          <Select
            label={t('filters.tag')}
            value={filters.tag}
            onChange={(e) => patchFilters({ tag: e.target.value })}
          >
            <option value="">{t('filters.allTags')}</option>
            {tags.map((tag) => (
              <option key={tag} value={tag}>
                {tag}
              </option>
            ))}
          </Select>
          <Select
            label={t('filters.owner')}
            value={filters.owner}
            onChange={(e) => patchFilters({ owner: e.target.value })}
          >
            <option value="">{t('filters.allOwners')}</option>
            {owners.map((owner) => (
              <option key={owner} value={owner}>
                {owner}
              </option>
            ))}
          </Select>
          <Input
            label={t('filters.dateFrom')}
            type="date"
            value={filters.dateFrom}
            onChange={(e) => patchFilters({ dateFrom: e.target.value })}
          />
          <Input
            label={t('filters.dateTo')}
            type="date"
            value={filters.dateTo}
            onChange={(e) => patchFilters({ dateTo: e.target.value })}
          />
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="documents-ds__reset-btn"
          onClick={() => {
            setSearchDraft('');
            setFilters(EMPTY_DOC_FILTERS);
            setPage(1);
          }}
        >
          {t('filters.reset')}
        </Button>
      </section>

      <div className="documents-ds__category-tabs" role="tablist" aria-label={t('tabs.aria')}>
        {DOC_CATEGORY_TABS.filter((tab) => tab === 'all' || countByTab(docs, tab) > 0).map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={
              filters.tab === tab && !filters.shortcut && !filters.folder && !filters.entityNav
            }
            className={`documents-ds__category-tab${
              filters.tab === tab && !filters.shortcut && !filters.folder && !filters.entityNav
                ? ' is-active'
                : ''
            }`}
            onClick={() => {
              clearNavContext();
              patchFilters({ tab });
            }}
            data-testid={`documents-ds-tab-${tab}`}
          >
            {t(`tabs.${tab}`)}
            <span className="documents-ds__tab-count">{countByTab(docs, tab)}</span>
          </button>
        ))}
      </div>

      <div className="documents-ds__workspace">
        <section className="documents-ds__panel documents-ds__panel--nav" aria-label={t('nav.aria')}>
          <div className="documents-ds__nav-scroll">
            <div className="documents-ds__nav-section">
              <p className="documents-ds__nav-section-title">{t('nav.shortcuts')}</p>
              {DOC_SHORTCUTS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={`documents-ds__nav-item${filters.shortcut === key ? ' is-active' : ''}`}
                  onClick={() =>
                    patchFilters({
                      shortcut: key,
                      folder: '',
                      entityNav: '',
                      tab: 'all',
                    })
                  }
                  data-testid={`documents-ds-shortcut-${key}`}
                >
                  <IhIcon
                    name={
                      key === 'trash'
                        ? 'alert'
                        : key === 'shared'
                          ? 'activity'
                          : key === 'frequent'
                            ? 'sparkles'
                            : key === 'mine'
                              ? 'user'
                              : 'clock'
                    }
                    size={13}
                  />
                  <span>{t(`shortcuts.${key}`)}</span>
                  <span>{countByShortcut(docs, key)}</span>
                </button>
              ))}
            </div>

            <div className="documents-ds__nav-section">
              <p className="documents-ds__nav-section-title">{t('nav.byEntity')}</p>
              {DOC_ENTITY_KINDS.map((kind) => (
                <button
                  key={kind}
                  type="button"
                  className={`documents-ds__nav-item${filters.entityNav === kind ? ' is-active' : ''}`}
                  onClick={() =>
                    patchFilters({
                      entityNav: kind,
                      shortcut: '',
                      folder: '',
                      tab: 'all',
                    })
                  }
                >
                  <IhIcon
                    name={
                      kind === 'project'
                        ? 'projects'
                        : kind === 'company'
                          ? 'investors'
                          : kind === 'investor'
                            ? 'trendingUp'
                            : 'target'
                    }
                    size={13}
                  />
                  <span>{t(`entities.${kind}`)}</span>
                  <span>{countByEntity(docs, kind)}</span>
                </button>
              ))}
            </div>

            <div className="documents-ds__nav-section">
              <p className="documents-ds__nav-section-title">{t('nav.folders')}</p>
              {DOC_FOLDERS.map((folder) => (
                <button
                  key={folder}
                  type="button"
                  className={`documents-ds__nav-item${filters.folder === folder ? ' is-active' : ''}`}
                  onClick={() =>
                    patchFilters({
                      folder,
                      shortcut: '',
                      entityNav: '',
                      tab: 'all',
                    })
                  }
                >
                  <IhIcon name="documents" size={13} />
                  <span>{t(`folders.${folder}`)}</span>
                  <span>{countByFolder(docs, folder)}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="documents-ds__storage">
            <div className="documents-ds__storage-head">
              <strong>{t('storage.title')}</strong>
              <button
                type="button"
                className="documents-ds__storage-link"
                onClick={() => showToast(t('toast.storage'))}
              >
                {t('storage.manage')}
              </button>
            </div>
            <div className="documents-ds__storage-bar" aria-hidden="true">
              <div className="documents-ds__storage-fill" style={{ width: `${storagePct}%` }} />
            </div>
            <div className="documents-ds__storage-meta">
              {t('storage.usage', { used: STORAGE_USED_GB, total: STORAGE_TOTAL_GB })}
            </div>
          </div>
        </section>

        <section
          className="documents-ds__panel documents-ds__panel--center"
          aria-label={t('center.aria')}
        >
          <div className="documents-ds__panel-head">
            <h2>
              {t('center.title')}
              <StatusChip tone="info">{filtered.length}</StatusChip>
            </h2>
            <div className="documents-ds__panel-head-actions">
              <SegmentedControl
                ariaLabel={t('center.viewAria')}
                value={filters.view}
                onChange={(next) => patchFilters({ view: next as DocViewMode })}
                options={[
                  { value: 'card', label: t('center.cardView') },
                  { value: 'list', label: t('center.listView') },
                ]}
              />
              <Select
                label={t('center.sort')}
                value={filters.sort}
                onChange={(e) => patchFilters({ sort: e.target.value as DocSortKey })}
                data-testid="documents-ds-sort"
              >
                {DOC_SORT_KEYS.map((key) => (
                  <option key={key} value={key}>
                    {t(`sort.${key}`)}
                  </option>
                ))}
              </Select>
              <div style={{ position: 'relative' }}>
                <button
                  type="button"
                  className="documents-ds__icon-btn"
                  aria-label={t('center.more')}
                  onClick={() => setMenuOpen((v) => !v)}
                >
                  <IhIcon name="chevronDown" size={13} />
                </button>
                {menuOpen ? (
                  <div
                    className="documents-ds__panel"
                    style={{
                      position: 'absolute',
                      right: 0,
                      top: '110%',
                      zIndex: 5,
                      minWidth: 160,
                      padding: 8,
                      gap: 4,
                    }}
                  >
                    <Button type="button" variant="secondary" size="sm" onClick={handleUploadClick}>
                      {t('actions.create')}
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setMenuOpen(false);
                        showToast(t('toast.export'));
                      }}
                    >
                      {t('center.export')}
                    </Button>
                  </div>
                ) : null}
              </div>
              <button
                type="button"
                className="documents-ds__info-toggle documents-ds__icon-btn"
                aria-label={t('preview.open')}
                onClick={() => setDrawerOpen(true)}
              >
                <IhIcon name="documents" size={13} />
              </button>
            </div>
          </div>

          <div className="documents-ds__center-body">
            {pageItems.length === 0 ? (
              <div className="documents-ds__empty">
                <IhIcon name="documents" size={22} />
                <strong>{t('center.emptyTitle')}</strong>
                <p>{t('center.emptyDescription')}</p>
                <Button type="button" variant="primary" size="sm" onClick={handleUploadClick}>
                  <IhIcon name="plus" size={13} />
                  {t('actions.create')}
                </Button>
              </div>
            ) : filters.view === 'card' ? (
              <div className="documents-ds__grid" data-testid="documents-ds-grid">
                {pageItems.map((doc) => (
                  <DocumentCard
                    key={doc.id}
                    doc={doc}
                    selected={selected?.id === doc.id}
                    onSelect={() => selectDoc(doc.id)}
                    onFavorite={() => toggleFavorite(doc.id)}
                    onPreview={() => {
                      selectDoc(doc.id);
                      setPreviewTab('preview');
                    }}
                    onDownload={() => {
                      setSelectedId(doc.id);
                      showToast(t('toast.download'));
                    }}
                    onShare={() => {
                      selectDoc(doc.id);
                      setPreviewTab('shares');
                      showToast(t('toast.share'));
                    }}
                  />
                ))}
              </div>
            ) : (
              <table className="documents-ds__list" data-testid="documents-ds-list">
                <thead>
                  <tr>
                    <th>{t('list.name')}</th>
                    <th>{t('list.folder')}</th>
                    <th>{t('list.related')}</th>
                    <th>{t('list.size')}</th>
                    <th>{t('list.date')}</th>
                    <th>{t('list.owner')}</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((doc) => (
                    <tr
                      key={doc.id}
                      className={selected?.id === doc.id ? 'is-selected' : undefined}
                      onClick={() => selectDoc(doc.id)}
                      data-testid={`documents-ds-row-${doc.id}`}
                    >
                      <td>
                        <div className="documents-ds__row-name">
                          <FileTypeIcon type={doc.fileType} size={13} />
                          <strong title={doc.name}>{doc.name}</strong>
                        </div>
                      </td>
                      <td>
                        <StatusChip tone={FOLDER_TONE[doc.folder]}>
                          {t(`folders.${doc.folder}`)}
                        </StatusChip>
                      </td>
                      <td>{doc.related[0]?.name ?? '—'}</td>
                      <td>{doc.sizeLabel}</td>
                      <td>{doc.uploadedAt}</td>
                      <td>{doc.owner}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="documents-ds__pagination" aria-label={t('pagination.aria')}>
            <span>
              {t('pagination.range', {
                from: filtered.length === 0 ? 0 : (pageSafe - 1) * PAGE_SIZE + 1,
                to: Math.min(pageSafe * PAGE_SIZE, filtered.length),
                total: filtered.length,
              })}
            </span>
            <div className="documents-ds__pagination-pages">
              <button
                type="button"
                className="documents-ds__page-btn"
                disabled={pageSafe <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                aria-label={t('pagination.prev')}
              >
                <IhIcon name="chevronLeft" size={12} />
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .slice(0, 8)
                .map((n) => (
                  <button
                    key={n}
                    type="button"
                    className={`documents-ds__page-btn${n === pageSafe ? ' is-active' : ''}`}
                    onClick={() => setPage(n)}
                  >
                    {n}
                  </button>
                ))}
              <button
                type="button"
                className="documents-ds__page-btn"
                disabled={pageSafe >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                aria-label={t('pagination.next')}
              >
                <IhIcon name="chevronRight" size={12} />
              </button>
            </div>
          </div>
        </section>

        <section
          className="documents-ds__panel documents-ds__panel--preview"
          aria-label={t('preview.aria')}
          data-testid="documents-ds-preview"
        >
          <PreviewPanel
            doc={selected}
            tab={previewTab}
            onTabChange={setPreviewTab}
            onFavorite={() => selected && toggleFavorite(selected.id)}
            onAction={handleAction}
          />
        </section>
      </div>

      <div
        className={`documents-ds__drawer${drawerOpen ? ' is-open' : ''}`}
        hidden={!drawerOpen}
        onClick={(e) => {
          if (e.target === e.currentTarget) setDrawerOpen(false);
        }}
      >
        <section
          className="documents-ds__panel documents-ds__panel--preview"
          aria-label={t('preview.aria')}
        >
          <PreviewPanel
            doc={selected}
            tab={previewTab}
            onTabChange={setPreviewTab}
            onClose={() => setDrawerOpen(false)}
            onFavorite={() => selected && toggleFavorite(selected.id)}
            onAction={handleAction}
            showClose
          />
        </section>
      </div>

      {toast ? (
        <div className="documents-ds__toast" role="status" data-testid="documents-ds-toast">
          {toast}
        </div>
      ) : null}
    </div>
  );
}
