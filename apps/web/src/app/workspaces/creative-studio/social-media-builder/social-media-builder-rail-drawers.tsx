'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import {
  BRAND_COLORS,
  COMPONENT_LIBRARY,
  FORMAT_PRESETS,
  INSPECTOR_PLATFORMS,
  SMB_TEMPLATES,
  TEMPLATE_CATEGORIES,
  formatDimensions,
  type BgMode,
  type FormatPresetKey,
  type PlatformKey,
  type SmbLeftRailId,
  type SmbRightRailId,
  type SocialPost,
  type TemplateCategoryKey,
} from './social-media-builder-model';
import { SmbZoomControls } from './smb-zoom-controls';

type LocalRailProps = {
  side: 'left' | 'right';
  items: { id: string; icon: IhIconName; label: string }[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function SmbLocalRail({ side, items, activeId, onSelect }: LocalRailProps) {
  return (
    <div
      className={`smb-ws__local-rail smb-ws__local-rail--${side} cs-local-rail`}
      role="tablist"
      aria-orientation="vertical"
      data-testid={`smb-local-rail-${side}`}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={activeId === item.id}
          className={`smb-ws__local-rail-btn cs-local-rail-btn${activeId === item.id ? ' is-active' : ''}`}
          title={item.label}
          aria-label={item.label}
          data-testid={`smb-local-rail-${side}-${item.id}`}
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
    <label className="smb-ws__field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export type SmbLeftRailDrawerProps = {
  id: SmbLeftRailId;
  onInsertComponent: (key: string) => void;
  onApplyTemplate: (format: FormatPresetKey, thumbUrl: string) => void;
  onToast: (msg: string) => void;
  /** Opens CsMediaPickerDialog — production media entry only from MediaDrawer. */
  onOpenMediaPicker?: () => void;
};

export function SmbLeftRailDrawer(props: SmbLeftRailDrawerProps) {
  const { id } = props;
  if (id === 'templates') return <TemplatesDrawer {...props} />;
  if (id === 'components') return <ComponentsDrawer {...props} />;
  if (id === 'text') return <TextDrawer {...props} />;
  if (id === 'media') return <MediaDrawer {...props} />;
  if (id === 'brand') return <BrandDrawer {...props} />;
  return <AiDrawer {...props} />;
}

function TemplatesDrawer({ onApplyTemplate }: SmbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<TemplateCategoryKey>('all');
  const q = query.trim().toLowerCase();

  const filtered = useMemo(
    () =>
      SMB_TEMPLATES.filter((tpl) => {
        if (category !== 'all' && tpl.category !== category) return false;
        if (!q) return true;
        return tpl.category.includes(q) || tpl.format.includes(q);
      }),
    [category, q],
  );

  return (
    <div className="smb-ws__rail-panel" data-testid="smb-rail-left-templates">
      <div className="smb-ws__rail-panel-head">
        <h2>{t('rails.templates.title')}</h2>
        <StatusChip tone="info">{t('left.ready')}</StatusChip>
      </div>
      <div className="smb-ws__rail-panel-body smb-ws__left-stack">
        <label className="smb-ws__search">
          <IhIcon name="search" size={12} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('rails.templates.search')}
            aria-label={t('rails.templates.search')}
            data-testid="smb-template-search"
          />
        </label>
        <Field label={t('rails.templates.category')}>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as TemplateCategoryKey)}
            data-testid="smb-template-category"
          >
            {TEMPLATE_CATEGORIES.map((key) => (
              <option key={key} value={key}>
                {t(`rails.templates.categories.${key}`)}
              </option>
            ))}
          </select>
        </Field>
        <div className="smb-ws__template-row" data-testid="smb-template-grid">
          {filtered.map((tpl) => (
            <button
              key={tpl.id}
              type="button"
              className="smb-ws__template"
              data-testid={`smb-template-${tpl.id}`}
              onClick={() => onApplyTemplate(tpl.format, tpl.thumbUrl)}
            >
              <img src={tpl.thumbUrl} alt="" />
              <span>{t(`formats.${tpl.format}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ComponentsDrawer({ onInsertComponent }: SmbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();

  return (
    <div className="smb-ws__rail-panel" data-testid="smb-rail-left-components">
      <div className="smb-ws__rail-panel-head">
        <h2>{t('rails.components.title')}</h2>
        <StatusChip tone="info">{t('left.ready')}</StatusChip>
      </div>
      <div className="smb-ws__rail-panel-body smb-ws__left-stack">
        <label className="smb-ws__search">
          <IhIcon name="search" size={12} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('rails.components.search')}
            aria-label={t('rails.components.search')}
            data-testid="smb-component-search"
          />
        </label>
        {COMPONENT_LIBRARY.map((group) => {
          const items = group.items.filter((item) => {
            if (!q) return true;
            return t(`rails.components.items.${item.key}`).toLowerCase().includes(q);
          });
          if (items.length === 0) return null;
          return (
            <div key={group.group} className="smb-ws__comp-group">
              <p className="smb-ws__section-label">{t(`rails.components.groups.${group.group}`)}</p>
              <div className="smb-ws__component-grid">
                {items.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    className="smb-ws__component-card"
                    data-testid={`smb-component-${item.key}`}
                    onClick={() => onInsertComponent(item.key)}
                  >
                    <span className="smb-ws__component-card-icon">
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

function TextDrawer({ onInsertComponent, onToast }: SmbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');

  return (
    <div className="smb-ws__rail-panel" data-testid="smb-rail-left-text">
      <div className="smb-ws__rail-panel-head">
        <h2>{t('rails.text.title')}</h2>
      </div>
      <div className="smb-ws__rail-panel-body smb-ws__left-stack">
        <p className="smb-ws__muted">{t('rails.text.help')}</p>
        {(['title', 'text', 'iconText'] as const).map((key) => (
          <Button
            key={key}
            variant="secondary"
            size="sm"
            onClick={() => {
              onInsertComponent(key);
              onToast(t('rails.components.toasts.inserted', { name: t(`rails.components.items.${key}`) }));
            }}
          >
            <IhIcon name="documents" size={12} />
            {t(`rails.components.items.${key}`)}
          </Button>
        ))}
      </div>
    </div>
  );
}

function MediaDrawer({ onInsertComponent, onToast, onOpenMediaPicker }: SmbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');

  return (
    <div className="smb-ws__rail-panel" data-testid="smb-rail-left-media">
      <div className="smb-ws__rail-panel-head">
        <h2>{t('rails.media.title')}</h2>
      </div>
      <div className="smb-ws__rail-panel-body smb-ws__left-stack">
        <p className="smb-ws__muted">{t('rails.media.help')}</p>
        <Button
          variant="primary"
          size="sm"
          data-testid="smb-media-open-picker"
          onClick={() => {
            if (onOpenMediaPicker) onOpenMediaPicker();
            else onToast(t('rails.media.libraryUnavailable'));
          }}
        >
          <IhIcon name="inventory" size={12} />
          {t('rails.media.openLibrary')}
        </Button>
        {(['image', 'video', 'logo', 'sticker'] as const).map((key) => (
          <Button
            key={key}
            variant="secondary"
            size="sm"
            onClick={() => {
              if (key === 'image' && onOpenMediaPicker) {
                onOpenMediaPicker();
                return;
              }
              onInsertComponent(key);
              onToast(t('rails.components.toasts.inserted', { name: t(`rails.components.items.${key}`) }));
            }}
          >
            <IhIcon name="inventory" size={12} />
            {t(`rails.components.items.${key}`)}
          </Button>
        ))}
      </div>
    </div>
  );
}

function BrandDrawer({ onToast }: SmbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');

  return (
    <div className="smb-ws__rail-panel" data-testid="smb-rail-left-brand">
      <div className="smb-ws__rail-panel-head">
        <h2>{t('rails.brand.title')}</h2>
      </div>
      <div className="smb-ws__rail-panel-body smb-ws__left-stack">
        <p className="smb-ws__muted">{t('rails.brand.help')}</p>
        <p className="smb-ws__section-label">{t('rails.brand.colors')}</p>
        <div className="smb-ws__chip-row">
          {BRAND_COLORS.map((color) => (
            <button
              key={color}
              type="button"
              className="smb-ws__chip"
              style={{ background: color, color: color === '#FFFFFF' || color === '#F5F1EA' ? '#111' : '#fff' }}
              onClick={() => onToast(t('rails.brand.colorApplied', { color }))}
            >
              {color}
            </button>
          ))}
        </div>
        <Button variant="secondary" size="sm" onClick={() => onToast(t('rails.brand.kitApplied'))}>
          {t('rails.brand.applyKit')}
        </Button>
      </div>
    </div>
  );
}

function AiDrawer({ onToast }: SmbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const [prompt, setPrompt] = useState('');

  return (
    <div className="smb-ws__rail-panel" data-testid="smb-rail-left-ai">
      <div className="smb-ws__rail-panel-head">
        <h2>{t('rails.ai.title')}</h2>
        <StatusChip tone="info">{t('left.ready')}</StatusChip>
      </div>
      <div className="smb-ws__rail-panel-body smb-ws__left-stack">
        <p className="smb-ws__muted">{t('rails.ai.help')}</p>
        <Field label={t('rails.ai.prompt')}>
          <textarea
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={t('rails.ai.placeholder')}
            data-testid="smb-ai-prompt"
          />
        </Field>
        <Button
          variant="primary"
          size="sm"
          data-testid="smb-ai-generate"
          onClick={() => {
            onToast(t('rails.ai.generated'));
            setPrompt('');
          }}
        >
          <IhIcon name="sparkles" size={12} />
          {t('rails.ai.generate')}
        </Button>
      </div>
    </div>
  );
}

export type SmbRightRailDrawerProps = {
  id: SmbRightRailId;
  onSelectTab: (id: SmbRightRailId) => void;
  post: SocialPost;
  patchPost: (patch: Partial<SocialPost>) => void;
  formatPreset: FormatPresetKey;
  setFormatPreset: (v: FormatPresetKey) => void;
  platforms: Set<PlatformKey>;
  togglePlatform: (key: PlatformKey) => void;
  brandLogo: boolean;
  setBrandLogo: (v: boolean) => void;
  bgMode: BgMode;
  setBgMode: (v: BgMode) => void;
  markDirty: () => void;
  onToast: (msg: string) => void;
};

export function SmbRightRailDrawer(props: SmbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');

  return (
    <div className="smb-ws__rail-panel" data-testid={`smb-rail-right-${props.id}`}>
      <div className="smb-ws__rail-panel-head smb-ws__prop-tabs-head">
        <div className="smb-ws__prop-tabs" role="tablist" aria-label={t('right.aria')}>
          {(['content', 'style', 'settings'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={props.id === tab}
              className={`smb-ws__prop-tab${props.id === tab ? ' is-active' : ''}`}
              data-testid={`smb-prop-tab-${tab}`}
              onClick={() => props.onSelectTab(tab)}
            >
              {t(`rails.labels.${tab}`)}
            </button>
          ))}
        </div>
      </div>
      {props.id === 'content' ? <ContentDrawer {...props} /> : null}
      {props.id === 'style' ? <StyleDrawer {...props} /> : null}
      {props.id === 'settings' ? <SettingsDrawer {...props} /> : null}
    </div>
  );
}

function ContentDrawer({
  post,
  patchPost,
  formatPreset,
  setFormatPreset,
  platforms,
  togglePlatform,
  brandLogo,
  setBrandLogo,
  bgMode,
  setBgMode,
  markDirty,
  onToast,
}: SmbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const size = FORMAT_PRESETS.find((f) => f.key === formatPreset) ?? FORMAT_PRESETS[0]!;

  return (
    <div className="smb-ws__rail-panel-body smb-ws__left-stack" data-testid="smb-content-drawer">
      <p className="smb-ws__section-label">{t('rails.content.postSettings')}</p>
      <div className="smb-ws__platform-icons" role="group" aria-label={t('rails.content.platformsAria')}>
        {INSPECTOR_PLATFORMS.map((p) => (
          <button
            key={p.key}
            type="button"
            className={`smb-ws__platform-icon-btn${platforms.has(p.key) ? ' is-active' : ''}`}
            aria-pressed={platforms.has(p.key)}
            title={t(`platforms.${p.key}`)}
            data-testid={`smb-platform-${p.key}`}
            onClick={() => {
              togglePlatform(p.key);
              markDirty();
            }}
          >
            <IhIcon name={p.icon} size={14} />
          </button>
        ))}
      </div>

      <Field label={t('rails.content.size')}>
        <select
          value={formatPreset}
          onChange={(e) => {
            const next = e.target.value as FormatPresetKey;
            setFormatPreset(next);
            const dims = FORMAT_PRESETS.find((f) => f.key === next)!;
            patchPost({ formatPreset: next, width: dims.width, height: dims.height });
            markDirty();
          }}
          data-testid="smb-content-size"
        >
          {FORMAT_PRESETS.map((f) => (
            <option key={f.key} value={f.key}>
              {t(`formats.${f.key}`)} ({formatDimensions(f.width, f.height)})
            </option>
          ))}
        </select>
      </Field>

      <Field label={t('rails.content.postName')}>
        <input
          value={post.name}
          onChange={(e) => {
            patchPost({ name: e.target.value });
            markDirty();
          }}
          data-testid="smb-content-name"
        />
      </Field>

      <Field label={t('rails.content.description')}>
        <textarea
          rows={3}
          value={post.description}
          onChange={(e) => {
            patchPost({ description: e.target.value });
            markDirty();
          }}
          data-testid="smb-content-description"
        />
      </Field>

      <p className="smb-ws__section-label">{t('rails.content.brandLogo')}</p>
      <div className="smb-ws__logo-row">
        <span className="smb-ws__logo-preview" aria-hidden="true">
          IH
        </span>
        <label className="smb-ws__toggle">
          <input
            type="checkbox"
            checked={brandLogo}
            onChange={(e) => {
              setBrandLogo(e.target.checked);
              markDirty();
            }}
            data-testid="smb-brand-logo-toggle"
          />
          <span>{t('rails.content.logoVisible')}</span>
        </label>
      </div>
      <div className="smb-ws__chip-row">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            markDirty();
            onToast(t('toasts.logoChanged'));
          }}
        >
          {t('rails.content.changeLogo')}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            setBrandLogo(false);
            markDirty();
            onToast(t('toasts.logoRemoved'));
          }}
        >
          {t('rails.content.removeLogo')}
        </Button>
      </div>

      <p className="smb-ws__section-label">{t('rails.content.background')}</p>
      <div className="smb-ws__bg-mode" role="group">
        {(['color', 'image', 'gradient'] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            className={bgMode === mode ? 'is-active' : undefined}
            data-testid={`smb-bg-${mode}`}
            onClick={() => {
              setBgMode(mode);
              markDirty();
            }}
          >
            {t(`rails.content.bgModes.${mode}`)}
          </button>
        ))}
      </div>
      {bgMode === 'image' ? (
        <div className="smb-ws__featured">
          <img src={post.thumbUrl} alt="" />
          <div className="smb-ws__featured-actions">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                markDirty();
                onToast(t('toasts.imageChanged'));
              }}
            >
              {t('rails.content.changeImage')}
            </Button>
          </div>
        </div>
      ) : null}
      {bgMode === 'color' ? (
        <div className="smb-ws__chip-row">
          {BRAND_COLORS.map((color) => (
            <button
              key={color}
              type="button"
              className="smb-ws__chip"
              style={{ background: color, minWidth: '1.75rem', minHeight: '1.75rem' }}
              aria-label={color}
              onClick={() => {
                markDirty();
                onToast(t('rails.brand.colorApplied', { color }));
              }}
            />
          ))}
        </div>
      ) : null}

      <details className="smb-ws__accordion">
        <summary>{t('rails.content.advanced')}</summary>
        <p className="smb-ws__muted">
          {t('rails.content.sizeHint', { size: formatDimensions(size.width, size.height) })}
        </p>
      </details>
      <details className="smb-ws__accordion">
        <summary>{t('rails.content.sharing')}</summary>
        <p className="smb-ws__muted">{t('rails.content.sharingHelp')}</p>
      </details>
    </div>
  );
}

function StyleDrawer({ markDirty, onToast }: SmbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');

  return (
    <div className="smb-ws__rail-panel-body smb-ws__left-stack" data-testid="smb-style-drawer">
      <details className="smb-ws__accordion" open>
        <summary>{t('rails.style.typography')}</summary>
        <Field label={t('rails.style.headingFont')}>
          <select
            defaultValue="sans"
            onChange={() => markDirty()}
            data-testid="smb-style-heading-font"
          >
            <option value="sans">{t('rails.style.fonts.sans')}</option>
            <option value="serif">{t('rails.style.fonts.serif')}</option>
          </select>
        </Field>
        <Field label={t('rails.style.bodyFont')}>
          <select defaultValue="sans" onChange={() => markDirty()}>
            <option value="sans">{t('rails.style.fonts.sans')}</option>
            <option value="serif">{t('rails.style.fonts.serif')}</option>
          </select>
        </Field>
      </details>
      <details className="smb-ws__accordion" open>
        <summary>{t('rails.style.overlay')}</summary>
        <Field label={t('rails.style.overlayStrength')}>
          <input type="range" min={0} max={100} defaultValue={45} onChange={() => markDirty()} />
        </Field>
      </details>
      <details className="smb-ws__accordion" open>
        <summary>{t('rails.style.brandColors')}</summary>
        <div className="smb-ws__chip-row">
          {BRAND_COLORS.map((color) => (
            <button
              key={color}
              type="button"
              className="smb-ws__chip"
              style={{ background: color, minWidth: '1.75rem', minHeight: '1.75rem' }}
              onClick={() => {
                markDirty();
                onToast(t('rails.brand.colorApplied', { color }));
              }}
            />
          ))}
        </div>
      </details>
      <details className="smb-ws__accordion">
        <summary>{t('rails.style.cta')}</summary>
        <Field label={t('rails.style.ctaLabel')}>
          <input defaultValue={t('rails.style.ctaDefault')} onChange={() => markDirty()} />
        </Field>
      </details>
    </div>
  );
}

function SettingsDrawer({ onToast }: SmbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');

  return (
    <div className="smb-ws__rail-panel-body smb-ws__left-stack" data-testid="smb-settings-drawer">
      <details className="smb-ws__accordion" open>
        <summary>{t('rails.settings.platform')}</summary>
        <p className="smb-ws__muted">{t('rails.settings.platformHelp')}</p>
        <label className="smb-ws__toggle-row">
          <span>{t('rails.settings.safeArea')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="smb-ws__toggle-row">
          <span>{t('rails.settings.autoCaption')}</span>
          <input type="checkbox" defaultChecked />
        </label>
      </details>
      <details className="smb-ws__accordion" open>
        <summary>{t('rails.settings.export')}</summary>
        <Field label={t('rails.settings.exportFormat')}>
          <select defaultValue="png">
            <option value="png">PNG</option>
            <option value="jpg">JPG</option>
            <option value="pdf">PDF</option>
            <option value="zip">ZIP</option>
          </select>
        </Field>
        <Button variant="secondary" size="sm" onClick={() => onToast(t('toasts.downloaded'))}>
          {t('download')}
        </Button>
      </details>
      <details className="smb-ws__accordion">
        <summary>{t('rails.settings.advanced')}</summary>
        <label className="smb-ws__toggle-row">
          <span>{t('rails.settings.gridSnap')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="smb-ws__toggle-row">
          <span>{t('rails.settings.showGuides')}</span>
          <input type="checkbox" defaultChecked />
        </label>
      </details>
    </div>
  );
}

export type SmbZoomToolbarProps = {
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

export function SmbZoomToolbar({
  engine,
  canvasLocked,
  onToggleLock,
  isFullscreen,
  onToggleFullscreen,
}: SmbZoomToolbarProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const percent = Math.round(engine.zoomPercent);

  function zoomBy(delta: number) {
    if (canvasLocked) return;
    engine.setPercent(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, percent + delta)));
  }

  return (
    <div
      className="smb-ws__zoom-bar"
      role="toolbar"
      aria-label={t('canvas.zoomBarAria')}
      data-testid="smb-zoom-bar"
    >
      <div className="smb-ws__zoom-bar-modes" role="group">
        <button
          type="button"
          className={`smb-ws__fit-btn${engine.mode === 'fit' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'fit'}
          data-testid="smb-ftv-fit"
          disabled={canvasLocked}
          onClick={() => engine.fitToView()}
        >
          {t('canvas.fitModes.fit')}
        </button>
        <button
          type="button"
          className={`smb-ws__fit-btn${engine.mode === 'actual' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'actual'}
          data-testid="smb-ftv-actual"
          disabled={canvasLocked}
          onClick={() => engine.actualSize()}
        >
          {t('canvas.fitModes.actual')}
        </button>
      </div>

      <SmbZoomControls
        percent={percent}
        disabledOut={percent <= ZOOM_MIN || canvasLocked}
        disabledIn={percent >= ZOOM_MAX || canvasLocked}
        onZoomOut={() => zoomBy(-ZOOM_STEP)}
        onZoomIn={() => zoomBy(ZOOM_STEP)}
        onReset={() => {
          if (!canvasLocked) engine.actualSize();
        }}
      />

      <label className="smb-ws__auto-fit" data-testid="smb-auto-fit">
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
        className={`smb-ws__fit-btn${canvasLocked ? ' is-active' : ''}`}
        aria-pressed={canvasLocked}
        data-testid="smb-lock-canvas"
        onClick={onToggleLock}
      >
        {t('canvas.lockCanvas')}
      </button>

      <button
        type="button"
        className={`smb-ws__fit-btn${isFullscreen ? ' is-active' : ''}`}
        aria-pressed={isFullscreen}
        data-testid="smb-fullscreen-zoom"
        onClick={onToggleFullscreen}
      >
        {t('canvas.fullscreenShort')}
      </button>
    </div>
  );
}
