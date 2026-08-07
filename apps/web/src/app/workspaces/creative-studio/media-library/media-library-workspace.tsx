'use client';

import type { Route } from 'next';
import Link from 'next/link';
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
  type MouseEvent,
} from 'react';
import { useTranslations } from 'next-intl';

import { Button, Card, Dialog, StatusChip, TextArea } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { getCreativeStudioMediaContentUrl } from '@/lib/api/creative-studio';

import { CsBottomActionToolbar } from '../_components';
import {
  CreativeStudioFocusWorkspace,
  FocusActionDock,
  useCreativeStudioFocusMode,
  type FocusRailItem,
} from '../_components/focus-workspace';

import {
  isAllowedMediaUpload,
  isMediaAssetUuid,
  ML_UPLOAD_ACCEPT,
} from './media-library-api-map';
import {
  BOTTOM_ACTIONS,
  CENTER_TABS,
  DETAIL_TABS,
  FOLDERS,
  ML_HOME,
  QUICK_ACTIONS,
  SIDEBAR_TYPES,
  STORAGE,
  docIcon,
  filterAssets,
  isGoogleDriveAsset,
  isMissingDriveAsset,
  sortAssets,
  type BottomActionKey,
  type CenterTabId,
  type DetailTabId,
  type MediaAsset,
  type QuickActionId,
  type SidebarTypeId,
  type SizePreset,
  type SortKey,
  type SourceFilterId,
  type ViewMode,
} from './media-library-model';
import { MediaLibraryQuickTagPopover } from './media-library-quick-tag-popover';
import { MediaLibraryTagEditor } from './media-library-tag-editor';
import {
  collectLibraryTags,
  collectUnionTags,
  mergeTags,
  pushRecentTags,
  rangeSelectIds,
  readRecentTags,
  removeTags,
  uniqueTags,
} from './media-library-tag-utils';
import { useMediaLibrary } from './use-media-library';

import './media-library.css';

const SEARCH_DEBOUNCE_MS = 300;

type BulkTagMode = 'add' | 'remove' | null;
type ArchiveTarget =
  | { kind: 'single'; assetId: string; name: string }
  | { kind: 'bulk'; ids: string[] }
  | null;

