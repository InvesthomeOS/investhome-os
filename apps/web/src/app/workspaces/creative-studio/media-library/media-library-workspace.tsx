'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, useState, type MouseEvent } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Card, StatusChip, TextArea } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import { CsBottomActionToolbar } from '../_components';
import {
  CreativeStudioFocusWorkspace,
  FocusActionDock,
  useCreativeStudioFocusMode,
  type FocusRailItem,
} from '../_components/focus-workspace';

import {
  BOTTOM_ACTIONS,
  CENTER_TABS,
  DEMO_ASSETS,
  DETAIL_TABS,
  FOLDERS,
  ML_HOME,
  QUICK_ACTIONS,
  SIDEBAR_TYPES,
  STORAGE,
  TOTAL_ASSET_COUNT,
  docIcon,
  filterAssets,
  sortAssets,
  type BottomActionKey,
  type CenterTabId,
  type DetailTabId,
  type MediaAsset,
  type QuickActionId,
  type SidebarTypeId,
  type SizePreset,
  type SortKey,
  type ViewMode,
} from './media-library-model';

import './media-library.css';

export function MediaLibraryWorkspace() {
  const t = useTranslations('creativeStudio.ds.mediaLibrary');
  const tTools = useTranslations('creativeStudio.ds.tools');
  const tFocus = useTranslations('creativeStudio.focusWorkspace');

  const focus = useCreativeStudioFocusMode({
    storageKey: 'media-library',
    defaultMode: 'normal',
    persist: false,
  });

  const [assets, setAssets] = useState<MediaAsset[]>(DEMO_ASSETS);
  const [sidebar, setSidebar] = useState<SidebarTypeId>('all');
  const [folderId, setFolderId] = useState<string | null>(null);
  const [centerTab, setCenterTab] = useState<CenterTabId>('all');
  const [detailTab, setDetailTab] = useState<DetailTabId>('details');
  const [selectedId, setSelectedId] = useState<string>(DEMO_ASSETS[0]!.id);
  const [selectedSet, setSelectedSet] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [sort, setSort] = useState<SortKey>('newest');
  const [size, setSize] = useState<SizePreset>('medium');
  const [saved, setSaved] = useState(true);
  const [toast, setToast] = useState<string | null>(null);
  const [activeQuick, setActiveQuick] = useState<QuickActionId | null>('info');
  const [showAllFolders, setShowAllFolders] = useState(false);
  const [dockOverflowOpen, setDockOverflowOpen] = useState(false);

  const filtered = useMemo(
    () =>
      sortAssets(
        filterAssets(assets, { sidebar, tab: centerTab, folderId, query }),
        sort,
      ),
    [assets, sidebar, centerTab, folderId, query, sort],
  );

  const selected = useMemo(
    () => assets.find((a) => a.id === selectedId) ?? filtered[0] ?? assets[0] ?? null,
    [assets, filtered, selectedId],
  );

  const visibleFolders = showAllFolders ? FOLDERS : FOLDERS.slice(0, 4);

  const mlRightRail: FocusRailItem[] = useMemo(
    () =>
      QUICK_ACTIONS.map((action) => ({
        id: action.id,
        icon: action.icon,
        labelKey: 'quickActions',
        label: t(`rail.actions.${action.id}`),
      })),
    [t],
  );

  const mlLeftRail: FocusRailItem[] = useMemo(
    () => [
      { id: 'library', icon: 'inventory', labelKey: 'assets', label: tTools('mediaLibrary.title') },
      { id: 'folders', icon: 'projects', labelKey: 'brief', label: t('left.folders') },
    ],
    [t, tTools],
  );

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 2200);
  }

  function markDirty() {
    setSaved(false);
  }

  function persist() {
    setSaved(true);
    showToast(t('toasts.saved'));
  }

  function selectAsset(id: string) {
    setSelectedId(id);
    setActiveQuick('info');
    setDetailTab('details');
  }

  function toggleFavorite(id: string, event: MouseEvent) {
    event.stopPropagation();
    setAssets((prev) =>
      prev.map((a) => (a.id === id ? { ...a, favorite: !a.favorite } : a)),
    );
    markDirty();
    showToast(t('toasts.favorite'));
  }

  function toggleSelectHandle(id: string, event: MouseEvent) {
    event.stopPropagation();
    setSelectedSet((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function patchSelected(patch: Partial<MediaAsset>) {
    if (!selected) return;
    setAssets((prev) => prev.map((a) => (a.id === selected.id ? { ...a, ...patch } : a)));
    markDirty();
  }

  function handleQuick(action: QuickActionId) {
    setActiveQuick(action);
    if (action === 'info') {
      setDetailTab('details');
      return;
    }
    if (action === 'tag') {
      setDetailTab('tags');
      return;
    }
    if (action === 'link') {
      showToast(t('toasts.linkCopied'));
      return;
    }
    if (action === 'share') {
      showToast(t('toasts.shared'));
      return;
    }
    if (action === 'download') {
      showToast(t('toasts.downloaded'));
      return;
    }
    if (action === 'delete' && selected) {
      setAssets((prev) =>
        prev.map((a) => (a.id === selected.id ? { ...a, trashed: true } : a)),
      );
      markDirty();
      showToast(t('toasts.trashed'));
    }
  }

  function handleBottom(action: BottomActionKey) {
    showToast(t(`bottomBar.toasts.${action}`));
  }

  function handleNewFolder() {
    markDirty();
    showToast(t('toasts.folderCreated'));
  }

  function handleUpload() {
    markDirty();
    showToast(t('toasts.uploaded'));
  }

  function handleCreate() {
    showToast(t('toasts.create'));
  }

  function handleRefresh() {
    showToast(t('toasts.refreshed'));
  }

  const displayCount =
    sidebar === 'all' && !folderId && !query.trim() && centerTab === 'all'
      ? TOTAL_ASSET_COUNT
      : filtered.length;

  const showInlineRail = focus.mode === 'normal' && !focus.isFullscreen;

  const leftPanel = (
    <aside className="ml-ws__left" aria-label={t('left.aria')} data-testid="ml-left">
      <div className="ml-ws__nav-section">
        <div className="ml-ws__nav-section-head">{t('left.assetTypes')}</div>
        {SIDEBAR_TYPES.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`ml-ws__nav-item${sidebar === item.id ? ' is-active' : ''}`}
            onClick={() => {
              setSidebar(item.id);
              setFolderId(null);
            }}
            data-testid={`ml-type-${item.id}`}
          >
            <span className="ml-ws__nav-item-icon">
              <IhIcon name={item.icon} size={13} />
            </span>
            {t(`left.types.${item.id}`)}
          </button>
        ))}
      </div>

      <div className="ml-ws__nav-section">
        <div className="ml-ws__nav-section-head">
          <span>{t('left.folders')}</span>
          <button
            type="button"
            className="ml-ws__icon-btn"
            onClick={handleNewFolder}
            aria-label={t('actions.newFolder')}
            data-testid="ml-folder-add"
          >
            <IhIcon name="plus" size={12} />
          </button>
        </div>
        {visibleFolders.map((folder) => (
          <div key={folder.id}>
            <button
              type="button"
              className={`ml-ws__nav-item${folderId === folder.id ? ' is-active' : ''}`}
              onClick={() => {
                setFolderId(folder.id);
                setSidebar('all');
              }}
              data-testid={`ml-folder-${folder.id}`}
            >
              <span className="ml-ws__nav-item-icon">
                <IhIcon name="projects" size={13} />
              </span>
              <span className="ml-ws__folder-name">{folder.name}</span>
              <span className="ml-ws__folder-count">
                {t('left.fileCount', { count: folder.count })}
              </span>
            </button>
            {folder.children?.map((child) => (
              <button
                key={child.id}
                type="button"
                className={`ml-ws__nav-item ml-ws__folder-child${folderId === child.id ? ' is-active' : ''}`}
                onClick={() => {
                  setFolderId(child.id);
                  setSidebar('all');
                }}
              >
                <span className="ml-ws__nav-item-icon">
                  <IhIcon name="documents" size={12} />
                </span>
                {child.name}
                <span className="ml-ws__folder-count">{child.count}</span>
              </button>
            ))}
          </div>
        ))}
        <button
          type="button"
          className="ml-ws__show-all"
          onClick={() => setShowAllFolders((v) => !v)}
          data-testid="ml-show-all-folders"
        >
          {showAllFolders ? t('left.showLess') : t('left.showAll')}
          <IhIcon name="chevronRight" size={11} />
        </button>
      </div>
    </aside>
  );

  const centerPanel = (
    <section className="ml-ws__center" aria-label={t('center.aria')} data-testid="ml-center">
      <div className="ml-ws__center-head">
        <h2>{t('center.title', { count: displayCount.toLocaleString('tr-TR') })}</h2>
      </div>
      <div className="ml-ws__tabs" role="tablist" aria-label={t('center.tabsAria')}>
        {CENTER_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={centerTab === tab.id}
            className={`ml-ws__tab${centerTab === tab.id ? ' is-active' : ''}`}
            onClick={() => setCenterTab(tab.id)}
            data-testid={`ml-tab-${tab.id}`}
          >
            <IhIcon name={tab.icon} size={12} />
            {t(`center.tabs.${tab.id}`)}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="ml-ws__empty" data-testid="ml-empty">
          <IhIcon name="empty" size={28} />
          <p>{t('center.empty')}</p>
        </div>
      ) : (
        <div
          className={`ml-ws__grid${viewMode === 'list' ? ' is-list' : ''}`}
          data-size={size}
          data-testid="ml-grid"
        >
          {filtered.map((asset) => (
            <article
              key={asset.id}
              className={`ml-ws__card${selected?.id === asset.id ? ' is-selected' : ''}${selectedSet.has(asset.id) ? ' is-checked' : ''}`}
              onClick={() => selectAsset(asset.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  selectAsset(asset.id);
                }
              }}
              role="button"
              tabIndex={0}
              data-testid={`ml-card-${asset.id}`}
            >
              <div className="ml-ws__thumb">
                {asset.thumbUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={asset.thumbUrl} alt="" />
                ) : (
                  <div className="ml-ws__thumb-doc">
                    <IhIcon name={docIcon(asset.ext)} size={28} />
                  </div>
                )}
                <span className="ml-ws__badge">{asset.ext}</span>
                {asset.kind === 'video' ? (
                  <>
                    <div className="ml-ws__play" aria-hidden="true">
                      <span className="ml-ws__play-circle">
                        <IhIcon name="meeting" size={14} />
                      </span>
                    </div>
                    {asset.duration ? (
                      <span className="ml-ws__duration">{asset.duration}</span>
                    ) : null}
                  </>
                ) : null}
                <button
                  type="button"
                  className={`ml-ws__fav${asset.favorite ? ' is-on' : ''}`}
                  onClick={(e) => toggleFavorite(asset.id, e)}
                  aria-label={t('card.favorite')}
                  data-testid={`ml-fav-${asset.id}`}
                >
                  <IhIcon name="check" size={11} />
                </button>
                <button
                  type="button"
                  className="ml-ws__select-handle"
                  onClick={(e) => toggleSelectHandle(asset.id, e)}
                  aria-label={t('card.select')}
                  aria-pressed={selectedSet.has(asset.id)}
                  data-testid={`ml-select-${asset.id}`}
                >
                  <IhIcon name="plus" size={11} />
                </button>
              </div>
              <div className="ml-ws__card-meta">
                <div className="ml-ws__card-name-row">
                  <span className="ml-ws__card-name" title={asset.name}>
                    {asset.name}
                  </span>
                  <button
                    type="button"
                    className="ml-ws__card-more"
                    onClick={(e) => {
                      e.stopPropagation();
                      selectAsset(asset.id);
                      showToast(t('toasts.menu'));
                    }}
                    aria-label={t('card.more')}
                  >
                    <IhIcon name="quickAction" size={12} />
                  </button>
                </div>
                <div className="ml-ws__card-sub">
                  {asset.sizeLabel}
                  {asset.resolution ? ` · ${asset.resolution}` : null}
                  {asset.duration && asset.kind !== 'video' ? ` · ${asset.duration}` : null}
                  {` · ${asset.dateLabel}`}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );

  function renderDetailBody() {
    if (!selected) {
      return <p className="ml-ws__detail-empty">{t('right.empty')}</p>;
    }

    if (detailTab === 'tags') {
      return (
        <div>
          <p className="ml-ws__block-label">{t('right.tags')}</p>
          <div className="ml-ws__tags">
            {selected.tags.map((tag) => (
              <StatusChip key={tag} tone="info">
                {tag}
              </StatusChip>
            ))}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => showToast(t('toasts.addTag'))}
              aria-label={t('right.addTag')}
              data-testid="ml-tag-add"
            >
              <IhIcon name="plus" size={11} />
            </Button>
          </div>
        </div>
      );
    }

    if (detailTab === 'history') {
      return (
        <ul className="ml-ws__history-list">
          {selected.history.map((h) => (
            <li key={h.id}>
              <Card title={h.action}>
                <p className="ml-ws__history-meta">
                  {h.actor} · {h.at}
                </p>
              </Card>
            </li>
          ))}
        </ul>
      );
    }

    if (detailTab === 'usage') {
      return (
        <ul className="ml-ws__usage-list">
          {selected.usages.length === 0 ? (
            <li className="ml-ws__detail-empty">{t('right.noUsage')}</li>
          ) : (
            selected.usages.map((u) => (
              <li key={u.id}>
                <Card title={u.tool}>
                  <div className="ml-ws__usage-card-body">
                    <span className="ml-ws__usage-icon">
                      <IhIcon name={u.icon} size={14} />
                    </span>
                    <span>{u.label}</span>
                  </div>
                </Card>
              </li>
            ))
          )}
        </ul>
      );
    }

    return (
      <>
        <div className="ml-ws__preview-card">
          <div className="ml-ws__preview">
            {selected.thumbUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={selected.thumbUrl} alt="" />
            ) : (
              <div className="ml-ws__preview-doc">
                <IhIcon name={docIcon(selected.ext)} size={40} />
              </div>
            )}
            <span className="ml-ws__preview-badge">{selected.ext}</span>
          </div>
          <dl className="ml-ws__meta-list">
            <div>
              <dt>{t('right.meta.fileName')}</dt>
              <dd>{selected.name}</dd>
            </div>
            <div>
              <dt>{t('right.meta.kind')}</dt>
              <dd>
                {t(`kinds.${selected.kind}`)} ({selected.ext})
              </dd>
            </div>
            {selected.resolution ? (
              <div>
                <dt>{t('right.meta.size')}</dt>
                <dd>{selected.resolution}</dd>
              </div>
            ) : null}
            {selected.resolution ? (
              <div>
                <dt>{t('right.meta.resolution')}</dt>
                <dd>{selected.resolution}</dd>
              </div>
            ) : null}
            <div>
              <dt>{t('right.meta.fileSize')}</dt>
              <dd>{selected.sizeLabel}</dd>
            </div>
            {selected.duration ? (
              <div>
                <dt>{t('right.meta.duration')}</dt>
                <dd>{selected.duration}</dd>
              </div>
            ) : null}
            <div>
              <dt>{t('right.meta.added')}</dt>
              <dd>{selected.addedAt}</dd>
            </div>
            <div>
              <dt>{t('right.meta.addedBy')}</dt>
              <dd>{selected.addedBy}</dd>
            </div>
            <div>
              <dt>{t('right.meta.folder')}</dt>
              <dd>{selected.folderName}</dd>
            </div>
          </dl>
        </div>

        <div className="ml-ws__desc-block">
          <TextArea
            label={t('right.description')}
            value={selected.description}
            onChange={(e) => patchSelected({ description: e.target.value })}
            data-testid="ml-description"
            rows={4}
          />
        </div>

        <div className="ml-ws__tags-block">
          <p className="ml-ws__block-label">{t('right.tags')}</p>
          <div className="ml-ws__tags">
            {selected.tags.map((tag) => (
              <StatusChip key={tag} tone="info">
                {tag}
              </StatusChip>
            ))}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setDetailTab('tags');
                showToast(t('toasts.addTag'));
              }}
              aria-label={t('right.addTag')}
            >
              <IhIcon name="plus" size={11} />
            </Button>
          </div>
        </div>

        <div className="ml-ws__usage-block">
          <p className="ml-ws__block-label">{t('right.inUse')}</p>
          {selected.usages.length === 0 ? (
            <p className="ml-ws__detail-empty">{t('right.noUsage')}</p>
          ) : (
            <ul className="ml-ws__usage-list">
              {selected.usages.map((u) => (
                <li key={u.id}>
                  <Card title={u.tool}>
                    <div className="ml-ws__usage-card-body">
                      <span className="ml-ws__usage-icon">
                        <IhIcon name={u.icon} size={14} />
                      </span>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => showToast(u.label)}
                      >
                        {u.label}
                      </Button>
                    </div>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </div>
      </>
    );
  }

  const rightDetail = (
    <aside className="ml-ws__right" aria-label={t('right.aria')} data-testid="ml-right">
      <div className="ml-ws__detail-tabs" role="tablist">
        {DETAIL_TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={detailTab === tab}
            className={`ml-ws__detail-tab${detailTab === tab ? ' is-active' : ''}`}
            onClick={() => setDetailTab(tab)}
            data-testid={`ml-detail-tab-${tab}`}
          >
            {t(`right.tabs.${tab}`)}
          </button>
        ))}
      </div>
      <div className="ml-ws__detail-body">{renderDetailBody()}</div>
    </aside>
  );

  /** Shared FocusRail markup/classes (cs-fw__rail) — normal mode only; focus mode uses framework rail. */
  const inlineRightRail = showInlineRail ? (
    <nav
      className="cs-fw__rail cs-fw__rail--right"
      data-testid="ml-rail"
      aria-label={t('rail.aria')}
    >
      {mlRightRail.map((item) => {
        const isActive = activeQuick === item.id;
        return (
          <button
            key={item.id}
            type="button"
            className={['cs-fw__rail-btn', isActive ? 'is-active' : '']
              .filter(Boolean)
              .join(' ')}
            data-testid={`ml-rail-${item.id}`}
            title={item.label ?? tFocus(`rails.${item.labelKey}`)}
            aria-label={item.label ?? tFocus(`rails.${item.labelKey}`)}
            aria-pressed={isActive}
            onClick={() => handleQuick(item.id as QuickActionId)}
          >
            <IhIcon name={item.icon} size={16} />
          </button>
        );
      })}
    </nav>
  ) : null;

  const rightPanel = showInlineRail ? (
    <div className="ml-ws__right-shell">
      {rightDetail}
      {inlineRightRail}
    </div>
  ) : (
    rightDetail
  );

  const bottomActionToolbar = (
    <CsBottomActionToolbar
      testId="ml-bat"
      primary={{
        label: t('bottomBar.actions.addComponent'),
        icon: 'plus',
        onClick: () => handleBottom('addComponent'),
        testId: 'ml-action-addComponent',
      }}
      actions={BOTTOM_ACTIONS.filter((a) => a.key !== 'addComponent').map((action) => ({
        key: action.key,
        icon: action.icon,
        label: t(`bottomBar.actions.${action.key}`),
        onClick: () => handleBottom(action.key),
        testId: `ml-action-${action.key}`,
      }))}
    />
  );

  return (
    <main className="dashboard" data-testid="media-library-page">
      <div className="ml-ws" data-testid="ml-workspace">
        <header className="ml-ws__header cs-page-header">
          <div>
            <Link href={ML_HOME as Route} className="ml-ws__back">
              <IhIcon name="chevronLeft" size={12} />
              {t('back')}
            </Link>
            <nav aria-label={t('breadcrumbAria')}>
              <ol className="ml-ws__breadcrumb">
                <li>
                  <Link href={ML_HOME as Route}>{t('creativeStudio')}</Link>
                </li>
                <li className="ml-ws__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="ml-ws__breadcrumb-current" aria-current="page">
                  {tTools('mediaLibrary.title')}
                </li>
              </ol>
            </nav>
            <h1>
              <span className="ml-ws__title-icon" aria-hidden="true">
                <IhIcon name="inventory" size={22} />
              </span>
              {tTools('mediaLibrary.title')}
            </h1>
            <p className="ml-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
          </div>
          <div className="ml-ws__header-right">
            <div className="ml-ws__saved-meta">
              <StatusChip tone={saved ? 'success' : 'warning'}>
                {saved ? t('saved') : t('draft')}
              </StatusChip>
              <span className="ml-ws__saved-ago">
                {saved ? t('savedAgo') : t('notSavedYet')}
              </span>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleNewFolder}
              data-testid="ml-new-folder"
            >
              <IhIcon name="plus" size={12} />
              {t('actions.newFolder')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleUpload}
              data-testid="ml-upload"
            >
              <IhIcon name="inbox" size={12} />
              {t('actions.upload')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
            <Button
              variant="primary"
              size="sm"
              className="ml-ws__create-btn"
              onClick={handleCreate}
              data-testid="ml-create"
            >
              <IhIcon name="sparkles" size={12} />
              {t('actions.create')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
            {!saved ? (
              <Button variant="secondary" size="sm" onClick={persist} data-testid="ml-save">
                {t('actions.save')}
              </Button>
            ) : null}
          </div>
        </header>

        <div className="ml-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
          <div
            className="ml-ws__storage"
            data-testid="ml-storage"
            style={{ ['--ml-storage-pct' as string]: `${STORAGE.percent}%` }}
          >
            <span className="ml-ws__storage-label">{t('storage.label')}</span>
            <span className="ml-ws__storage-value">
              {t('storage.value', { used: STORAGE.usedGb, total: STORAGE.totalGb })}
            </span>
            <div
              className="ml-ws__storage-bar"
              role="progressbar"
              aria-valuenow={STORAGE.percent}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <span />
            </div>
          </div>

          <label className="ml-ws__search">
            <IhIcon name="search" size={14} />
            <span className="sr-only">{t('searchLabel')}</span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('searchPlaceholder')}
              data-testid="ml-search"
            />
          </label>

          <div className="ml-ws__toolbar-controls">
            <Button variant="secondary" size="sm" data-testid="ml-filter">
              <IhIcon name="activity" size={12} />
              {t('actions.filter')}
            </Button>
            <div className="ml-ws__view-toggle" role="group" aria-label={t('viewAria')}>
              <button
                type="button"
                className={viewMode === 'grid' ? 'is-active' : undefined}
                aria-pressed={viewMode === 'grid'}
                onClick={() => setViewMode('grid')}
                data-testid="ml-view-grid"
                title={t('view.grid')}
              >
                <IhIcon name="executive" size={12} />
              </button>
              <button
                type="button"
                className={viewMode === 'list' ? 'is-active' : undefined}
                aria-pressed={viewMode === 'list'}
                onClick={() => setViewMode('list')}
                data-testid="ml-view-list"
                title={t('view.list')}
              >
                <IhIcon name="documents" size={12} />
              </button>
            </div>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              aria-label={t('sortAria')}
              data-testid="ml-sort"
            >
              <option value="newest">{t('sort.newest')}</option>
              <option value="oldest">{t('sort.oldest')}</option>
              <option value="nameAsc">{t('sort.nameAsc')}</option>
              <option value="sizeDesc">{t('sort.sizeDesc')}</option>
            </select>
            <select
              value={size}
              onChange={(e) => setSize(e.target.value as SizePreset)}
              aria-label={t('sizeAria')}
              data-testid="ml-size"
            >
              <option value="small">{t('size.small')}</option>
              <option value="medium">{t('size.medium')}</option>
              <option value="large">{t('size.large')}</option>
            </select>
            <button
              type="button"
              className="ml-ws__icon-btn"
              onClick={handleRefresh}
              aria-label={t('actions.refresh')}
              data-testid="ml-refresh"
            >
              <IhIcon name="refresh" size={13} />
            </button>
          </div>
        </div>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="ml-ws__layout"
          leftRail={mlLeftRail}
          rightRail={mlRightRail}
          onRightRailSelect={(id) => {
            if ((QUICK_ACTIONS.map((a) => a.id) as string[]).includes(id)) {
              handleQuick(id as QuickActionId);
            }
          }}
          left={leftPanel}
          center={centerPanel}
          right={rightPanel}
        />

        <FocusActionDock
          primary={bottomActionToolbar}
          visible
          pinned
          overflowOpen={dockOverflowOpen}
          onOverflowOpenChange={setDockOverflowOpen}
          testId="ml-dock"
        />

        {toast ? (
          <div className="ml-ws__toast" role="status" data-testid="ml-toast">
            {toast}
          </div>
        ) : null}
      </div>
    </main>
  );
}
