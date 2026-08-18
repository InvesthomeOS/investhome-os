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
import { toColorInputValue, type SocialElement, clampFontSize, clampOpacity, nudgeFontSize, opacityToPercent, parseSocialFontWeight, parseSocialObjectFit } from './social-media-builder-elements';
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
  onApplyTemplate: (format: FormatPresetKey) => void;
  onToast: (msg: string) => void;
  /** Opens CsMediaPickerDialog — production media entry only from MediaDrawer. */
  onOpenMediaPicker?: () => void;
  /** Shared Creative Studio generation — real API, not toast demo. */
  onGenerate?: (instruction: string) => void;
  generating?: boolean;
  /** When set, non-listed component keys are disabled (honest P0 UI). */
  enabledComponentKeys?: ReadonlySet<string>;
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
              onClick={() => onApplyTemplate(tpl.format)}
            >
              {tpl.thumbUrl ? <img src={tpl.thumbUrl} alt="" /> : <span className="smb-ws__template-swatch" />}
              <span>{t(`formats.${tpl.format}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ComponentsDrawer({ onInsertComponent, enabledComponentKeys }: SmbLeftRailDrawerProps) {
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
                {items.map((item) => {
                  const enabled =
                    !enabledComponentKeys || enabledComponentKeys.has(item.key);
                  return (
                    <button
                      key={item.key}
                      type="button"
                      className="smb-ws__component-card"
                      data-testid={`smb-component-${item.key}`}
                      disabled={!enabled}
                      aria-disabled={!enabled}
                      title={enabled ? undefined : t('toasts.notAvailable')}
                      onClick={() => {
                        if (!enabled) return;
                        onInsertComponent(item.key);
                      }}
                    >
                      <span className="smb-ws__component-card-icon">
                        <IhIcon name={item.icon} size={14} />
                      </span>
                      <span>{t(`rails.components.items.${item.key}`)}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TextDrawer({ onInsertComponent, enabledComponentKeys }: SmbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');

  return (
    <div className="smb-ws__rail-panel" data-testid="smb-rail-left-text">
      <div className="smb-ws__rail-panel-head">
        <h2>{t('rails.text.title')}</h2>
      </div>
      <div className="smb-ws__rail-panel-body smb-ws__left-stack">
        <p className="smb-ws__muted">{t('rails.text.help')}</p>
        {(['title', 'text', 'iconText'] as const).map((key) => {
          const enabled = !enabledComponentKeys || enabledComponentKeys.has(key);
          return (
            <Button
              key={key}
              variant="secondary"
              size="sm"
              disabled={!enabled}
              onClick={() => {
                if (!enabled) return;
                onInsertComponent(key);
              }}
            >
              <IhIcon name="documents" size={12} />
              {t(`rails.components.items.${key}`)}
            </Button>
          );
        })}
      </div>
    </div>
  );
}

function MediaDrawer({
  onInsertComponent,
  onOpenMediaPicker,
  enabledComponentKeys,
}: SmbLeftRailDrawerProps) {
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
          }}
        >
          <IhIcon name="inventory" size={12} />
          {t('rails.media.openLibrary')}
        </Button>
        {(['image', 'video', 'logo', 'sticker'] as const).map((key) => {
          const enabled = !enabledComponentKeys || enabledComponentKeys.has(key);
          return (
            <Button
              key={key}
              variant="secondary"
              size="sm"
              disabled={!enabled}
              onClick={() => {
                if (!enabled) return;
                if (key === 'image' && onOpenMediaPicker) {
                  onOpenMediaPicker();
                  return;
                }
                onInsertComponent(key);
              }}
            >
              <IhIcon name="inventory" size={12} />
              {t(`rails.components.items.${key}`)}
            </Button>
          );
        })}
      </div>
    </div>
  );
}

function BrandDrawer(_props: SmbLeftRailDrawerProps) {
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
              disabled
              title={t('toasts.notAvailable')}
            >
              {color}
            </button>
          ))}
        </div>
        <Button variant="secondary" size="sm" disabled title={t('toasts.notAvailable')}>
          {t('rails.brand.applyKit')}
        </Button>
      </div>
    </div>
  );
}

function AiDrawer({ onToast, onGenerate, generating }: SmbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const [prompt, setPrompt] = useState('');

  return (
    <div className="smb-ws__rail-panel" data-testid="smb-rail-left-ai">
      <div className="smb-ws__rail-panel-head">
        <h2>{t('rails.ai.title')}</h2>
        <StatusChip tone={generating ? 'warning' : 'info'}>
          {generating ? t('aiStatus.thinking') : t('left.ready')}
        </StatusChip>
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
            disabled={generating}
          />
        </Field>
        <Button
          variant="primary"
          size="sm"
          data-testid="smb-ai-generate"
          disabled={generating}
          onClick={() => {
            const instruction = prompt.trim();
            if (!instruction) {
              onToast(t('toasts.instructionRequired'));
              return;
            }
            if (onGenerate) {
              onGenerate(instruction);
              setPrompt('');
              return;
            }
            onToast(t('toasts.generateFailed'));
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
  post: SocialPost | null;
  patchPost: (patch: Partial<SocialPost>) => void;
  selectedElement: SocialElement | null;
  patchElement: (patch: Partial<SocialElement>) => void;
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
  /** Opens CsMediaPicker scoped to linked project — Content "change image". */
  onChangeImage?: () => void;
  /** Display URL for the current cover (authenticated blob), not Unsplash. */
  coverDisplayUrl?: string;
  /** Real PNG export of the current post. */
  onDownload?: () => void;
  /** Optional: open the last Canva edit_url (advanced). Header uses the in-OS engine instead. */
  onOpenInCanva?: () => void;
  canvaBusy?: boolean;
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
  selectedElement,
  patchElement,
  formatPreset,
  setFormatPreset,
  platforms,
  togglePlatform,
  brandLogo,
  setBrandLogo,
  bgMode,
  setBgMode,
  markDirty,
  onChangeImage,
  coverDisplayUrl,
}: SmbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
  const size = FORMAT_PRESETS.find((f) => f.key === formatPreset) ?? FORMAT_PRESETS[0]!;
  const featuredSrc = coverDisplayUrl || '';

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
          value={post?.name ?? ''}
          disabled={!post}
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
          value={post?.description ?? ''}
          disabled={!post}
          onChange={(e) => {
            patchPost({ description: e.target.value });
            markDirty();
          }}
          data-testid="smb-content-description"
        />
      </Field>

      {selectedElement?.type === 'TEXT' ? (
        <>
          <p className="smb-ws__section-label">{t('rails.content.elementText')}</p>
          <Field label={t('rails.content.headline')}>
            <textarea
              rows={3}
              value={selectedElement.content}
              data-testid="smb-element-text-content"
              onChange={(e) => {
                patchElement({ content: e.target.value });
                markDirty();
              }}
            />
          </Field>
        </>
      ) : null}

      {selectedElement?.type === 'BUTTON' ? (
        <>
          <p className="smb-ws__section-label">{t('rails.content.elementButton')}</p>
          <Field label={t('rails.style.ctaLabel')}>
            <input
              value={selectedElement.label}
              data-testid="smb-element-button-label"
              onChange={(e) => {
                patchElement({ label: e.target.value });
                markDirty();
              }}
            />
          </Field>
          <Field label={t('rails.content.buttonBg')}>
            <input
              type="color"
              value={toColorInputValue(selectedElement.backgroundColor, '#ffffff')}
              data-testid="smb-element-button-bg"
              onChange={(e) => {
                patchElement({ backgroundColor: e.target.value });
                markDirty();
              }}
            />
          </Field>
          <Field label={t('rails.content.buttonTextColor')}>
            <input
              type="color"
              value={toColorInputValue(selectedElement.textColor, '#111827')}
              data-testid="smb-element-button-color"
              onChange={(e) => {
                patchElement({ textColor: e.target.value });
                markDirty();
              }}
            />
          </Field>
        </>
      ) : null}

      {!selectedElement ? (
        <p className="smb-ws__muted" data-testid="smb-content-no-selection">
          {t('rails.content.selectElementHint')}
        </p>
      ) : null}

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
        <Button variant="secondary" size="sm" disabled title={t('toasts.notAvailable')}>
          {t('rails.content.changeLogo')}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            setBrandLogo(false);
            markDirty();
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
            disabled={mode !== 'image'}
            title={mode !== 'image' ? t('toasts.notAvailable') : undefined}
            onClick={() => {
              if (mode !== 'image') return;
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
          {featuredSrc ? (
            <img src={featuredSrc} alt="" data-testid="smb-content-featured-img" />
          ) : (
            <div className="smb-ws__featured-empty" data-testid="smb-content-featured-empty">
              {t('canvas.imageEmpty')}
            </div>
          )}
          <div className="smb-ws__featured-actions">
            <Button
              variant="secondary"
              size="sm"
              data-testid="smb-content-change-image"
              onClick={() => {
                onChangeImage?.();
              }}
            >
              {t('rails.content.changeImage')}
            </Button>
          </div>
        </div>
      ) : null}

      <details className="smb-ws__accordion">
        <summary>{t('rails.content.advanced')}</summary>
        <p className="smb-ws__muted">
          {t('rails.content.sizeHint', { size: formatDimensions(size.width, size.height) })}
        </p>
      </details>
    </div>
  );
}

function StyleDrawer({ selectedElement, patchElement, markDirty }: SmbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');

  if (!selectedElement) {
    return (
      <div className="smb-ws__rail-panel-body smb-ws__left-stack" data-testid="smb-style-drawer">
        <p className="smb-ws__muted">{t('rails.style.selectLayerHint')}</p>
      </div>
    );
  }

  const patch = (next: Partial<SocialElement>) => {
    patchElement(next);
    markDirty();
  };

  const isLogo = selectedElement.type === 'IMAGE' && selectedElement.role === 'logo';
  const isImage = selectedElement.type === 'IMAGE' && !isLogo;
  const isText = selectedElement.type === 'TEXT';
  const isCta = selectedElement.type === 'BUTTON';

  return (
    <div className="smb-ws__rail-panel-body smb-ws__left-stack" data-testid="smb-style-drawer">
      {isText || isCta ? (
        <details className="smb-ws__accordion" open>
          <summary>{t('rails.style.typography')}</summary>
          {isText ? (
            <Field label={t('rails.style.fontFamily')}>
              <select
                value={selectedElement.fontFamily ?? 'sans'}
                data-testid="smb-style-font-family"
                onChange={(e) => {
                  const v = e.target.value;
                  if (v === 'sans' || v === 'serif' || v === 'system') {
                    patch({ fontFamily: v });
                  }
                }}
              >
                <option value="sans">{t('rails.style.fonts.sans')}</option>
                <option value="serif">{t('rails.style.fonts.serif')}</option>
                <option value="system">{t('rails.style.fonts.system')}</option>
              </select>
            </Field>
          ) : null}
          <Field label={t('rails.style.fontSize')}>
            <div className="smb-ws__stepper" data-testid="smb-style-font-size-stepper">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                data-testid="smb-style-font-size-dec"
                aria-label={t('rails.style.fontSizeDecrease')}
                onClick={() => {
                  const current =
                    isText
                      ? selectedElement.fontSize
                      : selectedElement.fontSize ?? Math.max(12, Math.round(selectedElement.height * 0.42));
                  patch({ fontSize: nudgeFontSize(current, -2) });
                }}
              >
                −
              </Button>
              <input
                type="number"
                min={8}
                max={200}
                value={
                  isText
                    ? Number.isFinite(selectedElement.fontSize)
                      ? selectedElement.fontSize
                      : 24
                    : selectedElement.fontSize ?? Math.max(12, Math.round(selectedElement.height * 0.42))
                }
                data-testid="smb-style-font-size"
                onChange={(e) => {
                  patch({ fontSize: clampFontSize(e.target.value, 16) });
                }}
              />
              <span className="smb-ws__stepper-unit" aria-hidden="true">
                px
              </span>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                data-testid="smb-style-font-size-inc"
                aria-label={t('rails.style.fontSizeIncrease')}
                onClick={() => {
                  const current =
                    isText
                      ? selectedElement.fontSize
                      : selectedElement.fontSize ?? Math.max(12, Math.round(selectedElement.height * 0.42));
                  patch({ fontSize: nudgeFontSize(current, 2) });
                }}
              >
                +
              </Button>
            </div>
          </Field>
          <Field label={t('rails.style.fontWeight')}>
            <select
              value={
                isText
                  ? selectedElement.fontWeight
                  : selectedElement.fontWeight ?? 'normal'
              }
              data-testid="smb-style-font-weight"
              onChange={(e) => {
                const weight = parseSocialFontWeight(e.target.value);
                patch({ fontWeight: weight });
              }}
            >
              <option value="normal">{t('rails.style.weights.normal')}</option>
              <option value="medium">{t('rails.style.weights.medium')}</option>
              <option value="semibold">{t('rails.style.weights.semibold')}</option>
              <option value="bold">{t('rails.style.weights.bold')}</option>
            </select>
          </Field>
          <Field label={t('rails.style.align')}>
            <select
              value={
                isText
                  ? selectedElement.align === 'left' || selectedElement.align === 'right'
                    ? selectedElement.align
                    : 'center'
                  : selectedElement.align === 'left' || selectedElement.align === 'right'
                    ? selectedElement.align
                    : 'center'
              }
              data-testid="smb-style-align"
              onChange={(e) => {
                const align = e.target.value;
                if (align === 'left' || align === 'center' || align === 'right') {
                  patch({ align });
                }
              }}
            >
              <option value="left">{t('floating.alignModes.left')}</option>
              <option value="center">{t('floating.alignModes.center')}</option>
              <option value="right">{t('floating.alignModes.right')}</option>
            </select>
          </Field>
          <Field label={isCta ? t('rails.content.buttonTextColor') : t('rails.style.textColor')}>
            <input
              type="color"
              value={toColorInputValue(
                isText ? selectedElement.color : selectedElement.textColor,
                isText ? '#ffffff' : '#111827',
              )}
              data-testid="smb-style-text-color"
              onChange={(e) => {
                if (isText) patch({ color: e.target.value });
                else patch({ textColor: e.target.value });
              }}
            />
          </Field>
          {isText ? (
            <>
              <Field label={t('rails.style.lineHeight')}>
                <input
                  type="number"
                  min={0.8}
                  max={3}
                  step={0.05}
                  value={selectedElement.lineHeight ?? 1.2}
                  data-testid="smb-style-line-height"
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    if (!Number.isFinite(n)) return;
                    patch({ lineHeight: Math.max(0.8, Math.min(3, n)) });
                  }}
                />
              </Field>
              <Field label={t('rails.style.letterSpacing')}>
                <input
                  type="number"
                  min={-5}
                  max={40}
                  step={0.5}
                  value={selectedElement.letterSpacing ?? 0}
                  data-testid="smb-style-letter-spacing"
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    if (!Number.isFinite(n)) return;
                    patch({ letterSpacing: Math.max(-5, Math.min(40, n)) });
                  }}
                />
              </Field>
            </>
          ) : null}
          <Field label={t('rails.style.opacity')}>
            <input
              type="number"
              min={0}
              max={100}
              value={opacityToPercent(selectedElement.opacity)}
              data-testid="smb-style-opacity"
              onChange={(e) => {
                patch({ opacity: clampOpacity(Number(e.target.value) / 100, 1) });
              }}
            />
          </Field>
        </details>
      ) : null}

      {isCta ? (
        <details className="smb-ws__accordion" open>
          <summary>{t('rails.style.cta')}</summary>
          <Field label={t('rails.content.buttonBg')}>
            <input
              type="color"
              value={toColorInputValue(selectedElement.backgroundColor, '#ffffff')}
              data-testid="smb-style-cta-bg"
              onChange={(e) => patch({ backgroundColor: e.target.value })}
            />
          </Field>
          <Field label={t('rails.style.borderRadius')}>
            <input
              type="number"
              min={0}
              max={200}
              value={selectedElement.borderRadius ?? Math.round(selectedElement.height / 2)}
              data-testid="smb-style-border-radius"
              onChange={(e) => {
                const n = Number(e.target.value);
                if (!Number.isFinite(n)) return;
                patch({ borderRadius: Math.max(0, Math.round(n)) });
              }}
            />
          </Field>
          <Field label={t('rails.style.padding')}>
            <input
              type="number"
              min={0}
              max={120}
              value={selectedElement.padding ?? 12}
              data-testid="smb-style-padding"
              onChange={(e) => {
                const n = Number(e.target.value);
                if (!Number.isFinite(n)) return;
                patch({ padding: Math.max(0, Math.round(n)) });
              }}
            />
          </Field>
        </details>
      ) : null}

      {isLogo || isImage ? (
        <details className="smb-ws__accordion" open>
          <summary>{isLogo ? t('rails.style.logo') : t('rails.style.image')}</summary>
          <Field label={isLogo ? t('rails.style.size') : t('rails.style.scale')}>
            <div className="smb-ws__stepper" data-testid="smb-style-size-stepper">
              <input
                type="number"
                min={8}
                max={4000}
                value={Math.round(selectedElement.width)}
                data-testid="smb-style-width"
                aria-label={t('rails.style.width')}
                onChange={(e) => {
                  const nextW = Math.max(8, Math.round(Number(e.target.value) || selectedElement.width));
                  if (selectedElement.lockAspectRatio !== false) {
                    const ratio = selectedElement.width / Math.max(1, selectedElement.height);
                    patch({ width: nextW, height: Math.max(8, Math.round(nextW / ratio)) });
                  } else {
                    patch({ width: nextW });
                  }
                }}
              />
              <span className="smb-ws__stepper-unit">×</span>
              <input
                type="number"
                min={8}
                max={4000}
                value={Math.round(selectedElement.height)}
                data-testid="smb-style-height"
                aria-label={t('rails.style.height')}
                onChange={(e) => {
                  const nextH = Math.max(8, Math.round(Number(e.target.value) || selectedElement.height));
                  if (selectedElement.lockAspectRatio !== false) {
                    const ratio = selectedElement.width / Math.max(1, selectedElement.height);
                    patch({ height: nextH, width: Math.max(8, Math.round(nextH * ratio)) });
                  } else {
                    patch({ height: nextH });
                  }
                }}
              />
            </div>
          </Field>
          <Field label={t('rails.style.position')}>
            <div className="smb-ws__stepper" data-testid="smb-style-position">
              <input
                type="number"
                value={Math.round(selectedElement.x)}
                data-testid="smb-style-x"
                aria-label="X"
                onChange={(e) => {
                  const n = Number(e.target.value);
                  if (!Number.isFinite(n)) return;
                  patch({ x: Math.round(n) });
                }}
              />
              <input
                type="number"
                value={Math.round(selectedElement.y)}
                data-testid="smb-style-y"
                aria-label="Y"
                onChange={(e) => {
                  const n = Number(e.target.value);
                  if (!Number.isFinite(n)) return;
                  patch({ y: Math.round(n) });
                }}
              />
            </div>
          </Field>
          {isLogo ? (
            <label className="smb-ws__toggle-row">
              <span>{t('rails.style.lockAspect')}</span>
              <input
                type="checkbox"
                checked={selectedElement.lockAspectRatio !== false}
                data-testid="smb-style-lock-aspect"
                onChange={(e) => patch({ lockAspectRatio: e.target.checked })}
              />
            </label>
          ) : (
            <Field label={t('rails.style.cropFit')}>
              <select
                value={selectedElement.objectFit ?? 'cover'}
                data-testid="smb-style-object-fit"
                onChange={(e) => {
                  const fit = parseSocialObjectFit(e.target.value);
                  if (fit) patch({ objectFit: fit });
                }}
              >
                <option value="cover">{t('rails.style.fitModes.cover')}</option>
                <option value="contain">{t('rails.style.fitModes.contain')}</option>
                <option value="fill">{t('rails.style.fitModes.fill')}</option>
              </select>
            </Field>
          )}
          <Field label={t('rails.style.opacity')}>
            <input
              type="number"
              min={0}
              max={100}
              value={opacityToPercent(selectedElement.opacity)}
              data-testid="smb-style-opacity"
              onChange={(e) => {
                patch({ opacity: clampOpacity(Number(e.target.value) / 100, 1) });
              }}
            />
          </Field>
        </details>
      ) : null}

      {!isText && !isCta && !isLogo && !isImage ? (
        <p className="smb-ws__muted">{t('rails.style.selectLayerHint')}</p>
      ) : null}
    </div>
  );
}

function SettingsDrawer({ onToast, onDownload, onOpenInCanva, canvaBusy }: SmbRightRailDrawerProps) {
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
        <Button
          variant="secondary"
          size="sm"
          data-testid="smb-settings-download"
          onClick={() => {
            if (onDownload) {
              onDownload();
              return;
            }
            onToast(t('toasts.downloadFailed'));
          }}
        >
          {t('download')}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          data-testid="smb-settings-open-in-canva"
          disabled={canvaBusy}
          onClick={() => {
            if (onOpenInCanva) {
              onOpenInCanva();
              return;
            }
            onToast(t('toasts.canvaFailed'));
          }}
        >
          {canvaBusy ? t('openingInCanva') : t('openInCanva')}
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
