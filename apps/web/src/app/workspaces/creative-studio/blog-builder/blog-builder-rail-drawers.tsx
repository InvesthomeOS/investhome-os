'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import {
  BB_TEMPLATES,
  CATEGORIES,
  COMPONENT_LIBRARY,
  STYLE_PRESETS,
  scoreTone,
  type BbLeftRailId,
  type BbRightRailId,
  type PublishStatus,
  type SeoScores,
} from './blog-builder-model';
import { BbZoomControls } from './bb-zoom-controls';

type LocalRailProps = {
  side: 'left' | 'right';
  items: { id: string; icon: IhIconName; label: string }[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function BbLocalRail({ side, items, activeId, onSelect }: LocalRailProps) {
  return (
    <div
      className={`bb-ws__local-rail bb-ws__local-rail--${side} cs-local-rail`}
      role="tablist"
      aria-orientation="vertical"
      data-testid={`bb-local-rail-${side}`}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={activeId === item.id}
          className={`bb-ws__local-rail-btn cs-local-rail-btn${activeId === item.id ? ' is-active' : ''}`}
          title={item.label}
          aria-label={item.label}
          data-testid={`bb-local-rail-${side}-${item.id}`}
          onClick={() => onSelect(item.id)}
        >
          <IhIcon name={item.icon} size={16} />
        </button>
      ))}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="bb-ws__field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export type BbLeftRailDrawerProps = {
  id: BbLeftRailId;
  onInsertComponent: (key: string) => void;
  onApplyTemplate: (type: string) => void;
  onToast: (msg: string) => void;
};

export function BbLeftRailDrawer(props: BbLeftRailDrawerProps) {
  const { id } = props;
  if (id === 'components') return <ComponentsDrawer {...props} />;
  if (id === 'templates') return <TemplatesDrawer {...props} />;
  if (id === 'styles') return <StylesDrawer {...props} />;
  return <SettingsDrawer {...props} />;
}

