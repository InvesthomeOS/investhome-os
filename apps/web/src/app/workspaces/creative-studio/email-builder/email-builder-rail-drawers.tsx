'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import {
  COMPONENT_LIBRARY,
  EB_TEMPLATES,
  LINK_TYPE_KEYS,
  STYLE_PRESETS,
  type EbLeftRailId,
  type EbRightRailId,
  type PublishStatus,
} from './email-builder-model';
import { EbZoomControls } from './eb-zoom-controls';

type LocalRailProps = {
  side: 'left' | 'right';
  items: { id: string; icon: IhIconName; label: string }[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function EbLocalRail({ side, items, activeId, onSelect }: LocalRailProps) {
  return (
    <div
      className={`eb-ws__local-rail eb-ws__local-rail--${side} cs-local-rail`}
      role="tablist"
      aria-orientation="vertical"
      data-testid={`eb-local-rail-${side}`}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={activeId === item.id}
          className={`eb-ws__local-rail-btn cs-local-rail-btn${activeId === item.id ? ' is-active' : ''}`}
          title={item.label}
          aria-label={item.label}
          data-testid={`eb-local-rail-${side}-${item.id}`}
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
    <label className="eb-ws__field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export type EbLeftRailDrawerProps = {
  id: EbLeftRailId;
  onInsertComponent: (key: string) => void;
  onApplyTemplate: (type: string) => void;
  onToast: (msg: string) => void;
};

export function EbLeftRailDrawer(props: EbLeftRailDrawerProps) {
  const { id } = props;
  if (id === 'components') return <ComponentsDrawer {...props} />;
  if (id === 'templates') return <TemplatesDrawer {...props} />;
  if (id === 'styles') return <StylesDrawer {...props} />;
  return <LeftSettingsDrawer {...props} />;
}

function ComponentsDrawer({ onInsertComponent }: EbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.emailBuilder');
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();

  return (
    <div className="eb-ws__rail-panel" data-testid="eb-rail-left-components">
      <div className="eb-ws__rail-panel-head">
        <h2>{t('rails.components.title')}</h2>
        <StatusChip tone="info">{t('left.ready')}</StatusChip>
      </div>
      <div className="eb-ws__rail-panel-body eb-ws__left-stack">
        <label className="eb-ws__search">
          <IhIcon name="search" size={12} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('rails.components.search')}
            aria-label={t('rails.components.search')}
            data-testid="eb-component-search"
          />
        </label>
        {COMPONENT_LIBRARY.map((group) => {
          const items = group.items.filter((item) => {
            if (!q) return true;
            return t(`rails.components.items.${item.key}`).toLowerCase().includes(q);
          });
          if (items.length === 0) return null;
          return (
            <div key={group.group} className="eb-ws__comp-group">
              <p className="eb-ws__section-label">{t(`rails.components.groups.${group.group}`)}</p>
              <div className="eb-ws__component-grid">
                {items.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    className="eb-ws__component-card"
                    data-testid={`eb-component-${item.key}`}
                    onClick={() => onInsertComponent(item.key)}
                  >
                    <span className="eb-ws__component-card-icon">
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

function TemplatesDrawer({ onApplyTemplate }: EbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.emailBuilder');

  return (
    <div className="eb-ws__rail-panel" data-testid="eb-rail-left-templates">
      <div className="eb-ws__rail-panel-head">
        <h2>{t('rails.templates.title')}</h2>
      </div>
      <div className="eb-ws__rail-panel-body">
        <p className="eb-ws__muted">{t('rails.templates.help')}</p>
        <div className="eb-ws__template-row">
          {EB_TEMPLATES.map((tpl) => (
            <button
              key={tpl.id}
              type="button"
              className="eb-ws__template"
              data-testid={`eb-template-${tpl.id}`}
              onClick={() => onApplyTemplate(tpl.type)}
            >
              <span className="eb-ws__template-swatch" style={{ background: tpl.tint }} />
              <span>{t(`templates.types.${tpl.type}`)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function StylesDrawer({ onToast }: EbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.emailBuilder');
  const [active, setActive] = useState('navy');

  return (
    <div className="eb-ws__rail-panel" data-testid="eb-rail-left-styles">
      <div className="eb-ws__rail-panel-head">
        <h2>{t('rails.styles.title')}</h2>
      </div>
      <div className="eb-ws__rail-panel-body eb-ws__left-stack">
        <p className="eb-ws__muted">{t('rails.styles.help')}</p>
        <p className="eb-ws__section-label">{t('rails.styles.palette')}</p>
        <div className="eb-ws__design-swatches" role="list">
          {STYLE_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className={`eb-ws__swatch-btn${active === preset.id ? ' is-active' : ''}`}
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

function LeftSettingsDrawer({ onToast }: EbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.emailBuilder');

  return (
    <div className="eb-ws__rail-panel" data-testid="eb-rail-left-settings">
      <div className="eb-ws__rail-panel-head">
        <h2>{t('rails.settings.title')}</h2>
      </div>
      <div className="eb-ws__rail-panel-body eb-ws__left-stack">
        <p className="eb-ws__muted">{t('rails.settings.help')}</p>
        <label className="eb-ws__toggle-row">
          <span>{t('rails.settings.autoSave')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="eb-ws__toggle-row">
          <span>{t('rails.settings.gridSnap')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="eb-ws__toggle-row">
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

export type EbRightRailDrawerProps = {
  id: EbRightRailId;
  onSelectTab: (id: EbRightRailId) => void;
  subject: string;
  setSubject: (v: string) => void;
  senderName: string;
  setSenderName: (v: string) => void;
  senderEmail: string;
  setSenderEmail: (v: string) => void;
  replyTo: string;
  setReplyTo: (v: string) => void;
  previewText: string;
  setPreviewText: (v: string) => void;
  coverUrl: string;
  onChangeCover?: () => void;
  onRemoveCover?: () => void;
  linkType: string;
  setLinkType: (v: string) => void;
  linkUrl: string;
  setLinkUrl: (v: string) => void;
  heading: string;
  setHeading: (v: string) => void;
  bodyCopy: string;
  setBodyCopy: (v: string) => void;
  publishStatus: PublishStatus;
  markDirty: () => void;
  onToast: (msg: string) => void;
};

export function EbRightRailDrawer(props: EbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.emailBuilder');

  return (
    <div className="eb-ws__rail-panel" data-testid={`eb-rail-right-${props.id}`}>
      <div className="eb-ws__rail-panel-head eb-ws__prop-tabs-head">
        <div className="eb-ws__prop-tabs" role="tablist" aria-label={t('right.aria')}>
          {(['content', 'style', 'settings'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={props.id === tab}
              className={`eb-ws__prop-tab${props.id === tab ? ' is-active' : ''}`}
              data-testid={`eb-prop-tab-${tab}`}
              onClick={() => props.onSelectTab(tab)}
            >
              {t(`rails.labels.${tab}`)}
            </button>
          ))}
        </div>
      </div>
      {props.id === 'content' ? <ContentDrawer {...props} /> : null}
      {props.id === 'style' ? <StyleDrawer {...props} /> : null}
      {props.id === 'settings' ? <RightSettingsDrawer {...props} /> : null}
    </div>
  );
}

function ContentDrawer({
  subject,
  setSubject,
  senderName,
  setSenderName,
  senderEmail,
  setSenderEmail,
  replyTo,
  setReplyTo,
  previewText,
  setPreviewText,
  coverUrl,
  onChangeCover,
  onRemoveCover,
  linkType,
  setLinkType,
  linkUrl,
  setLinkUrl,
  heading,
  setHeading,
  bodyCopy,
  setBodyCopy,
  publishStatus,
  markDirty,
  onToast,
}: EbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.emailBuilder');

  return (
    <div className="eb-ws__rail-panel-body eb-ws__left-stack" data-testid="eb-content-drawer">
      <Field label={t('rails.content.subject')}>
        <input
          value={subject}
          onChange={(e) => {
            setSubject(e.target.value);
            markDirty();
          }}
          data-testid="eb-content-subject"
        />
      </Field>
      <Field label={t('rails.content.senderName')}>
        <input
          value={senderName}
          onChange={(e) => {
            setSenderName(e.target.value);
            markDirty();
          }}
          data-testid="eb-content-sender-name"
        />
      </Field>
      <Field label={t('rails.content.senderEmail')}>
        <input
          type="email"
          value={senderEmail}
          onChange={(e) => {
            setSenderEmail(e.target.value);
            markDirty();
          }}
          data-testid="eb-content-sender-email"
        />
      </Field>
      <Field label={t('rails.content.replyTo')}>
        <input
          type="email"
          value={replyTo}
          onChange={(e) => {
            setReplyTo(e.target.value);
            markDirty();
          }}
          data-testid="eb-content-reply-to"
        />
      </Field>
      <Field label={t('rails.content.previewText')}>
        <textarea
          rows={2}
          value={previewText}
          onChange={(e) => {
            setPreviewText(e.target.value);
            markDirty();
          }}
          data-testid="eb-content-preview-text"
        />
      </Field>
      <p className="eb-ws__section-label">{t('rails.content.cover')}</p>
      <div className="eb-ws__featured">
        <img src={coverUrl} alt="" />
        <div className="eb-ws__featured-actions">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              markDirty();
              if (onChangeCover) onChangeCover();
              else onToast(t('toasts.imageChanged'));
            }}
          >
            {t('rails.content.changeImage')}
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
            {t('rails.content.removeImage')}
          </Button>
        </div>
      </div>
      <p className="eb-ws__section-label">{t('rails.content.linkSettings')}</p>
      <Field label={t('rails.content.linkType')}>
        <select
          value={linkType}
          onChange={(e) => {
            setLinkType(e.target.value);
            markDirty();
          }}
          data-testid="eb-content-link-type"
        >
          {LINK_TYPE_KEYS.map((key) => (
            <option key={key} value={key}>
              {t(`rails.content.linkTypes.${key}`)}
            </option>
          ))}
        </select>
      </Field>
      <Field label={t('rails.content.linkUrl')}>
        <input
          value={linkUrl}
          onChange={(e) => {
            setLinkUrl(e.target.value);
            markDirty();
          }}
          data-testid="eb-content-link-url"
        />
      </Field>
      <Field label={t('rails.content.heading')}>
        <input
          value={heading}
          onChange={(e) => {
            setHeading(e.target.value);
            markDirty();
          }}
          data-testid="eb-content-heading"
        />
      </Field>
      <Field label={t('rails.content.body')}>
        <textarea
          rows={3}
          value={bodyCopy}
          onChange={(e) => {
            setBodyCopy(e.target.value);
            markDirty();
          }}
          data-testid="eb-content-body"
        />
      </Field>
      <div className="eb-ws__brief-row">
        <span className="eb-ws__brief-label">{t('rails.content.status')}</span>
        <StatusChip tone={publishStatus === 'published' ? 'success' : 'default'}>
          {t(`status.${publishStatus}`)}
        </StatusChip>
      </div>
    </div>
  );
}

function StyleDrawer({ markDirty, onToast }: EbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.emailBuilder');

  return (
    <div className="eb-ws__rail-panel-body eb-ws__left-stack" data-testid="eb-style-drawer">
      <p className="eb-ws__muted">{t('rails.style.help')}</p>
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
      <Field label={t('rails.style.background')}>
        <select defaultValue="white">
          <option value="white">{t('rails.style.backgrounds.white')}</option>
          <option value="soft">{t('rails.style.backgrounds.soft')}</option>
          <option value="navy">{t('rails.style.backgrounds.navy')}</option>
        </select>
      </Field>
      <Field label={t('rails.style.border')}>
        <select defaultValue="none">
          <option value="none">{t('rails.style.borders.none')}</option>
          <option value="subtle">{t('rails.style.borders.subtle')}</option>
          <option value="strong">{t('rails.style.borders.strong')}</option>
        </select>
      </Field>
      <Field label={t('rails.style.buttonStyle')}>
        <select defaultValue="solid">
          <option value="solid">{t('rails.style.buttons.solid')}</option>
          <option value="outline">{t('rails.style.buttons.outline')}</option>
          <option value="ghost">{t('rails.style.buttons.ghost')}</option>
        </select>
      </Field>
      <Field label={t('rails.style.typography')}>
        <select defaultValue="sans">
          <option value="sans">{t('rails.style.fonts.sans')}</option>
          <option value="serif">{t('rails.style.fonts.serif')}</option>
        </select>
      </Field>
      <Field label={t('rails.style.textAlign')}>
        <select defaultValue="left">
          <option value="left">{t('rails.style.align.left')}</option>
          <option value="center">{t('rails.style.align.center')}</option>
          <option value="right">{t('rails.style.align.right')}</option>
        </select>
      </Field>
      <label className="eb-ws__toggle-row">
        <span>{t('rails.style.shadows')}</span>
        <input type="checkbox" defaultChecked />
      </label>
    </div>
  );
}

function RightSettingsDrawer({ markDirty, onToast }: EbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.emailBuilder');

  return (
    <div className="eb-ws__rail-panel-body eb-ws__left-stack" data-testid="eb-settings-drawer">
      <p className="eb-ws__muted">{t('rails.blockSettings.help')}</p>
      <p className="eb-ws__section-label">{t('rails.blockSettings.visibility')}</p>
      <label className="eb-ws__toggle-row">
        <span>{t('rails.blockSettings.showDesktop')}</span>
        <input
          type="checkbox"
          defaultChecked
          onChange={() => {
            markDirty();
            onToast(t('rails.blockSettings.updated'));
          }}
        />
      </label>
      <label className="eb-ws__toggle-row">
        <span>{t('rails.blockSettings.showTablet')}</span>
        <input type="checkbox" defaultChecked />
      </label>
      <label className="eb-ws__toggle-row">
        <span>{t('rails.blockSettings.showMobile')}</span>
        <input type="checkbox" defaultChecked />
      </label>
      <Field label={t('rails.blockSettings.padding')}>
        <select defaultValue="md">
          <option value="sm">{t('rails.style.spacing.sm')}</option>
          <option value="md">{t('rails.style.spacing.md')}</option>
          <option value="lg">{t('rails.style.spacing.lg')}</option>
        </select>
      </Field>
      <Field label={t('rails.blockSettings.emailWidth')}>
        <select defaultValue="600">
          <option value="560">560px</option>
          <option value="600">600px</option>
          <option value="640">640px</option>
        </select>
      </Field>
      <label className="eb-ws__toggle-row">
        <span>{t('rails.blockSettings.preheader')}</span>
        <input type="checkbox" defaultChecked />
      </label>
    </div>
  );
}

export type EbZoomToolbarProps = {
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

export function EbZoomToolbar({
  engine,
  canvasLocked,
  onToggleLock,
  isFullscreen,
  onToggleFullscreen,
}: EbZoomToolbarProps) {
  const t = useTranslations('creativeStudio.ds.emailBuilder');
  const percent = Math.round(engine.zoomPercent);

  function zoomBy(delta: number) {
    if (canvasLocked) return;
    engine.setPercent(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, percent + delta)));
  }

  return (
    <div
      className="eb-ws__zoom-bar"
      role="toolbar"
      aria-label={t('canvas.zoomBarAria')}
      data-testid="eb-zoom-bar"
    >
      <div className="eb-ws__zoom-bar-modes" role="group">
        <button
          type="button"
          className={`eb-ws__fit-btn${engine.mode === 'fit' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'fit'}
          data-testid="eb-ftv-fit"
          disabled={canvasLocked}
          onClick={() => engine.fitToView()}
        >
          {t('canvas.fitModes.fit')}
        </button>
        <button
          type="button"
          className={`eb-ws__fit-btn${engine.mode === 'actual' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'actual'}
          data-testid="eb-ftv-actual"
          disabled={canvasLocked}
          onClick={() => engine.actualSize()}
        >
          {t('canvas.fitModes.actual')}
        </button>
      </div>

      <EbZoomControls
        percent={percent}
        disabledOut={percent <= ZOOM_MIN || canvasLocked}
        disabledIn={percent >= ZOOM_MAX || canvasLocked}
        onZoomOut={() => zoomBy(-ZOOM_STEP)}
        onZoomIn={() => zoomBy(ZOOM_STEP)}
        onReset={() => {
          if (!canvasLocked) engine.actualSize();
        }}
      />

      <label className="eb-ws__auto-fit" data-testid="eb-auto-fit">
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
        className={`eb-ws__fit-btn${canvasLocked ? ' is-active' : ''}`}
        aria-pressed={canvasLocked}
        data-testid="eb-lock-canvas"
        onClick={onToggleLock}
      >
        {t('canvas.lockCanvas')}
      </button>

      <button
        type="button"
        className={`eb-ws__fit-btn${isFullscreen ? ' is-active' : ''}`}
        aria-pressed={isFullscreen}
        data-testid="eb-fullscreen-zoom"
        onClick={onToggleFullscreen}
      >
        {t('canvas.fullscreenShort')}
      </button>
    </div>
  );
}
