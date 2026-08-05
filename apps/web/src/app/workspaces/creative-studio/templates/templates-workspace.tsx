'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, useState, type MouseEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import { CsBottomActionToolbar } from '../_components';
import {
  CreativeStudioFocusWorkspace,
  FocusActionDock,
  useCreativeStudioFocusMode,
  type FocusRailItem,
} from '../_components/focus-workspace';

import {
  AI_SUGGESTIONS,
  BOTTOM_ACTIONS,
  CARD_ACTIONS,
  CATEGORY_COUNTS,
  DEMO_TEMPLATES,
  DEVICE_ICONS,
  HEADER_TABS,
  PACK_ITEMS,
  QUICK_ACTIONS,
  SOURCE_ITEMS,
  TM_HOME,
  filterTemplates,
  sortTemplates,
  type AiSuggestionId,
  type BottomActionKey,
  type CardActionId,
  type DeviceKind,
  type HeaderTabId,
  type QuickActionId,
  type SortKey,
  type StudioTemplate,
  type TemplatePackId,
  type TemplateSource,
  type TemplateType,
} from './templates-model';

import './templates.css';

export function TemplatesWorkspace() {
  const t = useTranslations('creativeStudio.ds.templates');
  const tTools = useTranslations('creativeStudio.ds.tools');
  const tFocus = useTranslations('creativeStudio.focusWorkspace');
  const router = useRouter();

  const focus = useCreativeStudioFocusMode({
    storageKey: 'templates',
    defaultMode: 'normal',
    persist: false,
  });

  const [templates, setTemplates] = useState<StudioTemplate[]>(DEMO_TEMPLATES);
  const [category, setCategory] = useState<TemplateType | 'all'>('all');
  const [source, setSource] = useState<TemplateSource | null>(null);
  const [packId, setPackId] = useState<TemplatePackId | null>(null);
  const [headerTab, setHeaderTab] = useState<HeaderTabId>('investhomeAi');
  const [selectedId, setSelectedId] = useState<string>(DEMO_TEMPLATES[0]!.id);
  const [galleryIdx, setGalleryIdx] = useState(0);
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<TemplateType | 'all'>('all');
  const [deviceFilter, setDeviceFilter] = useState<DeviceKind | 'all'>('all');
  const [sort, setSort] = useState<SortKey>('popular');
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiType, setAiType] = useState<TemplateType>('landing');
  const [visibleCount, setVisibleCount] = useState(9);
  const [toast, setToast] = useState<string | null>(null);
  const [activeQuick, setActiveQuick] = useState<QuickActionId | null>('info');
  const [dockOverflowOpen, setDockOverflowOpen] = useState(false);

  const filtered = useMemo(
    () =>
      sortTemplates(
        filterTemplates(templates, {
          category,
          source,
          packId,
          query,
          typeFilter,
          deviceFilter,
        }),
        sort,
      ),
    [templates, category, source, packId, query, typeFilter, deviceFilter, sort],
  );

  const visible = filtered.slice(0, visibleCount);

  const selected = useMemo(
    () => templates.find((tpl) => tpl.id === selectedId) ?? filtered[0] ?? templates[0] ?? null,
    [templates, filtered, selectedId],
  );

  const tmRightRail: FocusRailItem[] = useMemo(
    () =>
      QUICK_ACTIONS.map((action) => ({
        id: action.id,
        icon: action.icon,
        labelKey: 'quickActions',
        label: t(`rail.actions.${action.id}`),
      })),
    [t],
  );

  const tmLeftRail: FocusRailItem[] = useMemo(
    () => [
      { id: 'categories', icon: 'theme', labelKey: 'assets', label: t('left.categories') },
      { id: 'sources', icon: 'inventory', labelKey: 'brief', label: t('left.sources') },
    ],
    [t],
  );

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 2200);
  }

  function selectTemplate(id: string) {
    setSelectedId(id);
    setGalleryIdx(0);
    setActiveQuick('info');
  }

  function toggleFavorite(id: string, event?: MouseEvent) {
    event?.stopPropagation();
    setTemplates((prev) =>
      prev.map((tpl) => (tpl.id === id ? { ...tpl, favorite: !tpl.favorite } : tpl)),
    );
    showToast(t('toasts.favorite'));
  }

  function handleQuick(action: QuickActionId) {
    setActiveQuick(action);
    if (!selected) return;
    if (action === 'info') return;
    if (action === 'preview') {
      showToast(t('toasts.preview'));
      return;
    }
    if (action === 'clone') {
      showToast(t('toasts.cloned'));
      return;
    }
    if (action === 'favorite') {
      toggleFavorite(selected.id);
      return;
    }
    if (action === 'open') {
      router.push(selected.builderHref as Route);
      return;
    }
    if (action === 'delete') {
      setTemplates((prev) =>
        prev.map((tpl) => (tpl.id === selected.id ? { ...tpl, trashed: true } : tpl)),
      );
      showToast(t('toasts.trashed'));
    }
  }

  function handleBottom(action: BottomActionKey) {
    showToast(t(`bottomBar.toasts.${action}`));
  }

  function handleAiGenerate() {
    showToast(t('toasts.aiGenerated'));
  }

  function applyAiSuggestion(id: AiSuggestionId) {
    setAiPrompt(t(`aiBanner.suggestions.${id}`));
  }

  function handleCardAction(id: string, action: CardActionId, event: MouseEvent) {
    event.stopPropagation();
    selectTemplate(id);
    if (action === 'open') {
      const tpl = templates.find((item) => item.id === id);
      if (tpl) router.push(tpl.builderHref as Route);
      return;
    }
    if (action === 'duplicate') {
      showToast(t('toasts.cloned'));
      return;
    }
    if (action === 'favorite') {
      toggleFavorite(id);
      return;
    }
    if (action === 'share') {
      showToast(t('toasts.shared'));
      return;
    }
    setTemplates((prev) =>
      prev.map((tpl) => (tpl.id === id ? { ...tpl, trashed: true } : tpl)),
    );
    showToast(t('toasts.trashed'));
  }

  function handleUpload() {
    showToast(t('toasts.uploaded'));
  }

  function handleCreate() {
    showToast(t('toasts.create'));
  }

  function clearSourceAndPack() {
    setSource(null);
    setPackId(null);
  }

  const showInlineRail = focus.mode === 'normal' && !focus.isFullscreen;

  const leftPanel = (
    <aside className="tm-ws__left" aria-label={t('left.aria')} data-testid="tm-left">
      <div className="tm-ws__nav-section">
        <div className="tm-ws__nav-section-head">{t('left.categories')}</div>
        {CATEGORY_COUNTS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`tm-ws__nav-item${category === item.id && !source && !packId ? ' is-active' : ''}`}
            onClick={() => {
              setCategory(item.id);
              clearSourceAndPack();
              setVisibleCount(9);
            }}
            data-testid={`tm-cat-${item.id}`}
          >
            <span className="tm-ws__nav-item-icon">
              <IhIcon name={item.icon} size={13} />
            </span>
            <span className="tm-ws__nav-label">{t(`left.types.${item.id}`)}</span>
            <span className="tm-ws__nav-count">{item.count}</span>
          </button>
        ))}
      </div>

      <div className="tm-ws__nav-section">
        <div className="tm-ws__nav-section-head">{t('left.sources')}</div>
        {SOURCE_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`tm-ws__nav-item${source === item.id ? ' is-active' : ''}`}
            onClick={() => {
              setSource(item.id);
              setPackId(null);
              setCategory('all');
              setVisibleCount(9);
            }}
            data-testid={`tm-source-${item.id}`}
          >
            <span className="tm-ws__nav-item-icon">
              <IhIcon name={item.icon} size={13} />
            </span>
            <span className="tm-ws__nav-label">{t(`left.sourceItems.${item.id}`)}</span>
            {item.badge === 'new' ? (
              <span className="tm-ws__nav-badge">{t('left.newBadge')}</span>
            ) : null}
          </button>
        ))}
      </div>

      <div className="tm-ws__nav-section">
        <div className="tm-ws__nav-section-head">{t('left.packs')}</div>
        {PACK_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`tm-ws__nav-item${packId === item.id ? ' is-active' : ''}`}
            onClick={() => {
              setPackId(item.id);
              setSource(null);
              setCategory('all');
              setVisibleCount(9);
            }}
            data-testid={`tm-pack-${item.id}`}
          >
            <span className="tm-ws__nav-item-icon">
              <IhIcon name={item.icon} size={13} />
            </span>
            <span className="tm-ws__nav-label">{t(`left.packItems.${item.id}`)}</span>
            <span className="tm-ws__nav-count">{item.count}</span>
          </button>
        ))}
      </div>
    </aside>
  );

  const centerPanel = (
    <section className="tm-ws__center" aria-label={t('center.aria')} data-testid="tm-center">
      <div className="tm-ws__toolbar" role="toolbar" aria-label={t('toolbarAria')}>
        <label className="tm-ws__search">
          <IhIcon name="search" size={14} />
          <span className="sr-only">{t('searchLabel')}</span>
          <input
            type="search"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setVisibleCount(9);
            }}
            placeholder={t('searchPlaceholder')}
            data-testid="tm-search"
          />
        </label>
        <div className="tm-ws__toolbar-controls">
          <select
            className="tm-ws__ctrl tm-ws__ctrl--md"
            value={packId ?? 'all'}
            onChange={(e) => {
              const next = e.target.value;
              setPackId(next === 'all' ? null : (next as TemplatePackId));
              setSource(null);
              setCategory('all');
              setVisibleCount(9);
            }}
            aria-label={t('filters.categoryAria')}
            data-testid="tm-filter-category"
          >
            <option value="all">{t('filters.allCategories')}</option>
            {PACK_ITEMS.map((item) => (
              <option key={item.id} value={item.id}>
                {t(`left.packItems.${item.id}`)}
              </option>
            ))}
          </select>
          <select
            className="tm-ws__ctrl tm-ws__ctrl--md"
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value as TemplateType | 'all');
              setVisibleCount(9);
            }}
            aria-label={t('filters.builderTypeAria')}
            data-testid="tm-filter-type"
          >
            <option value="all">{t('filters.allBuilderTypes')}</option>
            {CATEGORY_COUNTS.filter((c) => c.id !== 'all').map((c) => (
              <option key={c.id} value={c.id}>
                {t(`left.types.${c.id}`)}
              </option>
            ))}
          </select>
          <select
            className="tm-ws__ctrl tm-ws__ctrl--md"
            value={deviceFilter}
            onChange={(e) => {
              setDeviceFilter(e.target.value as DeviceKind | 'all');
              setVisibleCount(9);
            }}
            aria-label={t('filters.deviceAria')}
            data-testid="tm-filter-device"
          >
            <option value="all">{t('filters.allDevices')}</option>
            <option value="desktop">{t('devices.desktop')}</option>
            <option value="tablet">{t('devices.tablet')}</option>
            <option value="mobile">{t('devices.mobile')}</option>
          </select>
          <select
            className="tm-ws__ctrl tm-ws__ctrl--sm"
            aria-label={t('filters.colorAria')}
            data-testid="tm-filter-color"
            defaultValue="all"
          >
            <option value="all">{t('filters.color')}</option>
            <option value="navy">{t('filters.colors.navy')}</option>
            <option value="cyan">{t('filters.colors.cyan')}</option>
            <option value="neutral">{t('filters.colors.neutral')}</option>
          </select>
          <select
            className="tm-ws__ctrl tm-ws__ctrl--sm"
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            aria-label={t('filters.popularityAria')}
            data-testid="tm-sort"
          >
            <option value="popular">{t('sort.popular')}</option>
            <option value="newest">{t('sort.newest')}</option>
            <option value="nameAsc">{t('sort.nameAsc')}</option>
          </select>
        </div>
      </div>

      <div className="tm-ws__ai-banner" data-testid="tm-ai-banner">
        <div className="tm-ws__ai-banner-head">
          <span className="tm-ws__ai-banner-icon" aria-hidden="true">
            <IhIcon name="sparkles" size={14} />
          </span>
          <h2>{t('aiBanner.title')}</h2>
        </div>
        <div className="tm-ws__ai-banner-body">
          <label className="sr-only" htmlFor="tm-ai-prompt">
            {t('aiBanner.promptLabel')}
          </label>
          <textarea
            id="tm-ai-prompt"
            value={aiPrompt}
            onChange={(e) => setAiPrompt(e.target.value)}
            placeholder={t('aiBanner.promptPlaceholder')}
            rows={2}
            data-testid="tm-ai-prompt"
          />
          <div
            className="tm-ws__ai-chips"
            role="group"
            aria-label={t('aiBanner.suggestionsAria')}
            data-testid="tm-ai-suggestions"
          >
            {AI_SUGGESTIONS.map((id) => (
              <button
                key={id}
                type="button"
                className="tm-ws__ai-chip"
                onClick={() => applyAiSuggestion(id)}
                data-testid={`tm-ai-chip-${id}`}
              >
                {t(`aiBanner.suggestions.${id}`)}
              </button>
            ))}
          </div>
          <div className="tm-ws__ai-banner-actions">
            <select
              value={aiType}
              onChange={(e) => setAiType(e.target.value as TemplateType)}
              aria-label={t('aiBanner.typeAria')}
              data-testid="tm-ai-type"
            >
              {CATEGORY_COUNTS.filter((c) => c.id !== 'all').map((c) => (
                <option key={c.id} value={c.id}>
                  {t(`left.types.${c.id}`)}
                </option>
              ))}
            </select>
            <Button
              variant="primary"
              size="sm"
              onClick={handleAiGenerate}
              data-testid="tm-ai-create"
            >
              <IhIcon name="sparkles" size={12} />
              {t('aiBanner.create')}
            </Button>
          </div>
        </div>
      </div>

      <div className="tm-ws__center-head">
        <h2>{t('center.title', { count: filtered.length })}</h2>
      </div>

      {visible.length === 0 ? (
        <div className="tm-ws__empty" data-testid="tm-empty">
          <IhIcon name="empty" size={28} />
          <p>{t('center.empty')}</p>
        </div>
      ) : (
        <div className="tm-ws__grid" data-testid="tm-grid">
          {visible.map((tpl) => (
            <article
              key={tpl.id}
              className={`tm-ws__card${selected?.id === tpl.id ? ' is-selected' : ''}`}
              onClick={() => selectTemplate(tpl.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  selectTemplate(tpl.id);
                }
              }}
              role="button"
              tabIndex={0}
              data-testid={`tm-card-${tpl.id}`}
            >
              <div className="tm-ws__thumb">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={tpl.thumbUrl} alt="" />
                <button
                  type="button"
                  className={`tm-ws__fav${tpl.favorite ? ' is-on' : ''}`}
                  onClick={(e) => toggleFavorite(tpl.id, e)}
                  aria-label={t('card.favorite')}
                  data-testid={`tm-fav-${tpl.id}`}
                >
                  <IhIcon name="check" size={11} />
                </button>
              </div>
              <div className="tm-ws__card-meta">
                <div className="tm-ws__card-name-row">
                  <span className="tm-ws__card-name" title={tpl.name}>
                    {tpl.name}
                  </span>
                </div>
                <div className="tm-ws__card-sub">
                  <span>{t(`left.types.${tpl.type}`)}</span>
                  <span className="tm-ws__devices" aria-label={t('card.devices')}>
                    {tpl.devices.map((d) => (
                      <IhIcon key={d} name={DEVICE_ICONS[d]} size={10} />
                    ))}
                  </span>
                </div>
                <div
                  className="tm-ws__card-actions"
                  role="group"
                  aria-label={t('card.actionsAria')}
                >
                  {CARD_ACTIONS.map((action) => (
                    <button
                      key={action.id}
                      type="button"
                      className={`tm-ws__card-action${action.id === 'favorite' && tpl.favorite ? ' is-on' : ''}`}
                      title={t(`card.actions.${action.id}`)}
                      aria-label={t(`card.actions.${action.id}`)}
                      onClick={(e) => handleCardAction(tpl.id, action.id, e)}
                      data-testid={`tm-card-${action.id}-${tpl.id}`}
                    >
                      <IhIcon name={action.icon} size={12} />
                    </button>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {visibleCount < filtered.length ? (
        <div className="tm-ws__load-more">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setVisibleCount((n) => n + 6)}
            data-testid="tm-load-more"
          >
            {t('center.loadMore')}
          </Button>
        </div>
      ) : null}
    </section>
  );

  const rightDetail = (
    <aside className="tm-ws__right" aria-label={t('right.aria')} data-testid="tm-right">
      <div className="tm-ws__detail-head">
        <h2>{t('right.title')}</h2>
      </div>
      <div className="tm-ws__detail-body">
        {!selected ? (
          <p className="tm-ws__detail-empty">{t('right.empty')}</p>
        ) : (
          <>
            <div className="tm-ws__preview">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={selected.gallery[galleryIdx] ?? selected.thumbUrl}
                alt=""
              />
            </div>
            <div className="tm-ws__gallery" data-testid="tm-gallery">
              {selected.gallery.slice(0, 4).map((url, idx) => (
                <button
                  key={`${selected.id}-g-${idx}`}
                  type="button"
                  className={galleryIdx === idx ? 'is-active' : undefined}
                  onClick={() => setGalleryIdx(idx)}
                  aria-label={t('right.galleryThumb', { index: idx + 1 })}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={url} alt="" />
                  {idx === 3 ? (
                    <span className="tm-ws__gallery-more" aria-hidden="true">
                      +8
                    </span>
                  ) : null}
                </button>
              ))}
            </div>

            <div className="tm-ws__detail-title-row">
              <h3>{selected.name}</h3>
              <button
                type="button"
                className={`tm-ws__fav${selected.favorite ? ' is-on' : ''}`}
                onClick={() => toggleFavorite(selected.id)}
                aria-label={t('card.favorite')}
                style={{ position: 'static' }}
              >
                <IhIcon name="check" size={11} />
              </button>
            </div>

            <div className="tm-ws__tags">
              {selected.tags.map((tag) => (
                <StatusChip key={tag} tone="info">
                  {tag}
                </StatusChip>
              ))}
            </div>

            <p className="tm-ws__desc">{selected.description}</p>

            <div>
              <p className="tm-ws__block-label">{t('right.features')}</p>
              <ul className="tm-ws__feature-list">
                {selected.features.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>

            <div>
              <p className="tm-ws__block-label">{t('right.usage')}</p>
              <ol className="tm-ws__usage-list">
                {selected.usageSteps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </div>

            <div className="tm-ws__actions">
              <Button
                variant="primary"
                size="sm"
                onClick={() => router.push(selected.builderHref as Route)}
                data-testid="tm-open-editor"
              >
                <IhIcon name="arrowRight" size={12} />
                {t('right.openEditor')}
              </Button>
              <div className="tm-ws__actions-row">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => showToast(t('toasts.preview'))}
                  data-testid="tm-preview"
                >
                  {t('right.preview')}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => showToast(t('toasts.cloned'))}
                  data-testid="tm-clone"
                >
                  {t('right.clone')}
                </Button>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => toggleFavorite(selected.id)}
                data-testid="tm-add-favorite"
              >
                <IhIcon name="check" size={12} />
                {t('right.addFavorite')}
              </Button>
            </div>
          </>
        )}
      </div>
    </aside>
  );

  const inlineRightRail = showInlineRail ? (
    <nav
      className="cs-fw__rail cs-fw__rail--right"
      data-testid="tm-rail"
      aria-label={t('rail.aria')}
    >
      {tmRightRail.map((item) => {
        const isActive = activeQuick === item.id;
        return (
          <button
            key={item.id}
            type="button"
            className={['cs-fw__rail-btn', isActive ? 'is-active' : '']
              .filter(Boolean)
              .join(' ')}
            data-testid={`tm-rail-${item.id}`}
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
    <div className="tm-ws__right-shell">
      {rightDetail}
      {inlineRightRail}
    </div>
  ) : (
    rightDetail
  );

  const bottomActionToolbar = (
    <CsBottomActionToolbar
      testId="tm-bat"
      primary={{
        label: t('bottomBar.actions.addComponent'),
        icon: 'plus',
        onClick: () => handleBottom('addComponent'),
        testId: 'tm-action-addComponent',
      }}
      actions={BOTTOM_ACTIONS.filter((a) => a.key !== 'addComponent').map((action) => ({
        key: action.key,
        icon: action.icon,
        label: t(`bottomBar.actions.${action.key}`),
        onClick: () => handleBottom(action.key),
        testId: `tm-action-${action.key}`,
      }))}
    />
  );

  return (
    <main className="dashboard" data-testid="templates-page">
      <div className="tm-ws" data-testid="tm-workspace">
        <header className="tm-ws__header cs-page-header">
          <div className="tm-ws__header-main">
            <div>
              <Link href={TM_HOME as Route} className="tm-ws__back">
                <IhIcon name="chevronLeft" size={12} />
                {t('back')}
              </Link>
              <nav aria-label={t('breadcrumbAria')}>
                <ol className="tm-ws__breadcrumb">
                  <li>
                    <Link href={TM_HOME as Route}>{t('creativeStudio')}</Link>
                  </li>
                  <li className="tm-ws__breadcrumb-sep" aria-hidden="true">
                    /
                  </li>
                  <li className="tm-ws__breadcrumb-current" aria-current="page">
                    {tTools('templates.title')}
                  </li>
                </ol>
              </nav>
              <h1>
                <span className="tm-ws__title-icon" aria-hidden="true">
                  <IhIcon name="theme" size={22} />
                </span>
                {tTools('templates.title')}
              </h1>
              <p className="tm-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
            </div>
            <div
              className="tm-ws__header-tabs"
              role="tablist"
              aria-label={t('tabsAria')}
              data-testid="tm-header-tabs"
            >
              {HEADER_TABS.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={headerTab === tab}
                  className={`tm-ws__header-tab${headerTab === tab ? ' is-active' : ''}`}
                  onClick={() => {
                    setHeaderTab(tab);
                    showToast(t(`toasts.tab.${tab}`));
                  }}
                  data-testid={`tm-tab-${tab}`}
                >
                  {t(`tabs.${tab}`)}
                </button>
              ))}
            </div>
          </div>
          <div className="tm-ws__header-right">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleAiGenerate}
              data-testid="tm-ai-header"
            >
              <IhIcon name="plus" size={12} />
              {t('actions.aiCreate')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleUpload}
              data-testid="tm-upload"
            >
              <IhIcon name="inbox" size={12} />
              {t('actions.upload')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              className="tm-ws__create-btn"
              onClick={handleCreate}
              data-testid="tm-create"
            >
              <IhIcon name="sparkles" size={12} />
              {t('actions.create')}
              <IhIcon name="chevronDown" size={10} />
            </Button>
          </div>
        </header>

        <CreativeStudioFocusWorkspace
          mode={focus.mode}
          onModeChange={focus.setMode}
          isFullscreen={focus.isFullscreen}
          onExitFullscreen={focus.exitFullscreen}
          layoutClassName="tm-ws__layout"
          leftRail={tmLeftRail}
          rightRail={tmRightRail}
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
          testId="tm-dock"
        />

        {toast ? (
          <div className="tm-ws__toast" role="status" data-testid="tm-toast">
            {toast}
          </div>
        ) : null}
      </div>
    </main>
  );
}
