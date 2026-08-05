'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, useState } from 'react';
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
  AC_HOME,
  AI_USAGE,
  ASSETS,
  BOTTOM_ACTIONS,
  DEMO_MESSAGES,
  DETAIL_TABS,
  FOLDERS,
  MODELS,
  OUTPUTS,
  RAIL_ACTIONS,
  STORAGE,
  SUGGESTIONS,
  TEMPLATES,
  THREADS,
  filterThreads,
  type BottomActionKey,
  type ChatMessage,
  type DetailTabId,
  type ModelId,
  type RailActionId,
  type SizePreset,
  type SortKey,
  type ViewMode,
} from './ai-chat-model';

import './ai-chat.css';

export function AiChatWorkspace() {
  const t = useTranslations('creativeStudio.ds.aiChat');
  const tTools = useTranslations('creativeStudio.ds.tools');
  const tFocus = useTranslations('creativeStudio.focusWorkspace');

  const focus = useCreativeStudioFocusMode({
    storageKey: 'ai-chat',
    defaultMode: 'normal',
    persist: false,
  });

  const [threads] = useState(THREADS);
  const [activeThreadId, setActiveThreadId] = useState(THREADS[0]!.id);
  const [folderId, setFolderId] = useState<string | null>(null);
  const [chatQuery, setChatQuery] = useState('');
  const [centerQuery, setCenterQuery] = useState('');
  const [modelId, setModelId] = useState<ModelId>('investhome');
  const [composerModel, setComposerModel] = useState<ModelId>('investhome');
  const [detailTab, setDetailTab] = useState<DetailTabId>('templates');
  const [activeRail, setActiveRail] = useState<RailActionId>('suggestions');
  const [viewMode, setViewMode] = useState<ViewMode>('thread');
  const [sort, setSort] = useState<SortKey>('newest');
  const [size, setSize] = useState<SizePreset>('medium');
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>(DEMO_MESSAGES);
  const [toast, setToast] = useState<string | null>(null);
  const [dockOverflowOpen, setDockOverflowOpen] = useState(false);

  const filteredThreads = useMemo(
    () => filterThreads(threads, { query: chatQuery, folderId }),
    [threads, chatQuery, folderId],
  );

  const activeThread = useMemo(
    () => threads.find((th) => th.id === activeThreadId) ?? threads[0]!,
    [threads, activeThreadId],
  );

  const acRightRail: FocusRailItem[] = useMemo(
    () =>
      RAIL_ACTIONS.map((action) => ({
        id: action.id,
        icon: action.icon,
        labelKey: action.labelKey,
        label: t(`rail.actions.${action.id}`),
      })),
    [t],
  );

  const acLeftRail: FocusRailItem[] = useMemo(
    () => [
      { id: 'chats', icon: 'sparkles', labelKey: 'brief', label: t('left.chats') },
      { id: 'folders', icon: 'projects', labelKey: 'assets', label: t('left.folders') },
    ],
    [t],
  );

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 2200);
  }

  function handleRail(id: RailActionId) {
    setActiveRail(id);
    if (id === 'suggestions') setDetailTab('templates');
    if (id === 'export') setDetailTab('outputs');
    if (id === 'history') setDetailTab('outputs');
    if (id === 'quickActions') setDetailTab('assets');
    showToast(t(`rail.toasts.${id}`));
  }

  function handleBottom(action: BottomActionKey) {
    showToast(t(`bottomBar.toasts.${action}`));
  }

  function handleNewChat() {
    showToast(t('toasts.newChat'));
  }

  function handleUpload() {
    showToast(t('toasts.uploaded'));
  }

  function handleCreate() {
    showToast(t('toasts.create'));
  }

  function handleSend() {
    const text = draft.trim();
    if (!text) return;
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text,
    };
    setMessages((prev) => [...prev, userMsg]);
    setDraft('');
    window.setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: t('center.demoReply'),
        },
      ]);
    }, 500);
    showToast(t('toasts.sent'));
  }

  function applySuggestion(label: string) {
    setDraft(label);
    showToast(t('toasts.suggestion'));
  }

  const showInlineRail = focus.mode === 'normal' && !focus.isFullscreen;

  const leftPanel = (
    <aside className="ac-ws__left" aria-label={t('left.aria')} data-testid="ac-left">
      <div
        className="ac-ws__storage"
        data-testid="ac-storage"
        style={{ ['--ac-bar-pct' as string]: `${STORAGE.percent}%` }}
      >
        <span className="ac-ws__storage-label">{t('storage.label')}</span>
        <span className="ac-ws__storage-value">
          {t('storage.value', { used: STORAGE.usedGb, total: STORAGE.totalGb })}
        </span>
        <div
          className="ac-ws__storage-bar"
          role="progressbar"
          aria-valuenow={STORAGE.percent}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <span />
        </div>
      </div>

      <div className="ac-ws__nav-section">
        <div className="ac-ws__nav-section-head">
          <span>{t('left.chats')}</span>
          <button
            type="button"
            className="ac-ws__icon-btn"
            onClick={handleNewChat}
            aria-label={t('actions.newChat')}
            data-testid="ac-chat-add"
          >
            <IhIcon name="plus" size={12} />
          </button>
        </div>
        <label className="ac-ws__chat-search">
          <IhIcon name="search" size={12} />
          <span className="sr-only">{t('left.searchChats')}</span>
          <input
            type="search"
            value={chatQuery}
            onChange={(e) => setChatQuery(e.target.value)}
            placeholder={t('left.searchPlaceholder')}
            data-testid="ac-chat-search"
          />
        </label>
        {filteredThreads.map((th) => (
          <button
            key={th.id}
            type="button"
            className={`ac-ws__nav-item${activeThreadId === th.id ? ' is-active' : ''}`}
            onClick={() => {
              setActiveThreadId(th.id);
              setModelId(th.modelId);
              setComposerModel(th.modelId);
            }}
            data-testid={`ac-thread-${th.id}`}
          >
            <span className="ac-ws__nav-item-icon">
              <IhIcon name="sparkles" size={13} />
            </span>
            <span className="ac-ws__thread-title">{th.title}</span>
            <span className="ac-ws__folder-count">{th.timeLabel}</span>
            <span className="ac-ws__thread-meta">{th.preview}</span>
          </button>
        ))}
      </div>

      <div className="ac-ws__nav-section">
        <div className="ac-ws__nav-section-head">
          <span>{t('left.folders')}</span>
          <button
            type="button"
            className="ac-ws__icon-btn"
            onClick={() => showToast(t('toasts.folderCreated'))}
            aria-label={t('actions.newFolder')}
            data-testid="ac-folder-add"
          >
            <IhIcon name="plus" size={12} />
          </button>
        </div>
        {FOLDERS.map((folder) => (
          <button
            key={folder.id}
            type="button"
            className={`ac-ws__nav-item${folderId === folder.id ? ' is-active' : ''}`}
            onClick={() => setFolderId((prev) => (prev === folder.id ? null : folder.id))}
            data-testid={`ac-folder-${folder.id}`}
          >
            <span className="ac-ws__nav-item-icon">
              <IhIcon name="projects" size={13} />
            </span>
            <span className="ac-ws__thread-title">{folder.name}</span>
            <span className="ac-ws__folder-count">{folder.count}</span>
          </button>
        ))}
      </div>

      <div
        className="ac-ws__usage"
        data-testid="ac-usage"
        style={{ ['--ac-bar-pct' as string]: `${AI_USAGE.percent}%` }}
      >
        <span className="ac-ws__usage-label">{t('usage.label')}</span>
        <span className="ac-ws__usage-value">
          {t('usage.value', { used: AI_USAGE.usedLabel, total: AI_USAGE.totalLabel })}
        </span>
        <div
          className="ac-ws__usage-bar"
          role="progressbar"
          aria-valuenow={AI_USAGE.percent}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <span />
        </div>
      </div>
    </aside>
  );

  const centerPanel = (
    <section className="ac-ws__center" aria-label={t('center.aria')} data-testid="ac-center">
      <div className="ac-ws__utility" role="toolbar" aria-label={t('utilityAria')}>
        <label className="ac-ws__search">
          <IhIcon name="search" size={14} />
          <span className="sr-only">{t('searchLabel')}</span>
          <input
            type="search"
            value={centerQuery}
            onChange={(e) => setCenterQuery(e.target.value)}
            placeholder={t('searchPlaceholder')}
            data-testid="ac-search"
          />
        </label>
        <div className="ac-ws__utility-controls">
          <Button variant="secondary" size="sm" data-testid="ac-filter">
            <IhIcon name="activity" size={12} />
            {t('actions.filter')}
          </Button>
          <div className="ac-ws__view-toggle" role="group" aria-label={t('viewAria')}>
            <button
              type="button"
              className={viewMode === 'thread' ? 'is-active' : undefined}
              aria-pressed={viewMode === 'thread'}
              onClick={() => setViewMode('thread')}
              data-testid="ac-view-thread"
              title={t('view.thread')}
            >
              <IhIcon name="documents" size={12} />
            </button>
            <button
              type="button"
              className={viewMode === 'compact' ? 'is-active' : undefined}
              aria-pressed={viewMode === 'compact'}
              onClick={() => setViewMode('compact')}
              data-testid="ac-view-compact"
              title={t('view.compact')}
            >
              <IhIcon name="executive" size={12} />
            </button>
          </div>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            aria-label={t('sortAria')}
            data-testid="ac-sort"
          >
            <option value="newest">{t('sort.newest')}</option>
            <option value="oldest">{t('sort.oldest')}</option>
            <option value="nameAsc">{t('sort.nameAsc')}</option>
          </select>
          <select
            value={size}
            onChange={(e) => setSize(e.target.value as SizePreset)}
            aria-label={t('sizeAria')}
            data-testid="ac-size"
          >
            <option value="small">{t('size.small')}</option>
            <option value="medium">{t('size.medium')}</option>
            <option value="large">{t('size.large')}</option>
          </select>
          <button
            type="button"
            className="ac-ws__icon-btn"
            onClick={() => showToast(t('toasts.refreshed'))}
            aria-label={t('actions.refresh')}
            data-testid="ac-refresh"
          >
            <IhIcon name="refresh" size={13} />
          </button>
        </div>
      </div>

      <div className="ac-ws__chat-head">
        <div>
          <h2>
            {activeThread.title}
            <button
              type="button"
              className="ac-ws__icon-btn"
              aria-label={t('center.editTitle')}
              onClick={() => showToast(t('toasts.editTitle'))}
            >
              <IhIcon name="design" size={12} />
            </button>
          </h2>
          <div className="ac-ws__tags">
            {activeThread.tags.map((tag) => (
              <StatusChip key={tag} tone="info">
                {tag}
              </StatusChip>
            ))}
          </div>
        </div>
        <div className="ac-ws__chat-head-actions">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => showToast(t('toasts.shared'))}
            data-testid="ac-share"
          >
            <IhIcon name="users" size={12} />
            {t('actions.share')}
          </Button>
          <button
            type="button"
            className="ac-ws__icon-btn"
            aria-label={t('actions.more')}
            onClick={() => showToast(t('toasts.menu'))}
            data-testid="ac-more"
          >
            <IhIcon name="quickAction" size={12} />
          </button>
        </div>
      </div>

      <div className="ac-ws__thread" data-view={viewMode} data-size={size} data-testid="ac-thread">
        {messages
          .filter((msg) => {
            const q = centerQuery.trim().toLowerCase();
            if (!q) return true;
            return msg.content.toLowerCase().includes(q);
          })
          .map((msg) => (
          <div
            key={msg.id}
            className={`ac-ws__msg ac-ws__msg--${msg.role}`}
            data-testid={`ac-msg-${msg.id}`}
          >
            <span className="ac-ws__avatar" aria-hidden="true">
              {msg.role === 'user' ? 'AD' : <IhIcon name="sparkles" size={12} />}
            </span>
            <div>
              <div className="ac-ws__bubble">
                <p style={{ margin: 0 }}>{msg.content}</p>
                {msg.richCard ? (
                  <article className="ac-ws__rich-card" data-testid="ac-rich-card">
                    <div className="ac-ws__rich-media">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={msg.richCard.imageUrl} alt="" />
                    </div>
                    <div className="ac-ws__rich-body">
                      <h3>{msg.richCard.title}</h3>
                      <p>{msg.richCard.subtitle}</p>
                      <div className="ac-ws__rich-actions">
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => showToast(msg.richCard!.primaryCta)}
                        >
                          {msg.richCard.primaryCta}
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => showToast(msg.richCard!.secondaryCta)}
                        >
                          {msg.richCard.secondaryCta}
                        </Button>
                      </div>
                    </div>
                  </article>
                ) : null}
              </div>
              {msg.role === 'assistant' ? (
                <div className="ac-ws__feedback">
                  <button
                    type="button"
                    className="ac-ws__icon-btn"
                    aria-label={t('center.feedback.up')}
                    onClick={() => showToast(t('toasts.feedback'))}
                  >
                    <IhIcon name="trendingUp" size={12} />
                  </button>
                  <button
                    type="button"
                    className="ac-ws__icon-btn"
                    aria-label={t('center.feedback.down')}
                    onClick={() => showToast(t('toasts.feedback'))}
                  >
                    <IhIcon name="activity" size={12} />
                  </button>
                  <button
                    type="button"
                    className="ac-ws__icon-btn"
                    aria-label={t('center.feedback.copy')}
                    onClick={() => showToast(t('toasts.copied'))}
                  >
                    <IhIcon name="documents" size={12} />
                  </button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => showToast(t('toasts.edit'))}
                  >
                    {t('center.feedback.edit')}
                    <IhIcon name="chevronDown" size={10} />
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
        ))}

        <div className="ac-ws__pills" aria-label={t('center.suggestionsAria')}>
          {SUGGESTIONS.map((label) => (
            <button
              key={label}
              type="button"
              className="ac-ws__pill"
              onClick={() => applySuggestion(t(`center.suggestions.${label}`))}
              data-testid={`ac-pill-${label}`}
            >
              {t(`center.suggestions.${label}`)}
            </button>
          ))}
        </div>
      </div>

      <div className="ac-ws__composer" data-testid="ac-composer">
        <label className="sr-only" htmlFor="ac-composer-input">
          {t('composer.label')}
        </label>
        <textarea
          id="ac-composer-input"
          className="ac-ws__composer-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={t('composer.placeholder')}
          rows={3}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              handleSend();
            }
          }}
        />
        <div className="ac-ws__composer-bar">
          <div className="ac-ws__composer-tools">
            <button
              type="button"
              className="ac-ws__icon-btn"
              aria-label={t('composer.attach')}
              onClick={handleUpload}
            >
              <IhIcon name="plus" size={12} />
            </button>
            <button
              type="button"
              className="ac-ws__icon-btn"
              aria-label={t('composer.mention')}
              onClick={() => showToast(t('toasts.mention'))}
            >
              <IhIcon name="users" size={12} />
            </button>
            <button
              type="button"
              className="ac-ws__icon-btn"
              aria-label={t('composer.image')}
              onClick={() => showToast(t('toasts.image'))}
            >
              <IhIcon name="inventory" size={12} />
            </button>
          </div>
          <div className="ac-ws__composer-actions">
            <select
              value={composerModel}
              onChange={(e) => setComposerModel(e.target.value as ModelId)}
              aria-label={t('composer.modelAria')}
              data-testid="ac-composer-model"
            >
              {MODELS.map((m) => (
                <option key={m.id} value={m.id}>
                  {t(`models.${m.labelKey}`)}
                </option>
              ))}
            </select>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSend}
              disabled={!draft.trim()}
              data-testid="ac-send"
            >
              <IhIcon name="arrowRight" size={12} />
              {t('composer.send')}
            </Button>
          </div>
        </div>
      </div>
    </section>
  );

  function renderDetailBody() {
    if (detailTab === 'assets') {
      return (
        <div>
          <p className="ac-ws__block-label">{t('right.recommendedAssets')}</p>
          <div className="ac-ws__asset-grid">
            {ASSETS.map((asset) => (
              <button
                key={asset.id}
                type="button"
                className="ac-ws__asset-card"
                onClick={() => showToast(asset.name)}
                data-testid={`ac-asset-${asset.id}`}
              >
                <div className="ac-ws__asset-thumb">
                  {asset.thumbUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={asset.thumbUrl} alt="" />
                  ) : (
                    <IhIcon name="sparkles" size={18} />
                  )}
                </div>
                <div className="ac-ws__asset-meta">
                  <strong title={asset.name}>{asset.name}</strong>
                  <span>{asset.ext}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (detailTab === 'outputs') {
      return (
        <div>
          <p className="ac-ws__block-label">{t('right.recentOutputs')}</p>
          <ul className="ac-ws__output-list">
            {OUTPUTS.map((out) => (
              <li key={out.id} className="ac-ws__output-item" data-testid={`ac-output-${out.id}`}>
                <span className="ac-ws__output-icon">
                  <IhIcon name={out.icon} size={14} />
                </span>
                <div>
                  <strong>{out.title}</strong>
                  <span>
                    {out.type} · {out.timeLabel}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      );
    }

    return (
      <>
        <div>
          <p className="ac-ws__block-label">{t('right.templates')}</p>
          <div className="ac-ws__tpl-grid">
            {TEMPLATES.map((tpl) => (
              <button
                key={tpl.id}
                type="button"
                className="ac-ws__tpl-card"
                onClick={() => showToast(tpl.title)}
                data-testid={`ac-tpl-${tpl.id}`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={tpl.imageUrl} alt="" />
                <span>{tpl.title}</span>
              </button>
            ))}
          </div>
        </div>
        <div>
          <p className="ac-ws__block-label">{t('right.recommendedAssets')}</p>
          <div className="ac-ws__asset-grid">
            {ASSETS.slice(0, 2).map((asset) => (
              <button
                key={asset.id}
                type="button"
                className="ac-ws__asset-card"
                onClick={() => showToast(asset.name)}
              >
                <div className="ac-ws__asset-thumb">
                  {asset.thumbUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={asset.thumbUrl} alt="" />
                  ) : (
                    <IhIcon name="sparkles" size={18} />
                  )}
                </div>
                <div className="ac-ws__asset-meta">
                  <strong>{asset.name}</strong>
                  <span>{asset.ext}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
        <div>
          <p className="ac-ws__block-label">{t('right.recentOutputs')}</p>
          <ul className="ac-ws__output-list">
            {OUTPUTS.slice(0, 2).map((out) => (
              <li key={out.id} className="ac-ws__output-item">
                <span className="ac-ws__output-icon">
                  <IhIcon name={out.icon} size={14} />
                </span>
                <div>
                  <strong>{out.title}</strong>
                  <span>
                    {out.type} · {out.timeLabel}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </>
    );
  }

  const rightDetail = (
    <aside className="ac-ws__right" aria-label={t('right.aria')} data-testid="ac-right">
      <div className="ac-ws__detail-tabs" role="tablist">
        {DETAIL_TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={detailTab === tab}
            className={`ac-ws__detail-tab${detailTab === tab ? ' is-active' : ''}`}
            onClick={() => setDetailTab(tab)}
            data-testid={`ac-detail-tab-${tab}`}
          >
            {t(`right.tabs.${tab}`)}
          </button>
        ))}
      </div>
      <div className="ac-ws__detail-body">{renderDetailBody()}</div>
    </aside>
  );

  const inlineRightRail = showInlineRail ? (
    <nav
      className="cs-fw__rail cs-fw__rail--right"
      data-testid="ac-rail"
      aria-label={t('rail.aria')}
    >
      {acRightRail.map((item) => {
        const isActive = activeRail === item.id;
        return (
          <button
            key={item.id}
            type="button"
            className={['cs-fw__rail-btn', isActive ? 'is-active' : '']
              .filter(Boolean)
              .join(' ')}
            data-testid={`ac-rail-${item.id}`}
            title={item.label ?? tFocus(`rails.${item.labelKey}`)}
            aria-label={item.label ?? tFocus(`rails.${item.labelKey}`)}
            aria-pressed={isActive}
            onClick={() => handleRail(item.id as RailActionId)}
          >
            <IhIcon name={item.icon} size={16} />
          </button>
        );
      })}
    </nav>
  ) : null;

  const rightPanel = showInlineRail ? (
    <div className="ac-ws__right-shell">
      {rightDetail}
      {inlineRightRail}
    </div>
  ) : (
    rightDetail
  );

  const bottomActionToolbar = (
    <CsBottomActionToolbar
      testId="ac-bat"
      primary={{
        label: t('bottomBar.actions.addComponent'),
        icon: 'plus',
        onClick: () => handleBottom('addComponent'),
        testId: 'ac-action-addComponent',
      }}
      actions={BOTTOM_ACTIONS.filter((a) => a.key !== 'addComponent').map((action) => ({
        key: action.key,
        icon: action.icon,
        label: t(`bottomBar.actions.${action.key}`),
        onClick: () => handleBottom(action.key),
        testId: `ac-action-${action.key}`,
      }))}
    />
  );

  return (
    <main className="dashboard" data-testid="ai-chat-page">
      <div className="ac-ws" data-testid="ac-workspace">
        <header className="ac-ws__header cs-page-header">
          <div className="ac-ws__header-main">
            <div>
              <Link href={AC_HOME as Route} className="ac-ws__back">
                <IhIcon name="chevronLeft" size={12} />
                {t('back')}
              </Link>
              <nav aria-label={t('breadcrumbAria')}>
                <ol className="ac-ws__breadcrumb">
                  <li>
                    <Link href={AC_HOME as Route}>{t('creativeStudio')}</Link>
                  </li>
                  <li className="ac-ws__breadcrumb-sep" aria-hidden="true">
                    /
                  </li>
                  <li className="ac-ws__breadcrumb-current" aria-current="page">
                    {tTools('aiChat.title')}
                  </li>
                </ol>
              </nav>
              <h1>
                <span className="ac-ws__title-icon" aria-hidden="true">
                  <IhIcon name="sparkles" size={22} />
                </span>
                {tTools('aiChat.title')}
              </h1>
              <p className="ac-ws__subtitle cs-page-header__subtitle">{t('subtitle')}</p>
            </div>
            <div
              className="ac-ws__models"
              role="tablist"
              aria-label={t('modelsAria')}
              data-testid="ac-models"
            >
              {MODELS.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  role="tab"
                  aria-selected={modelId === m.id}
                  className={`ac-ws__model-tab${modelId === m.id ? ' is-active' : ''}`}
                  onClick={() => {
                    setModelId(m.id);
                    setComposerModel(m.id);
                  }}
                  data-testid={`ac-model-${m.id}`}
                >
                  {t(`models.${m.labelKey}`)}
                </button>
              ))}
            </div>
          </div>
          <div className="ac-ws__header-right">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleNewChat}
              data-testid="ac-new-chat"
            >
              <IhIcon name="plus" size={12} />
              {t('actions.newChat')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleUpload}
              data-testid="ac-upload"
            >
              <IhIcon name="inbox" size={12} />
              {t('actions.upload')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              className="ac-ws__create-btn"
              onClick={handleCreate}
              data-testid="ac-create"
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
          layoutClassName="ac-ws__layout"
          leftRail={acLeftRail}
          rightRail={acRightRail}
          onRightRailSelect={(id) => {
            if ((RAIL_ACTIONS.map((a) => a.id) as string[]).includes(id)) {
              handleRail(id as RailActionId);
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
          testId="ac-dock"
        />

        {toast ? (
          <div className="ac-ws__toast" role="status" data-testid="ac-toast">
            {toast}
          </div>
        ) : null}
      </div>
    </main>
  );
}
