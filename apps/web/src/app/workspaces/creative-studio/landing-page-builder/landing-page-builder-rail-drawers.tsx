'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import {
  CsMediaPicker,
  type CsImageRef,
  type UseCsMediaLibraryResult,
} from '../_components';

import {
  COMPONENT_LIBRARY,
  STYLE_PRESETS,
  type CampaignBrief,
  type ConversionScores,
  type LpbLeftRailId,
  type LpbPage,
  type LpbRightRailId,
  type LpbTemplate,
  scoreTone,
} from './landing-page-builder-model';
import { LpbZoomControls } from './lpb-zoom-controls';

type LocalRailProps = {
  side: 'left' | 'right';
  items: { id: string; icon: IhIconName; label: string }[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function LpbLocalRail({ side, items, activeId, onSelect }: LocalRailProps) {
  return (
    <div
      className={`lpb-ws__local-rail lpb-ws__local-rail--${side} cs-local-rail`}
      role="tablist"
      aria-orientation="vertical"
      data-testid={`lpb-local-rail-${side}`}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={activeId === item.id}
          className={`lpb-ws__local-rail-btn cs-local-rail-btn${activeId === item.id ? ' is-active' : ''}`}
          title={item.label}
          aria-label={item.label}
          data-testid={`lpb-local-rail-${side}-${item.id}`}
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
    <label className="lpb-ws__field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export type LpbLeftRailDrawerProps = {
  id: LpbLeftRailId;
  templates: LpbTemplate[];
  onInsertComponent: (key: string) => void;
  onApplyTemplate: (type: string) => void;
  media: UseCsMediaLibraryResult;
  linkedProjectId?: string | null;
  coverAssetId?: string | null;
  onSelectMediaAsset: (ref: CsImageRef) => void;
  onToast: (msg: string) => void;
};

export function LpbLeftRailDrawer(props: LpbLeftRailDrawerProps) {
  const { id } = props;
  if (id === 'components') return <ComponentsDrawer {...props} />;
  if (id === 'templates') return <TemplatesDrawer {...props} />;
  if (id === 'media') return <MediaDrawer {...props} />;
  if (id === 'styles') return <StylesDrawer {...props} />;
  return <SettingsDrawer {...props} />;
}

function ComponentsDrawer({ onInsertComponent }: LpbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.landingPageBuilder');
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();

  return (
    <div className="lpb-ws__rail-panel" data-testid="lpb-rail-left-components">
      <div className="lpb-ws__rail-panel-head">
        <h2>{t('rails.components.title')}</h2>
        <StatusChip tone="info">{t('left.ready')}</StatusChip>
      </div>
      <div className="lpb-ws__rail-panel-body lpb-ws__left-stack">
        <label className="lpb-ws__search">
          <IhIcon name="search" size={12} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('rails.components.search')}
            aria-label={t('rails.components.search')}
            data-testid="lpb-component-search"
          />
        </label>
        {COMPONENT_LIBRARY.map((group) => {
          const items = group.items.filter((item) => {
            if (!q) return true;
            return t(`rails.components.items.${item.key}`).toLowerCase().includes(q);
          });
          if (items.length === 0) return null;
          return (
            <div key={group.group} className="lpb-ws__comp-group">
              <p className="lpb-ws__section-label">{t(`rails.components.groups.${group.group}`)}</p>
              <div className="lpb-ws__component-grid">
                {items.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    className="lpb-ws__component-card"
                    data-testid={`lpb-component-${item.key}`}
                    onClick={() => onInsertComponent(item.key)}
                  >
                    <span className="lpb-ws__component-card-icon">
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

function TemplatesDrawer({ templates, onApplyTemplate }: LpbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.landingPageBuilder');

  return (
    <div className="lpb-ws__rail-panel" data-testid="lpb-rail-left-templates">
      <div className="lpb-ws__rail-panel-head">
        <h2>{t('rails.templates.title')}</h2>
      </div>
      <div className="lpb-ws__rail-panel-body">
        <p className="lpb-ws__muted">{t('rails.templates.help')}</p>
        <div className="lpb-ws__template-row">
          {templates.map((tpl) => (
            <button
              key={tpl.id}
              type="button"
              className="lpb-ws__template"
              data-testid={`lpb-template-${tpl.id}`}
              onClick={() => onApplyTemplate(tpl.type)}
            >
              <span className="lpb-ws__template-swatch" style={{ background: tpl.tint }} />
              <span>{t(`templates.types.${tpl.type}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function MediaDrawer({
  media,
  linkedProjectId,
  coverAssetId,
  onSelectMediaAsset,
}: LpbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.landingPageBuilder');
  const tPicker = useTranslations('creativeStudio.mediaPicker');

  return (
    <div className="lpb-ws__rail-panel" data-testid="lpb-rail-left-media">
      <div className="lpb-ws__rail-panel-head">
        <h2>{t('rails.media.title')}</h2>
      </div>
      <div className="lpb-ws__rail-panel-body">
        <p className="lpb-ws__muted">{t('rails.media.help')}</p>
        <CsMediaPicker
          media={media}
          variant="inline"
          linkedProjectId={linkedProjectId}
          lockLinkedProject
          selectedAssetId={coverAssetId ?? null}
          onSelect={(ref) => onSelectMediaAsset(ref)}
          allowUpload
          testId="lpb-media-picker"
          labels={{
            title: tPicker('chooseAsset'),
            chooseAsset: tPicker('chooseAsset'),
            upload: tPicker('upload'),
          }}
        />
      </div>
    </div>
  );
}

function StylesDrawer({ onToast }: LpbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.landingPageBuilder');
  const [active, setActive] = useState('navy');

  return (
    <div className="lpb-ws__rail-panel" data-testid="lpb-rail-left-styles">
      <div className="lpb-ws__rail-panel-head">
        <h2>{t('rails.styles.title')}</h2>
      </div>
      <div className="lpb-ws__rail-panel-body lpb-ws__left-stack">
        <p className="lpb-ws__muted">{t('rails.styles.help')}</p>
        <p className="lpb-ws__section-label">{t('rails.styles.palette')}</p>
        <div className="lpb-ws__design-swatches" role="list">
          {STYLE_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className={`lpb-ws__swatch-btn${active === preset.id ? ' is-active' : ''}`}
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

function SettingsDrawer({ onToast }: LpbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.landingPageBuilder');

  return (
    <div className="lpb-ws__rail-panel" data-testid="lpb-rail-left-settings">
      <div className="lpb-ws__rail-panel-head">
        <h2>{t('rails.settings.title')}</h2>
      </div>
      <div className="lpb-ws__rail-panel-body lpb-ws__left-stack">
        <p className="lpb-ws__muted">{t('rails.settings.help')}</p>
        <label className="lpb-ws__toggle-row">
          <span>{t('rails.settings.autoSave')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="lpb-ws__toggle-row">
          <span>{t('rails.settings.gridSnap')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="lpb-ws__toggle-row">
          <span>{t('rails.settings.showGuides')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onToast(t('rails.settings.resetToast'))}
        >
          {t('rails.settings.reset')}
        </Button>
      </div>
    </div>
  );
}

export type LpbRightRailDrawerProps = {
  id: LpbRightRailId;
  brief: CampaignBrief;
  setBrief: (updater: (prev: CampaignBrief) => CampaignBrief) => void;
  pages: LpbPage[];
  selectedPageId: string;
  scores: ConversionScores;
  pageName: string;
  setPageName: (v: string) => void;
  pageUrl: string;
  setPageUrl: (v: string) => void;
  contentWidth: number;
  setContentWidth: (v: number) => void;
  showHeader: boolean;
  setShowHeader: (v: boolean) => void;
  showFooter: boolean;
  setShowFooter: (v: boolean) => void;
  seoTitle: string;
  setSeoTitle: (v: string) => void;
  seoDescription: string;
  setSeoDescription: (v: string) => void;
  seoKeywords: string;
  setSeoKeywords: (v: string) => void;
  bgMode: 'color' | 'image' | 'video';
  setBgMode: (v: 'color' | 'image' | 'video') => void;
  markDirty: () => void;
  onToast: (msg: string) => void;
};

export function LpbRightRailDrawer(props: LpbRightRailDrawerProps) {
  const { id } = props;
  if (id === 'page') return <PageDrawer {...props} />;
  if (id === 'style') return <StyleDrawer {...props} />;
  return <AdvancedDrawer {...props} />;
}

function PageDrawer({
  pageName,
  setPageName,
  pageUrl,
  setPageUrl,
  contentWidth,
  setContentWidth,
  showHeader,
  setShowHeader,
  showFooter,
  setShowFooter,
  bgMode,
  setBgMode,
  markDirty,
  scores,
}: LpbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.landingPageBuilder');

  return (
    <div className="lpb-ws__rail-panel" data-testid="lpb-rail-right-page">
      <div className="lpb-ws__rail-panel-head">
        <h2>{t('rails.page.title')}</h2>
        <StatusChip tone={scoreTone(scores.overall)}>{scores.overall}</StatusChip>
      </div>
      <div className="lpb-ws__rail-panel-body lpb-ws__left-stack">
        <p className="lpb-ws__section-label">{t('rails.page.settingsTitle')}</p>
        <Field label={t('rails.page.pageName')}>
          <input
            value={pageName}
            onChange={(e) => {
              setPageName(e.target.value);
              markDirty();
            }}
            data-testid="lpb-page-name"
          />
        </Field>
        <Field label={t('rails.page.url')}>
          <input
            value={pageUrl}
            onChange={(e) => {
              setPageUrl(e.target.value);
              markDirty();
            }}
            data-testid="lpb-page-url"
          />
        </Field>
        <Field label={t('rails.page.pageWidth')}>
          <select defaultValue="full">
            <option value="full">{t('rails.page.widthFull')}</option>
            <option value="boxed">{t('rails.page.widthBoxed')}</option>
          </select>
        </Field>
        <Field label={t('rails.page.contentWidth')}>
          <input
            type="number"
            value={contentWidth}
            onChange={(e) => {
              setContentWidth(Number(e.target.value) || 1200);
              markDirty();
            }}
            data-testid="lpb-content-width"
          />
        </Field>
        <p className="lpb-ws__section-label">{t('rails.page.background')}</p>
        <div className="lpb-ws__bg-opts" role="group" aria-label={t('rails.page.background')}>
          {(['color', 'image', 'video'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              className={`lpb-ws__bg-opt${bgMode === mode ? ' is-active' : ''}`}
              onClick={() => {
                setBgMode(mode);
                markDirty();
              }}
            >
              {t(`rails.page.bgModes.${mode}`)}
            </button>
          ))}
        </div>
        {bgMode === 'color' ? (
          <div className="lpb-ws__color-swatch" style={{ background: '#0b1820' }} aria-hidden="true" />
        ) : null}
        <label className="lpb-ws__toggle-row">
          <span>{t('rails.page.header')}</span>
          <input
            type="checkbox"
            checked={showHeader}
            onChange={(e) => {
              setShowHeader(e.target.checked);
              markDirty();
            }}
          />
        </label>
        <label className="lpb-ws__toggle-row">
          <span>{t('rails.page.footer')}</span>
          <input
            type="checkbox"
            checked={showFooter}
            onChange={(e) => {
              setShowFooter(e.target.checked);
              markDirty();
            }}
          />
        </label>
      </div>
    </div>
  );
}

function StyleDrawer({ markDirty, onToast }: LpbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.landingPageBuilder');

  return (
    <div className="lpb-ws__rail-panel" data-testid="lpb-rail-right-style">
      <div className="lpb-ws__rail-panel-head">
        <h2>{t('rails.style.title')}</h2>
      </div>
      <div className="lpb-ws__rail-panel-body lpb-ws__left-stack">
        <p className="lpb-ws__muted">{t('rails.style.help')}</p>
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
        <label className="lpb-ws__toggle-row">
          <span>{t('rails.style.shadows')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="lpb-ws__toggle-row">
          <span>{t('rails.style.animations')}</span>
          <input type="checkbox" defaultChecked />
        </label>
      </div>
    </div>
  );
}

function AdvancedDrawer({
  seoTitle,
  setSeoTitle,
  seoDescription,
  setSeoDescription,
  seoKeywords,
  setSeoKeywords,
  scores,
  markDirty,
}: LpbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.landingPageBuilder');

  return (
    <div className="lpb-ws__rail-panel" data-testid="lpb-rail-right-advanced">
      <div className="lpb-ws__rail-panel-head">
        <h2>{t('rails.advanced.title')}</h2>
        <StatusChip tone={scoreTone(scores.seo)}>{scores.seo}</StatusChip>
      </div>
      <div className="lpb-ws__rail-panel-body lpb-ws__left-stack">
        <p className="lpb-ws__section-label">{t('rails.advanced.seoTitle')}</p>
        <Field label={t('rails.advanced.pageTitle')}>
          <input
            value={seoTitle}
            onChange={(e) => {
              setSeoTitle(e.target.value);
              markDirty();
            }}
            data-testid="lpb-seo-title"
          />
        </Field>
        <Field label={t('rails.advanced.description')}>
          <textarea
            rows={3}
            value={seoDescription}
            onChange={(e) => {
              setSeoDescription(e.target.value);
              markDirty();
            }}
            data-testid="lpb-seo-description"
          />
        </Field>
        <Field label={t('rails.advanced.keywords')}>
          <input
            value={seoKeywords}
            onChange={(e) => {
              setSeoKeywords(e.target.value);
              markDirty();
            }}
            data-testid="lpb-seo-keywords"
          />
        </Field>
        <p className="lpb-ws__section-label">{t('rails.advanced.tracking')}</p>
        <label className="lpb-ws__toggle-row">
          <span>{t('rails.advanced.analytics')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="lpb-ws__toggle-row">
          <span>{t('rails.advanced.pixel')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <Field label={t('rails.advanced.customHead')}>
          <textarea rows={2} placeholder={t('rails.advanced.customHeadPlaceholder')} />
        </Field>
      </div>
    </div>
  );
}

export type LpbZoomToolbarProps = {
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
  onPublish: () => void;
};

const ZOOM_STEP = 10;
const ZOOM_MIN = 10;
const ZOOM_MAX = 400;

export function LpbZoomToolbar({
  engine,
  canvasLocked,
  onToggleLock,
  isFullscreen,
  onToggleFullscreen,
  onPublish,
}: LpbZoomToolbarProps) {
  const t = useTranslations('creativeStudio.ds.landingPageBuilder');
  const percent = Math.round(engine.zoomPercent);

  function zoomBy(delta: number) {
    if (canvasLocked) return;
    engine.setPercent(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, percent + delta)));
  }

  return (
    <div
      className="lpb-ws__zoom-bar"
      role="toolbar"
      aria-label={t('canvas.zoomBarAria')}
      data-testid="lpb-zoom-bar"
    >
      <div className="lpb-ws__zoom-bar-modes" role="group">
        <button
          type="button"
          className={`lpb-ws__fit-btn${engine.mode === 'fit' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'fit'}
          data-testid="lpb-ftv-fit"
          disabled={canvasLocked}
          onClick={() => engine.fitToView()}
        >
          {t('canvas.fitModes.fit')}
        </button>
      </div>

      <LpbZoomControls
        percent={percent}
        disabledOut={percent <= ZOOM_MIN || canvasLocked}
        disabledIn={percent >= ZOOM_MAX || canvasLocked}
        onZoomOut={() => zoomBy(-ZOOM_STEP)}
        onZoomIn={() => zoomBy(ZOOM_STEP)}
        onReset={() => {
          if (!canvasLocked) engine.actualSize();
        }}
      />

      <label className="lpb-ws__auto-fit" data-testid="lpb-auto-fit">
        <input
          type="checkbox"
          checked={engine.autoFit}
          disabled={canvasLocked}
          onChange={(e) => engine.setAutoFit(e.target.checked)}
        />
        <span>{t('canvas.autoFit')}</span>
      </label>

      <div className="lpb-ws__toolbar-actions" role="group" aria-label={t('canvas.toolbarAria')}>
        <button
          type="button"
          className={`lpb-ws__fit-btn${canvasLocked ? ' is-active' : ''}`}
          aria-pressed={canvasLocked}
          data-testid="lpb-lock-canvas"
          onClick={onToggleLock}
        >
          {t('canvas.lockCanvas')}
        </button>

        <button
          type="button"
          className={`lpb-ws__fit-btn${isFullscreen ? ' is-active' : ''}`}
          aria-pressed={isFullscreen}
          data-testid="lpb-fullscreen-zoom"
          onClick={onToggleFullscreen}
        >
          {t('canvas.fullscreenShort')}
        </button>

        <Button
          variant="primary"
          size="sm"
          data-testid="lpb-publish"
          onClick={onPublish}
        >
          {t('publish')}
          <IhIcon name="chevronDown" size={10} />
        </Button>
      </div>
    </div>
  );
}