export function MediaLibraryWorkspace() {
  const t = useTranslations('creativeStudio.ds.mediaLibrary');
  const tTools = useTranslations('creativeStudio.ds.tools');
  const tFocus = useTranslations('creativeStudio.focusWorkspace');

  const focus = useCreativeStudioFocusMode({
    storageKey: 'media-library',
    defaultMode: 'normal',
    persist: false,
  });

  const media = useMediaLibrary();
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const quickTagAnchorRef = useRef<HTMLButtonElement | null>(null);
  const lastRangeAnchorRef = useRef<string | null>(null);
  const cardMenuRef = useRef<HTMLDivElement | null>(null);

  const [sidebar, setSidebar] = useState<SidebarTypeId>('all');
  const [folderId, setFolderId] = useState<string | null>(null);
  const [centerTab, setCenterTab] = useState<CenterTabId>('all');
  const [detailTab, setDetailTab] = useState<DetailTabId>('details');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedSet, setSelectedSet] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [sort, setSort] = useState<SortKey>('newest');
  const [size, setSize] = useState<SizePreset>('medium');
  const [sourceFilter, setSourceFilter] = useState<SourceFilterId>('all');
  const [saved, setSaved] = useState(true);
  const [toast, setToast] = useState<string | null>(null);
  const [activeQuick, setActiveQuick] = useState<QuickActionId | null>('info');
  const [showAllFolders, setShowAllFolders] = useState(false);
  const [dockOverflowOpen, setDockOverflowOpen] = useState(false);
  const [dropActive, setDropActive] = useState(false);
  const [quickTagAssetId, setQuickTagAssetId] = useState<string | null>(null);
  const [quickTagError, setQuickTagError] = useState<string | null>(null);
  const [recentTags, setRecentTags] = useState<string[]>([]);
  const [bulkTagMode, setBulkTagMode] = useState<BulkTagMode>(null);
  const [bulkTagDraft, setBulkTagDraft] = useState<string[]>([]);
  const [bulkTagError, setBulkTagError] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [archiveTarget, setArchiveTarget] = useState<ArchiveTarget>(null);
  const [archiveBusy, setArchiveBusy] = useState(false);
  const [cardMenuId, setCardMenuId] = useState<string | null>(null);
  const [detailTagDraft, setDetailTagDraft] = useState<string[]>([]);
  const [detailTagOpen, setDetailTagOpen] = useState(false);
  const [detailTagError, setDetailTagError] = useState<string | null>(null);
  const skipServerFilterEffect = useRef(true);

  useEffect(() => {
    setRecentTags(readRecentTags());
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  // Demo folder ids (temple, social, …) must never be sent as API folder_id.
  const apiFolderId = folderId && isMediaAssetUuid(folderId) ? folderId : null;

  useEffect(() => {
    if (skipServerFilterEffect.current) {
      skipServerFilterEffect.current = false;
      return;
    }
    void media.refresh({
      query: debouncedQuery,
      folderId: apiFolderId,
      includeArchived: sidebar === 'trash',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- drive list from filter inputs only
  }, [debouncedQuery, apiFolderId, sidebar]);

  // Clear multi-select when list context changes (folder / search / sidebar / tab).
  useEffect(() => {
    setSelectedSet(new Set());
    lastRangeAnchorRef.current = null;
    setCardMenuId(null);
    setQuickTagAssetId(null);
  }, [debouncedQuery, apiFolderId, sidebar, centerTab, folderId, sourceFilter]);

  useEffect(() => {
    if (!media.usingSamples) {
      setFolderId((prev) => (prev && isMediaAssetUuid(prev) ? prev : null));
    }
  }, [media.usingSamples]);

  useEffect(() => {
    if (!media.assets.length) {
      setSelectedId(null);
      return;
    }
    setSelectedId((prev) => {
      if (prev && media.assets.some((a) => a.id === prev)) return prev;
      return media.assets[0]!.id;
    });
  }, [media.assets]);

  useEffect(() => {
    if (!cardMenuId) return;
    function onPointer(e: MouseEvent | globalThis.MouseEvent) {
      if (cardMenuRef.current?.contains(e.target as Node)) return;
      setCardMenuId(null);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setCardMenuId(null);
    }
    document.addEventListener('mousedown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [cardMenuId]);

  const libraryFolders = media.usingSamples ? FOLDERS : media.folders;

  const filtered = useMemo(() => {
    if (media.usingSamples) {
      return sortAssets(
        filterAssets(media.assets, {
          sidebar,
          tab: centerTab,
          folderId,
          query: debouncedQuery,
          sourceFilter,
        }),
        sort,
      );
    }
    return sortAssets(
      filterAssets(media.assets, {
        sidebar,
        tab: centerTab,
        folderId: null,
        query: '',
        sourceFilter,
      }),
      sort,
    );
  }, [
    media.assets,
    media.usingSamples,
    sidebar,
    centerTab,
    folderId,
    debouncedQuery,
    sort,
    sourceFilter,
  ]);

  const orderedIds = useMemo(() => filtered.map((a) => a.id), [filtered]);

  const selected = useMemo(
    () =>
      filtered.find((a) => a.id === selectedId) ??
      media.assets.find((a) => a.id === selectedId) ??
      filtered[0] ??
      null,
    [filtered, media.assets, selectedId],
  );

  const selectedPreviewUrl = useMemo(() => {
    if (!selected) return null;
    if (selected.thumbUrl) return selected.thumbUrl;
    if (isMediaAssetUuid(selected.id)) return media.displayUrls[selected.id] ?? null;
    return null;
  }, [selected, media.displayUrls]);

  useEffect(() => {
    if (!selected || !isMediaAssetUuid(selected.id)) return;
    if (selected.kind !== 'image') return;
    void media.ensureDisplayUrl(selected.id);
  }, [selected, media]);

  useEffect(() => {
    if (!selected || detailTagOpen) return;
    setDetailTagDraft(uniqueTags(selected.tags));
  }, [selected, detailTagOpen]);

  const libraryTags = useMemo(() => collectLibraryTags(media.assets), [media.assets]);

  const quickTagAsset = useMemo(
    () => (quickTagAssetId ? media.assets.find((a) => a.id === quickTagAssetId) ?? null : null),
    [media.assets, quickTagAssetId],
  );

  const selectedCount = selectedSet.size;
  const bulkAssets = useMemo(
    () => filtered.filter((a) => selectedSet.has(a.id)),
    [filtered, selectedSet],
  );

  const tagEditorLabels = useMemo(
    () => ({
      searchPlaceholder: t('tags.searchPlaceholder'),
      createLabel: t('tags.create'),
      createWithName: (name: string) => t('tags.createWithName', { name }),
      selectedLabel: t('tags.selected'),
      suggestionsLabel: t('tags.suggestions'),
      recentLabel: t('tags.recent'),
      emptySuggestions: t('tags.emptySuggestions'),
      removeTag: t('tags.remove'),
      apply: t('tags.apply'),
      cancel: t('tags.cancel'),
      applying: t('tags.applying'),
    }),
    [t],
  );

  const visibleFolders = showAllFolders ? libraryFolders : libraryFolders.slice(0, 4);

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

  function clearSelection() {
    setSelectedSet(new Set());
    lastRangeAnchorRef.current = null;
  }

  function selectAsset(id: string) {
    setSelectedId(id);
    setActiveQuick('info');
    setDetailTab('details');
    setCardMenuId(null);
  }

  function toggleFavorite(_id: string, event: MouseEvent) {
    event.stopPropagation();
    showToast(t('toasts.favoriteUnavailable'));
  }

  function toggleCheck(id: string, event: MouseEvent) {
    event.stopPropagation();
    const shift = event.shiftKey;
    setSelectedSet((prev) => {
      const next = new Set(prev);
      if (shift && lastRangeAnchorRef.current) {
        for (const rangeId of rangeSelectIds(orderedIds, lastRangeAnchorRef.current, id)) {
          next.add(rangeId);
        }
      } else if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
    lastRangeAnchorRef.current = id;
  }

  function openQuickTag(asset: MediaAsset, event: MouseEvent<HTMLButtonElement>) {
    event.stopPropagation();
    if (!isMediaAssetUuid(asset.id)) {
      showToast(t('toasts.samplesOnly'));
      return;
    }
    if (sidebar === 'trash') {
      showToast(t('toasts.trashReadOnly'));
      return;
    }
    quickTagAnchorRef.current = event.currentTarget;
    setQuickTagError(null);
    setQuickTagAssetId(asset.id);
    setSelectedId(asset.id);
  }

  async function applyQuickTag(assetId: string, tags: string[]): Promise<boolean> {
    const updated = await media.updateTags(assetId, tags);
    if (!updated) {
      setQuickTagError(t('toasts.tagFailed'));
      showToast(t('toasts.tagFailed'));
      return false;
    }
    markDirty();
    showToast(t('toasts.tagsUpdated'));
    return true;
  }

  async function applyDetailTags() {
    if (!selected || !isMediaAssetUuid(selected.id)) {
      showToast(t('toasts.samplesOnly'));
      return;
    }
    setDetailTagError(null);
    const updated = await media.updateTags(selected.id, uniqueTags(detailTagDraft));
    if (!updated) {
      setDetailTagError(t('toasts.tagFailed'));
      showToast(t('toasts.tagFailed'));
      return;
    }
    setRecentTags(pushRecentTags(detailTagDraft));
    setDetailTagOpen(false);
    markDirty();
    showToast(t('toasts.tagsUpdated'));
  }

  function openBulkTag(mode: 'add' | 'remove') {
    if (!selectedCount) return;
    if (sidebar === 'trash') {
      showToast(t('toasts.trashReadOnly'));
      return;
    }
    setBulkTagError(null);
    setBulkTagDraft(mode === 'remove' ? collectUnionTags(bulkAssets) : []);
    setBulkTagMode(mode);
  }

  async function applyBulkTags() {
    if (!bulkTagMode || !bulkAssets.length) return;
    const tags = uniqueTags(bulkTagDraft);
    if (!tags.length) {
      setBulkTagError(t('tags.emptySelection'));
      return;
    }
    setBulkBusy(true);
    setBulkTagError(null);
    let failed = 0;
    for (const asset of bulkAssets) {
      if (!isMediaAssetUuid(asset.id)) {
        failed += 1;
        continue;
      }
      const next =
        bulkTagMode === 'add' ? mergeTags(asset.tags, tags) : removeTags(asset.tags, tags);
      const updated = await media.updateTags(asset.id, next);
      if (!updated) failed += 1;
    }
    setBulkBusy(false);
    if (failed) {
      setBulkTagError(t('toasts.tagFailed'));
      showToast(t('toasts.tagFailed'));
      return;
    }
    setRecentTags(pushRecentTags(tags));
    setBulkTagMode(null);
    markDirty();
    showToast(
      bulkTagMode === 'add' ? t('toasts.bulkTagsAdded') : t('toasts.bulkTagsRemoved'),
    );
  }

  function requestArchiveSingle(asset: MediaAsset) {
    if (!isMediaAssetUuid(asset.id)) {
      showToast(t('toasts.samplesOnly'));
      return;
    }
    if (sidebar === 'trash') {
      showToast(t('toasts.trashReadOnly'));
      return;
    }
    setCardMenuId(null);
    setArchiveTarget({ kind: 'single', assetId: asset.id, name: asset.name });
  }

  function requestArchiveBulk() {
    const ids = [...selectedSet].filter((id) => isMediaAssetUuid(id));
    if (!ids.length) {
      showToast(t('toasts.samplesOnly'));
      return;
    }
    setArchiveTarget({ kind: 'bulk', ids });
  }

  async function confirmArchive() {
    if (!archiveTarget) return;
    setArchiveBusy(true);
    const ids =
      archiveTarget.kind === 'single' ? [archiveTarget.assetId] : archiveTarget.ids;
    let failed = 0;
    for (const id of ids) {
      const archived = await media.archiveAsset(id);
      if (!archived) failed += 1;
    }
    setArchiveBusy(false);
    setArchiveTarget(null);
    if (failed) {
      showToast(t('toasts.archiveFailed'));
      return;
    }
    setSelectedSet((prev) => {
      const next = new Set(prev);
      for (const id of ids) next.delete(id);
      return next;
    });
    markDirty();
    showToast(ids.length > 1 ? t('toasts.bulkArchived', { count: ids.length }) : t('toasts.trashed'));
  }

  async function handleQuick(action: QuickActionId) {
    setActiveQuick(action);
    if (action === 'info') {
      setDetailTab('details');
      return;
    }
    if (action === 'tag') {
      setDetailTab('tags');
      setDetailTagOpen(true);
      return;
    }
    if (action === 'link') {
      if (selected && isMediaAssetUuid(selected.id)) {
        try {
          await navigator.clipboard.writeText(getCreativeStudioMediaContentUrl(selected.id));
        } catch {
          // ignore clipboard failures
        }
      }
      showToast(t('toasts.linkCopied'));
      return;
    }
    if (action === 'share') {
      showToast(t('toasts.shared'));
      return;
    }
    if (action === 'download') {
      if (!selected) return;
      if (!isMediaAssetUuid(selected.id)) {
        showToast(t('toasts.samplesOnly'));
        return;
      }
      const ok = await media.downloadAsset(selected.id, selected.name);
      showToast(ok ? t('toasts.downloaded') : t('toasts.downloadFailed'));
      return;
    }
    if (action === 'delete' && selected) {
      requestArchiveSingle(selected);
    }
  }

  function handleBottom(action: BottomActionKey) {
    showToast(t(`bottomBar.toasts.${action}`));
  }

  async function handleNewFolder() {
    const name = window.prompt(t('toasts.folderNamePrompt'));
    if (name == null) return;
    const trimmed = name.trim();
    if (!trimmed) return;
    const folder = await media.createFolder(trimmed);
    if (!folder) {
      showToast(t('toasts.folderCreateFailed'));
      return;
    }
    markDirty();
    showToast(t('toasts.folderCreated'));
  }

  function openUploadPicker() {
    if (media.uploading) return;
    uploadInputRef.current?.click();
  }

  async function handleUploadFiles(files: FileList | File[] | null) {
    if (!files || media.uploading) return;
    const list = Array.from(files).filter(Boolean);
    if (!list.length) return;

    const invalid = list.find((f) => !isAllowedMediaUpload(f));
    if (invalid) {
      showToast(t('toasts.unsupportedType'));
      return;
    }

    const uploaded = await media.uploadFiles(list, apiFolderId);
    if (!uploaded) {
      showToast(t('toasts.uploadFailed'));
      return;
    }
    setSelectedId(uploaded.id);
    markDirty();
    showToast(t('toasts.uploaded', { file: uploaded.filename }));
  }

  function handleUpload() {
    openUploadPicker();
  }

  function handleCreate() {
    showToast(t('toasts.create'));
  }

  async function handleRefresh() {
    await media.refresh({
      query: debouncedQuery,
      folderId: apiFolderId,
      includeArchived: sidebar === 'trash',
    });
    if (media.status === 'error') {
      showToast(t('toasts.refreshFailed'));
      return;
    }
    showToast(t('toasts.refreshed'));
  }

  function onDragOverCenter(event: DragEvent) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
    setDropActive(true);
  }

  function onDragLeaveCenter(event: DragEvent) {
    if (event.currentTarget.contains(event.relatedTarget as Node)) return;
    setDropActive(false);
  }

  async function onDropCenter(event: DragEvent) {
    event.preventDefault();
    setDropActive(false);
    await handleUploadFiles(event.dataTransfer.files);
  }

  const displayCount = media.usingSamples
    ? filtered.length
    : sidebar === 'all' && !apiFolderId && !debouncedQuery.trim() && centerTab === 'all'
      ? media.total || filtered.length
      : filtered.length;

  const showInlineRail = focus.mode === 'normal' && !focus.isFullscreen;
  const trashReadOnly = sidebar === 'trash';

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
            onClick={() => void handleNewFolder()}
            aria-label={t('actions.newFolder')}
            data-testid="ml-folder-add"
          >
            <IhIcon name="plus" size={12} />
          </button>
        </div>
        <button
          type="button"
          className={`ml-ws__nav-item${!folderId && sidebar === 'all' ? ' is-active' : ''}`}
          onClick={() => {
            setFolderId(null);
            setSidebar('all');
          }}
          data-testid="ml-folder-all"
        >
          <span className="ml-ws__nav-item-icon">
            <IhIcon name="inventory" size={13} />
          </span>
          <span className="ml-ws__folder-name">{t('center.tabs.all')}</span>
        </button>
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
        {libraryFolders.length > 4 ? (
          <button
            type="button"
            className="ml-ws__show-all"
            onClick={() => setShowAllFolders((v) => !v)}
            data-testid="ml-show-all-folders"
          >
            {showAllFolders ? t('left.showLess') : t('left.showAll')}
            <IhIcon name="chevronRight" size={11} />
          </button>
        ) : null}
      </div>
    </aside>
  );

  const centerPanel = (
    <section
      className={`ml-ws__center${dropActive ? ' is-drop-active' : ''}`}
      aria-label={t('center.aria')}
      data-testid="ml-center"
      onDragOver={onDragOverCenter}
      onDragLeave={onDragLeaveCenter}
      onDrop={(e) => void onDropCenter(e)}
    >
      <div className="ml-ws__center-head">
        <h2>
          {sidebar === 'trash'
            ? t('center.trashTitle', { count: displayCount.toLocaleString('tr-TR') })
            : t('center.title', { count: displayCount.toLocaleString('tr-TR') })}
        </h2>
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

      {media.status === 'loading' && !media.assets.length ? (
        <div className="ml-ws__empty" data-testid="ml-loading">
          <IhIcon name="refresh" size={28} />
          <p>{t('center.loading')}</p>
        </div>
      ) : media.status === 'error' && !media.assets.length ? (
        <div className="ml-ws__empty" data-testid="ml-error">
          <IhIcon name="alert" size={28} />
          <p>{media.error || t('center.error')}</p>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void handleRefresh()}
            data-testid="ml-retry"
          >
            {t('center.retry')}
          </Button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="ml-ws__empty" data-testid="ml-empty">
          <IhIcon name="empty" size={28} />
          <p>{sidebar === 'trash' ? t('center.trashEmpty') : t('center.empty')}</p>
          {dropActive ? <p>{t('center.dropHint')}</p> : null}
        </div>
      ) : (
        <>
          {media.usingSamples ? (
            <p className="ml-ws__detail-empty" data-testid="ml-samples-hint">
              {t('center.samplesHint')}
            </p>
          ) : null}
          {trashReadOnly ? (
            <p className="ml-ws__detail-empty" data-testid="ml-trash-readonly">
              {t('center.trashReadOnly')}
            </p>
          ) : null}
          {media.uploading ? (
            <p className="ml-ws__detail-empty" data-testid="ml-uploading">
              {t('center.uploading')}
            </p>
          ) : null}
          <div
            className={`ml-ws__grid${viewMode === 'list' ? ' is-list' : ''}`}
            data-size={size}
            data-testid="ml-grid"
          >
            {filtered.map((asset) => {
              const thumb =
                asset.thumbUrl ||
                (isMediaAssetUuid(asset.id) ? media.displayUrls[asset.id] : undefined);
              const checked = selectedSet.has(asset.id);
              return (
                <article
                  key={asset.id}
                  className={`ml-ws__card${selected?.id === asset.id ? ' is-selected' : ''}${checked ? ' is-checked' : ''}`}
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
                    {thumb && asset.kind === 'image' ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={thumb} alt="" />
                    ) : (
                      <div className="ml-ws__thumb-doc">
                        <IhIcon name={docIcon(asset.ext)} size={28} />
                      </div>
                    )}
                    <span className="ml-ws__badge">{asset.ext}</span>
                    {isMissingDriveAsset(asset) ? (
                      <span
                        className="ml-ws__sync-badge is-missing"
                        data-testid={`ml-missing-badge-${asset.id}`}
                      >
                        {t('drive.sync.missing')}
                      </span>
                    ) : null}
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
                    <label
                      className={`ml-ws__check${checked ? ' is-on' : ''}`}
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => e.stopPropagation()}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => undefined}
                        onClick={(e) => toggleCheck(asset.id, e)}
                        aria-label={t('card.select')}
                        data-testid={`ml-check-${asset.id}`}
                      />
                      <span aria-hidden="true">
                        {checked ? <IhIcon name="check" size={10} /> : null}
                      </span>
                    </label>
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
                      onClick={(e) => openQuickTag(asset, e)}
                      aria-label={t('card.quickTag')}
                      data-testid={`ml-quick-tag-${asset.id}`}
                    >
                      <IhIcon name="plus" size={11} />
                    </button>
                  </div>
                  <div className="ml-ws__card-meta">
                    <div className="ml-ws__card-name-row">
                      <span className="ml-ws__card-name" title={asset.name}>
                        {asset.name}
                      </span>
                      <div className="ml-ws__card-more-wrap">
                        <button
                          type="button"
                          className="ml-ws__card-more"
                          onClick={(e) => {
                            e.stopPropagation();
                            selectAsset(asset.id);
                            setCardMenuId((prev) => (prev === asset.id ? null : asset.id));
                          }}
                          aria-label={t('card.more')}
                          aria-expanded={cardMenuId === asset.id}
                          data-testid={`ml-card-more-${asset.id}`}
                        >
                          <IhIcon name="quickAction" size={12} />
                        </button>
                        {cardMenuId === asset.id ? (
                          <div
                            ref={cardMenuRef}
                            className="ml-ws__card-menu"
                            role="menu"
                            data-testid={`ml-card-menu-${asset.id}`}
                          >
                            <button
                              type="button"
                              role="menuitem"
                              onClick={(e) => {
                                e.stopPropagation();
                                setCardMenuId(null);
                                selectAsset(asset.id);
                                setDetailTab('tags');
                                setDetailTagDraft(uniqueTags(asset.tags));
                                setDetailTagError(null);
                                setDetailTagOpen(true);
                              }}
                              disabled={trashReadOnly}
                            >
                              {t('card.quickTag')}
                            </button>
                            <button
                              type="button"
                              role="menuitem"
                              onClick={(e) => {
                                e.stopPropagation();
                                requestArchiveSingle(asset);
                              }}
                              disabled={trashReadOnly}
                              data-testid={`ml-card-archive-${asset.id}`}
                            >
                              {t('actions.archive')}
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </div>
                    <div className="ml-ws__card-sub">
                      {isGoogleDriveAsset(asset) ? (
                        <span
                          className="ml-ws__source-inline"
                          data-testid={`ml-drive-badge-${asset.id}`}
                        >
                          {t('drive.sourceShort')}
                          {' · '}
                        </span>
                      ) : null}
                      {asset.possibleDuplicate ? (
                        <span
                          className="ml-ws__dup-inline"
                          data-testid={`ml-duplicate-badge-${asset.id}`}
                        >
                          {t('drive.possibleDuplicateShort')}
                          {' · '}
                        </span>
                      ) : null}
                      {asset.sizeLabel}
                      {asset.resolution ? ` · ${asset.resolution}` : null}
                      {asset.duration && asset.kind !== 'video' ? ` · ${asset.duration}` : null}
                      {` · ${asset.dateLabel}`}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </>
      )}
    </section>
  );

  function renderDetailBody() {
    if (!selected) {
      return <p className="ml-ws__detail-empty">{t('right.empty')}</p>;
    }

    if (detailTab === 'tags') {
      return (
        <div data-testid="ml-detail-tags">
          {detailTagOpen || trashReadOnly ? null : (
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
                  setDetailTagDraft(uniqueTags(selected.tags));
                  setDetailTagError(null);
                  setDetailTagOpen(true);
                }}
                disabled={media.tagsUpdating || !isMediaAssetUuid(selected.id)}
                aria-label={t('right.addTag')}
                data-testid="ml-tag-add"
              >
                <IhIcon name="plus" size={11} />
              </Button>
            </div>
          )}
          {detailTagOpen && !trashReadOnly ? (
            <MediaLibraryTagEditor
              value={detailTagDraft}
              libraryTags={libraryTags}
              recentTags={recentTags}
              labels={tagEditorLabels}
              busy={media.tagsUpdating}
              error={detailTagError}
              onChange={setDetailTagDraft}
              onApply={() => void applyDetailTags()}
              onCancel={() => {
                setDetailTagOpen(false);
                setDetailTagDraft(uniqueTags(selected.tags));
                setDetailTagError(null);
              }}
              testIdPrefix="ml-detail-tag"
            />
          ) : trashReadOnly ? (
            <div className="ml-ws__tags">
              {selected.tags.map((tag) => (
                <StatusChip key={tag} tone="info">
                  {tag}
                </StatusChip>
              ))}
              <p className="ml-ws__detail-empty">{t('center.trashReadOnly')}</p>
            </div>
          ) : null}
        </div>
      );
    }

    if (detailTab === 'history') {
      return (
        <ul className="ml-ws__history-list">
          {selected.history.length === 0 ? (
            <li className="ml-ws__detail-empty">{t('right.empty')}</li>
          ) : (
            selected.history.map((h) => (
              <li key={h.id}>
                <Card title={h.action}>
                  <p className="ml-ws__history-meta">
                    {h.actor} · {h.at}
                  </p>
                </Card>
              </li>
            ))
          )}
        </ul>
      );
    }

    if (detailTab === 'usage') {
      return (
        <ul className="ml-ws__usage-list">
          <li className="ml-ws__detail-empty">{t('right.noUsage')}</li>
        </ul>
      );
    }

    return (
      <>
        <div className="ml-ws__preview-card">
          <div className="ml-ws__preview">
            {selectedPreviewUrl && selected.kind === 'image' ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={selectedPreviewUrl} alt="" />
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

        {isGoogleDriveAsset(selected) ? (
          <div className="ml-ws__drive-block" data-testid="ml-drive-detail">
            <p className="ml-ws__block-label">{t('drive.sectionTitle')}</p>
            {isMissingDriveAsset(selected) ? (
              <p className="ml-ws__drive-missing" data-testid="ml-drive-missing-note">
                {t('drive.missingRetainId')}
              </p>
            ) : null}
            {selected.possibleDuplicate ? (
              <p className="ml-ws__drive-dup" data-testid="ml-drive-duplicate-warning" role="status">
                {t('drive.possibleDuplicate')}
              </p>
            ) : null}
            <dl className="ml-ws__meta-list">
              <div>
                <dt>{t('drive.fields.source')}</dt>
                <dd>{t('drive.sourceGoogleDrive')}</dd>
              </div>
              <div>
                <dt>{t('drive.fields.assetId')}</dt>
                <dd className="ml-ws__mono">{selected.id}</dd>
              </div>
              <div>
                <dt>{t('drive.fields.filename')}</dt>
                <dd>{selected.name}</dd>
              </div>
              <div>
                <dt>{t('drive.fields.fileId')}</dt>
                <dd className="ml-ws__mono">{selected.externalFileId || '—'}</dd>
              </div>
              <div>
                <dt>{t('drive.fields.lastModified')}</dt>
                <dd>{selected.externalModifiedAt || '—'}</dd>
              </div>
              <div>
                <dt>{t('drive.fields.syncStatus')}</dt>
                <dd>
                  <StatusChip
                    tone={
                      selected.syncStatus === 'missing' || selected.syncStatus === 'error'
                        ? 'danger'
                        : selected.syncStatus === 'changed'
                          ? 'warning'
                          : 'success'
                    }
                  >
                    {selected.syncStatus === 'active'
                      ? t('drive.sync.active')
                      : selected.syncStatus === 'changed'
                        ? t('drive.sync.changed')
                        : selected.syncStatus === 'missing'
                          ? t('drive.sync.missing')
                          : selected.syncStatus === 'error'
                            ? t('drive.sync.error')
                            : t('drive.sync.unknown')}
                  </StatusChip>
                </dd>
              </div>
              <div>
                <dt>{t('drive.fields.category')}</dt>
                <dd>{selected.folderCategory || '—'}</dd>
              </div>
              <div>
                <dt>{t('drive.fields.project')}</dt>
                <dd className="ml-ws__mono">{selected.linkedProjectId || '—'}</dd>
              </div>
              {selected.externalChecksum ? (
                <div>
                  <dt>{t('drive.fields.checksum')}</dt>
                  <dd className="ml-ws__mono">{selected.externalChecksum}</dd>
                </div>
              ) : null}
            </dl>
            {selected.webViewLink ? (
              <a
                className="ml-ws__drive-link"
                href={selected.webViewLink}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="ml-open-in-drive"
              >
                {t('drive.openInDrive')}
                <span className="ml-ws__sr-only">{t('drive.opensExternal')}</span>
              </a>
            ) : null}
          </div>
        ) : null}

        {selected.description ? (
          <div className="ml-ws__desc-block">
            <TextArea
              label={t('right.description')}
              value={selected.description}
              readOnly
              data-testid="ml-description"
              rows={4}
            />
          </div>
        ) : null}

        <div className="ml-ws__tags-block">
          <p className="ml-ws__block-label">{t('right.tags')}</p>
          <div className="ml-ws__tags">
            {selected.tags.map((tag) => (
              <StatusChip key={tag} tone="info">
                {tag}
              </StatusChip>
            ))}
            {!trashReadOnly ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setDetailTab('tags');
                  setDetailTagDraft(uniqueTags(selected.tags));
                  setDetailTagError(null);
                  setDetailTagOpen(true);
                }}
                disabled={media.tagsUpdating}
                aria-label={t('right.addTag')}
              >
                <IhIcon name="plus" size={11} />
              </Button>
            ) : null}
          </div>
        </div>

        <div className="ml-ws__usage-block">
          <p className="ml-ws__block-label">{t('right.inUse')}</p>
          <p className="ml-ws__detail-empty">{t('right.noUsage')}</p>
        </div>

        {!trashReadOnly ? (
          <div className="ml-ws__detail-actions">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => requestArchiveSingle(selected)}
              data-testid="ml-detail-archive"
            >
              {t('actions.archive')}
            </Button>
          </div>
        ) : null}
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
            onClick={() => void handleQuick(item.id as QuickActionId)}
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
        <input
          ref={uploadInputRef}
          type="file"
          accept={ML_UPLOAD_ACCEPT}
          multiple
          hidden
          aria-hidden="true"
          tabIndex={-1}
          data-testid="ml-upload-input"
          onChange={(e) => {
            const files = e.target.files ? Array.from(e.target.files) : [];
            e.target.value = '';
            void handleUploadFiles(files);
          }}
        />
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
              onClick={() => void handleNewFolder()}
              data-testid="ml-new-folder"
            >
              <IhIcon name="plus" size={12} />
              {t('actions.newFolder')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleUpload}
              disabled={media.uploading}
              data-testid="ml-upload"
            >
              <IhIcon name="inbox" size={12} />
              {media.uploading ? t('center.uploading') : t('actions.upload')}
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

          {selectedCount > 0 ? (
            <div className="ml-ws__bulk" data-testid="ml-bulk-bar" role="group" aria-label={t('bulk.aria')}>
              <span className="ml-ws__bulk-count" data-testid="ml-bulk-count">
                {t('bulk.selected', { count: selectedCount })}
              </span>
              {!trashReadOnly ? (
                <>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => openBulkTag('add')}
                    data-testid="ml-bulk-add-tags"
                  >
                    {t('bulk.addTags')}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => openBulkTag('remove')}
                    data-testid="ml-bulk-remove-tags"
                  >
                    {t('bulk.removeTags')}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={requestArchiveBulk}
                    data-testid="ml-bulk-archive"
                  >
                    {t('actions.archive')}
                  </Button>
                </>
              ) : null}
              <Button
                variant="ghost"
                size="sm"
                onClick={clearSelection}
                data-testid="ml-bulk-clear"
              >
                {t('bulk.clear')}
              </Button>
            </div>
          ) : null}

          <div className="ml-ws__toolbar-controls">
            <label className="ml-ws__source-filter">
              <span className="ml-ws__sr-only">{t('sourceFilter.aria')}</span>
              <select
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value as SourceFilterId)}
                aria-label={t('sourceFilter.aria')}
                data-testid="ml-source-filter"
              >
                <option value="all">{t('sourceFilter.all')}</option>
                <option value="google_drive">{t('sourceFilter.googleDrive')}</option>
                <option value="upload">{t('sourceFilter.uploaded')}</option>
              </select>
            </label>
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
              onClick={() => void handleRefresh()}
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
              void handleQuick(id as QuickActionId);
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

        {quickTagAsset ? (
          <MediaLibraryQuickTagPopover
            open={Boolean(quickTagAssetId)}
            anchorRef={quickTagAnchorRef}
            assetId={quickTagAsset.id}
            initialTags={quickTagAsset.tags}
            libraryTags={libraryTags}
            recentTags={recentTags}
            labels={{ ...tagEditorLabels, title: t('tags.quickTitle') }}
            busy={media.tagsUpdating}
            error={quickTagError}
            onClose={() => {
              setQuickTagAssetId(null);
              setQuickTagError(null);
            }}
            onApply={applyQuickTag}
            onRecentTagsChange={setRecentTags}
          />
        ) : null}

        <Dialog
          open={bulkTagMode !== null}
          onClose={() => {
            if (bulkBusy) return;
            setBulkTagMode(null);
            setBulkTagError(null);
          }}
          title={
            bulkTagMode === 'remove' ? t('bulk.removeTagsTitle') : t('bulk.addTagsTitle')
          }
          footer={null}
        >
          <MediaLibraryTagEditor
            value={bulkTagDraft}
            libraryTags={
              bulkTagMode === 'remove' ? collectUnionTags(bulkAssets) : libraryTags
            }
            recentTags={recentTags}
            labels={tagEditorLabels}
            busy={bulkBusy}
            error={bulkTagError}
            onChange={setBulkTagDraft}
            onApply={() => void applyBulkTags()}
            onCancel={() => {
              if (bulkBusy) return;
              setBulkTagMode(null);
              setBulkTagError(null);
            }}
            testIdPrefix="ml-bulk-tag"
          />
        </Dialog>

        <Dialog
          open={archiveTarget !== null}
          onClose={() => {
            if (archiveBusy) return;
            setArchiveTarget(null);
          }}
          title={t('actions.archive')}
          footer={
            <>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setArchiveTarget(null)}
                disabled={archiveBusy}
                data-testid="ml-archive-cancel"
              >
                {t('tags.cancel')}
              </Button>
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => void confirmArchive()}
                disabled={archiveBusy}
                data-testid="ml-archive-confirm"
              >
                {archiveBusy ? t('toasts.archiving') : t('actions.archive')}
              </Button>
            </>
          }
        >
          <p data-testid="ml-archive-message">
            {archiveTarget?.kind === 'bulk'
              ? t('toasts.bulkArchiveConfirm', { count: archiveTarget.ids.length })
              : t('toasts.archiveConfirm')}
          </p>
        </Dialog>

        {toast ? (
          <div className="ml-ws__toast" role="status" data-testid="ml-toast">
            {toast}
          </div>
        ) : null}
      </div>
    </main>
  );
}