function ComponentsDrawer({ onInsertComponent }: BbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.blogBuilder');
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();

  return (
    <div className="bb-ws__rail-panel" data-testid="bb-rail-left-components">
      <div className="bb-ws__rail-panel-head">
        <h2>{t('rails.components.title')}</h2>
        <StatusChip tone="info">{t('left.ready')}</StatusChip>
      </div>
      <div className="bb-ws__rail-panel-body bb-ws__left-stack">
        <label className="bb-ws__search">
          <IhIcon name="search" size={12} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('rails.components.search')}
            aria-label={t('rails.components.search')}
            data-testid="bb-component-search"
          />
        </label>
        {COMPONENT_LIBRARY.map((group) => {
          const items = group.items.filter((item) => {
            if (!q) return true;
            return t(`rails.components.items.${item.key}`).toLowerCase().includes(q);
          });
          if (items.length === 0) return null;
          return (
            <div key={group.group} className="bb-ws__comp-group">
              <p className="bb-ws__section-label">{t(`rails.components.groups.${group.group}`)}</p>
              <div className="bb-ws__component-grid">
                {items.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    className="bb-ws__component-card"
                    data-testid={`bb-component-${item.key}`}
                    onClick={() => onInsertComponent(item.key)}
                  >
                    <span className="bb-ws__component-card-icon">
                      <IhIcon name={item.icon} size={14} />
                    </span>
                    <span>{t(`rails.components.items.${item.key}`)}</span>
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TemplatesDrawer({ onApplyTemplate }: BbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.blogBuilder');

  return (
    <div className="bb-ws__rail-panel" data-testid="bb-rail-left-templates">
      <div className="bb-ws__rail-panel-head">
        <h2>{t('rails.templates.title')}</h2>
      </div>
      <div className="bb-ws__rail-panel-body">
        <p className="bb-ws__muted">{t('rails.templates.help')}</p>
        <div className="bb-ws__template-row">
          {BB_TEMPLATES.map((tpl) => (
            <button
              key={tpl.id}
              type="button"
              className="bb-ws__template"
              data-testid={`bb-template-${tpl.id}`}
              onClick={() => onApplyTemplate(tpl.type)}
            >
              <span className="bb-ws__template-swatch" style={{ background: tpl.tint }} />
              <span>{t(`templates.types.${tpl.type}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function StylesDrawer({ onToast }: BbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.blogBuilder');
  const [active, setActive] = useState('navy');

  return (
    <div className="bb-ws__rail-panel" data-testid="bb-rail-left-styles">
      <div className="bb-ws__rail-panel-head">
        <h2>{t('rails.styles.title')}</h2>
      </div>
      <div className="bb-ws__rail-panel-body bb-ws__left-stack">
        <p className="bb-ws__muted">{t('rails.styles.help')}</p>
        <p className="bb-ws__section-label">{t('rails.styles.palette')}</p>
        <div className="bb-ws__design-swatches" role="list">
          {STYLE_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className={`bb-ws__swatch-btn${active === preset.id ? ' is-active' : ''}`}
              style={{ background: preset.swatch }}
              aria-label={t(`rails.styles.presets.${preset.labelKey}`)}
              aria-pressed={active === preset.id}
              onClick={() => {
                setActive(preset.id);
                onToast(t('rails.styles.applied', { name: t(`rails.styles.presets.${preset.labelKey}`) }));
              }}
            />
          ))}
        </div>
        <Field label={t('rails.styles.headingFont')}>
          <select defaultValue="display">
            <option value="display">{t('rails.styles.fonts.display')}</option>
            <option value="sans">{t('rails.styles.fonts.sans')}</option>
          </select>
        </Field>
        <Field label={t('rails.styles.bodyFont')}>
          <select defaultValue="sans">
            <option value="sans">{t('rails.styles.fonts.sans')}</option>
            <option value="serif">{t('rails.styles.fonts.serif')}</option>
          </select>
        </Field>
        <Field label={t('rails.styles.radius')}>
          <select defaultValue="8">
            <option value="4">4px</option>
            <option value="8">8px</option>
            <option value="12">12px</option>
          </select>
        </Field>
      </div>
    </div>
  );
}

function SettingsDrawer({ onToast }: BbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.blogBuilder');

  return (
    <div className="bb-ws__rail-panel" data-testid="bb-rail-left-settings">
      <div className="bb-ws__rail-panel-head">
        <h2>{t('rails.settings.title')}</h2>
      </div>
      <div className="bb-ws__rail-panel-body bb-ws__left-stack">
        <p className="bb-ws__muted">{t('rails.settings.help')}</p>
        <label className="bb-ws__toggle-row">
          <span>{t('rails.settings.autoSave')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="bb-ws__toggle-row">
          <span>{t('rails.settings.gridSnap')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="bb-ws__toggle-row">
          <span>{t('rails.settings.showGuides')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <Button variant="secondary" size="sm" onClick={() => onToast(t('rails.settings.resetToast'))}>
          {t('rails.settings.reset')}
        </Button>
      </div>
    </div>
  );
}

export type BbRightRailDrawerProps = {
  id: BbRightRailId;
  onSelectTab: (id: BbRightRailId) => void;
  postTitle: string;
  setPostTitle: (v: string) => void;
  postSlug: string;
  setPostSlug: (v: string) => void;
  postSummary: string;
  setPostSummary: (v: string) => void;
  category: string;
  setCategory: (v: string) => void;
  tags: string[];
  setTags: (updater: (prev: string[]) => string[]) => void;
  featured: boolean;
  setFeatured: (v: boolean) => void;
  coverUrl: string;
  onChangeCover?: () => void;
  onRemoveCover?: () => void;
  publishStatus: PublishStatus;
  seoTitle: string;
  setSeoTitle: (v: string) => void;
  seoDescription: string;
  setSeoDescription: (v: string) => void;
  seoKeywords: string;
  setSeoKeywords: (v: string) => void;
  scores: SeoScores;
  markDirty: () => void;
  onToast: (msg: string) => void;
};

export function BbRightRailDrawer(props: BbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.blogBuilder');

  return (
    <div className="bb-ws__rail-panel" data-testid={`bb-rail-right-${props.id}`}>
      <div className="bb-ws__rail-panel-head bb-ws__prop-tabs-head">
        <div className="bb-ws__prop-tabs" role="tablist" aria-label={t('right.aria')}>
          {(['post', 'style', 'seo'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={props.id === tab}
              className={`bb-ws__prop-tab${props.id === tab ? ' is-active' : ''}`}
              data-testid={`bb-prop-tab-${tab}`}
              onClick={() => props.onSelectTab(tab)}
            >
              {t(`rails.labels.${tab}`)}
            </button>
          ))}
        </div>
      </div>
      {props.id === 'post' ? <PostDrawer {...props} /> : null}
      {props.id === 'style' ? <StyleDrawer {...props} /> : null}
      {props.id === 'seo' ? <SeoDrawer {...props} /> : null}
    </div>
  );
}

function PostDrawer({
  postTitle,
  setPostTitle,
  postSlug,
  setPostSlug,
  postSummary,
  setPostSummary,
  category,
  setCategory,
  tags,
  setTags,
  featured,
  setFeatured,
  coverUrl,
  onChangeCover,
  onRemoveCover,
  publishStatus,
  markDirty,
  onToast,
}: BbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.blogBuilder');
  const [tagInput, setTagInput] = useState('');

  return (
    <div className="bb-ws__rail-panel-body bb-ws__left-stack" data-testid="bb-post-drawer">
      <Field label={t('rails.post.title')}>
        <input
          value={postTitle}
          onChange={(e) => {
            setPostTitle(e.target.value);
            markDirty();
          }}
          data-testid="bb-post-title"
        />
      </Field>
      <Field label={t('rails.post.slug')}>
        <input
          value={postSlug}
          onChange={(e) => {
            setPostSlug(e.target.value);
            markDirty();
          }}
          data-testid="bb-post-slug"
        />
      </Field>
      <Field label={t('rails.post.summary')}>
        <textarea
          rows={3}
          value={postSummary}
          onChange={(e) => {
            setPostSummary(e.target.value);
            markDirty();
          }}
          data-testid="bb-post-summary"
        />
      </Field>
      <p className="bb-ws__section-label">{t('rails.post.cover')}</p>
      <div className="bb-ws__featured">
        <img src={coverUrl} alt="" />
        <div className="bb-ws__featured-actions">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              markDirty();
              if (onChangeCover) onChangeCover();
              else onToast(t('toasts.imageChanged'));
            }}
          >
            {t('rails.post.changeImage')}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              markDirty();
              if (onRemoveCover) onRemoveCover();
              else onToast(t('toasts.imageRemoved'));
            }}
          >
            {t('rails.post.removeImage')}
          </Button>
        </div>
      </div>
      <Field label={t('rails.post.category')}>
        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            markDirty();
          }}
          data-testid="bb-post-category"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </Field>
      <Field label={t('rails.post.tags')}>
        <div className="bb-ws__tag-editor">
          <div className="bb-ws__keyword-chips">
            {tags.map((tag) => (
              <button
                key={tag}
                type="button"
                className="bb-ws__chip is-good"
                onClick={() => {
                  setTags((prev) => prev.filter((x) => x !== tag));
                  markDirty();
                }}
              >
                {tag} ×
              </button>
            ))}
          </div>
          <input
            value={tagInput}
            placeholder={t('rails.post.tagPlaceholder')}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key !== 'Enter') return;
              e.preventDefault();
              const value = tagInput.trim();
              if (!value || tags.includes(value)) return;
              setTags((prev) => [...prev, value]);
              setTagInput('');
              markDirty();
            }}
            data-testid="bb-post-tags"
          />
        </div>
      </Field>
      <label className="bb-ws__toggle-row">
        <span>{t('rails.post.featured')}</span>
        <input
          type="checkbox"
          checked={featured}
          onChange={(e) => {
            setFeatured(e.target.checked);
            markDirty();
          }}
          data-testid="bb-post-featured"
        />
      </label>
      <div className="bb-ws__brief-row">
        <span className="bb-ws__brief-label">{t('rails.post.status')}</span>
        <StatusChip tone={publishStatus === 'published' ? 'success' : 'default'}>
          {t(`status.${publishStatus}`)}
        </StatusChip>
      </div>
    </div>
  );
}

function StyleDrawer({ markDirty, onToast }: BbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.blogBuilder');

  return (
    <div className="bb-ws__rail-panel-body bb-ws__left-stack" data-testid="bb-style-drawer">
      <p className="bb-ws__muted">{t('rails.style.help')}</p>
      <Field label={t('rails.style.sectionSpacing')}>
        <select
          defaultValue="md"
          onChange={() => {
            markDirty();
            onToast(t('rails.style.updated'));
          }}
        >
          <option value="sm">{t('rails.style.spacing.sm')}</option>
          <option value="md">{t('rails.style.spacing.md')}</option>
          <option value="lg">{t('rails.style.spacing.lg')}</option>
        </select>
      </Field>
      <Field label={t('rails.style.buttonStyle')}>
        <select defaultValue="solid">
          <option value="solid">{t('rails.style.buttons.solid')}</option>
          <option value="outline">{t('rails.style.buttons.outline')}</option>
          <option value="ghost">{t('rails.style.buttons.ghost')}</option>
        </select>
      </Field>
      <Field label={t('rails.style.textAlign')}>
        <select defaultValue="left">
          <option value="left">{t('rails.style.align.left')}</option>
          <option value="center">{t('rails.style.align.center')}</option>
          <option value="right">{t('rails.style.align.right')}</option>
        </select>
      </Field>
      <label className="bb-ws__toggle-row">
        <span>{t('rails.style.shadows')}</span>
        <input type="checkbox" defaultChecked />
      </label>
      <label className="bb-ws__toggle-row">
        <span>{t('rails.style.animations')}</span>
        <input type="checkbox" defaultChecked />
      </label>
    </div>
  );
}

function SeoDrawer({
  seoTitle,
  setSeoTitle,
  seoDescription,
  setSeoDescription,
  seoKeywords,
  setSeoKeywords,
  scores,
  markDirty,
}: BbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.blogBuilder');

  return (
    <div className="bb-ws__rail-panel-body bb-ws__left-stack" data-testid="bb-seo-drawer">
      <div className="bb-ws__brief-row">
        <span className="bb-ws__brief-label">{t('rails.seo.score')}</span>
        <StatusChip tone={scoreTone(scores.overall)}>{scores.overall}</StatusChip>
      </div>
      <Field label={t('rails.seo.pageTitle')}>
        <input
          value={seoTitle}
          onChange={(e) => {
            setSeoTitle(e.target.value);
            markDirty();
          }}
          data-testid="bb-seo-title"
        />
      </Field>
      <Field label={t('rails.seo.description')}>
        <textarea
          rows={3}
          value={seoDescription}
          onChange={(e) => {
            setSeoDescription(e.target.value);
            markDirty();
          }}
          data-testid="bb-seo-description"
        />
      </Field>
      <Field label={t('rails.seo.keywords')}>
        <input
          value={seoKeywords}
          onChange={(e) => {
            setSeoKeywords(e.target.value);
            markDirty();
          }}
          data-testid="bb-seo-keywords"
        />
      </Field>
      <label className="bb-ws__toggle-row">
        <span>{t('rails.seo.schema')}</span>
        <input type="checkbox" defaultChecked />
      </label>
      <label className="bb-ws__toggle-row">
        <span>{t('rails.seo.sitemap')}</span>
        <input type="checkbox" defaultChecked />
      </label>
    </div>
  );
}

export type BbZoomToolbarProps = {
  engine: {
    mode: string;
    zoomPercent: number;
    autoFit: boolean;
    fitToView: () => void;
    actualSize: () => void;
    setPercent: (n: number) => void;
    setAutoFit: (v: boolean) => void;
  };
  canvasLocked: boolean;
  onToggleLock: () => void;
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
};

const ZOOM_STEP = 10;
const ZOOM_MIN = 10;
const ZOOM_MAX = 400;

export function BbZoomToolbar({
  engine,
  canvasLocked,
  onToggleLock,
  isFullscreen,
  onToggleFullscreen,
}: BbZoomToolbarProps) {
  const t = useTranslations('creativeStudio.ds.blogBuilder');
  const percent = Math.round(engine.zoomPercent);

  function zoomBy(delta: number) {
    if (canvasLocked) return;
    engine.setPercent(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, percent + delta)));
  }

  return (
    <div
      className="bb-ws__zoom-bar"
      role="toolbar"
      aria-label={t('canvas.zoomBarAria')}
      data-testid="bb-zoom-bar"
    >
      <div className="bb-ws__zoom-bar-modes" role="group">
        <button
          type="button"
          className={`bb-ws__fit-btn${engine.mode === 'fit' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'fit'}
          data-testid="bb-ftv-fit"
          disabled={canvasLocked}
          onClick={() => engine.fitToView()}
        >
          {t('canvas.fitModes.fit')}
        </button>
        <button
          type="button"
          className={`bb-ws__fit-btn${engine.mode === 'actual' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'actual'}
          data-testid="bb-ftv-actual"
          disabled={canvasLocked}
          onClick={() => engine.actualSize()}
        >
          {t('canvas.fitModes.actual')}
        </button>
      </div>

      <BbZoomControls
        percent={percent}
        disabledOut={percent <= ZOOM_MIN || canvasLocked}
        disabledIn={percent >= ZOOM_MAX || canvasLocked}
        onZoomOut={() => zoomBy(-ZOOM_STEP)}
        onZoomIn={() => zoomBy(ZOOM_STEP)}
        onReset={() => {
          if (!canvasLocked) engine.actualSize();
        }}
      />

      <label className="bb-ws__auto-fit" data-testid="bb-auto-fit">
        <input
          type="checkbox"
          checked={engine.autoFit}
          disabled={canvasLocked}
          onChange={(e) => engine.setAutoFit(e.target.checked)}
        />
        <span>{t('canvas.autoFit')}</span>
      </label>

      <button
        type="button"
        className={`bb-ws__fit-btn${canvasLocked ? ' is-active' : ''}`}
        aria-pressed={canvasLocked}
        data-testid="bb-lock-canvas"
        onClick={onToggleLock}
      >
        {t('canvas.lockCanvas')}
      </button>

      <button
        type="button"
        className={`bb-ws__fit-btn${isFullscreen ? ' is-active' : ''}`}
        aria-pressed={isFullscreen}
        data-testid="bb-fullscreen-zoom"
        onClick={onToggleFullscreen}
      >
        {t('canvas.fullscreenShort')}
      </button>
    </div>
  );
}
