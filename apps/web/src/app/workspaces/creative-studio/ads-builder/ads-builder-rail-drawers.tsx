'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

import {
  AD_STATUS_TONE,
  ADS_TEMPLATES,
  BRAND_COLORS,
  COMPONENT_LIBRARY,
  CTA_OPTIONS,
  PERFORMANCE_ESTIMATE,
  TEMPLATE_CATEGORIES,
  formatDimensions,
  type AdCreative,
  type AdFormatKey,
  type AdStatus,
  type AdsLeftRailId,
  type AdsRightRailId,
  type BgMode,
  type CtaKey,
  type TemplateCategoryKey,
} from './ads-builder-model';
import { AdsZoomControls } from './ads-zoom-controls';

type LocalRailProps = {
  side: 'left' | 'right';
  items: { id: string; icon: IhIconName; label: string }[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function AdsLocalRail({ side, items, activeId, onSelect }: LocalRailProps) {
  return (
    <div
      className={`ads-ws__local-rail ads-ws__local-rail--${side} cs-local-rail`}
      role="tablist"
      aria-orientation="vertical"
      data-testid={`ads-local-rail-${side}`}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={activeId === item.id}
          className={`ads-ws__local-rail-btn cs-local-rail-btn${activeId === item.id ? ' is-active' : ''}`}
          title={item.label}
          aria-label={item.label}
          data-testid={`ads-local-rail-${side}-${item.id}`}
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
    <label className="ads-ws__field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export type AdsLeftRailDrawerProps = {
  id: AdsLeftRailId;
  ads: AdCreative[];
  selectedAdId: string;
  onSelectAd: (ad: AdCreative) => void;
  onAddAd: () => void;
  onInsertComponent: (key: string) => void;
  onApplyTemplate: (format: AdFormatKey, thumbUrl: string) => void;
  onToast: (msg: string) => void;
};

export function AdsLeftRailDrawer(props: AdsLeftRailDrawerProps) {
  const { id } = props;
  if (id === 'ads') return <AdsListDrawer {...props} />;
  if (id === 'templates') return <TemplatesDrawer {...props} />;
  if (id === 'components') return <ComponentsDrawer {...props} />;
  if (id === 'text') return <TextDrawer {...props} />;
  if (id === 'media') return <MediaDrawer {...props} />;
  if (id === 'brand') return <BrandDrawer {...props} />;
  return <LeftSettingsDrawer {...props} />;
}

function AdsListDrawer({
  ads,
  selectedAdId,
  onSelectAd,
  onAddAd,
}: AdsLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      ads.filter((ad) => {
        if (!q) return true;
        return (
          ad.name.toLowerCase().includes(q) ||
          ad.platform.includes(q) ||
          ad.format.includes(q)
        );
      }),
    [ads, q],
  );

  return (
    <div className="ads-ws__rail-panel" data-testid="ads-rail-left-ads">
      <div className="ads-ws__rail-panel-head">
        <h2>
          {t('rails.ads.title')} ({ads.length})
        </h2>
        <button
          type="button"
          className="ads-ws__icon-btn"
          aria-label={t('rails.ads.add')}
          data-testid="ads-list-add"
          onClick={onAddAd}
        >
          <IhIcon name="plus" size={12} />
        </button>
      </div>
      <div className="ads-ws__rail-panel-body ads-ws__left-stack">
        <label className="ads-ws__search">
          <IhIcon name="search" size={12} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('rails.ads.search')}
            aria-label={t('rails.ads.search')}
            data-testid="ads-list-search"
          />
        </label>
        <div className="ads-ws__ad-list" data-testid="ads-ad-list">
          {filtered.map((ad, index) => (
            <button
              key={ad.id}
              type="button"
              className={`ads-ws__ad-card${selectedAdId === ad.id ? ' is-selected' : ''}`}
              data-testid={`ads-ad-card-${ad.id}`}
              onClick={() => onSelectAd(ad)}
            >
              <span className="ads-ws__ad-card-thumb">
                <img src={ad.thumbUrl} alt="" />
              </span>
              <span className="ads-ws__ad-card-meta">
                <strong>
                  <span className="ads-ws__ad-card-index">{index + 1}.</span> {ad.name}
                </strong>
                <span className="ads-ws__ad-card-platform">{t(`platforms.${ad.platform}`)}</span>
                <StatusChip tone={AD_STATUS_TONE[ad.status as AdStatus]}>
                  {t(`adStatus.${ad.status}`)}
                </StatusChip>
              </span>
              <span className="ads-ws__ad-card-menu" aria-hidden="true">
                ⋯
              </span>
            </button>
          ))}
        </div>
        <Button
          variant="secondary"
          size="sm"
          data-testid="ads-list-new"
          onClick={onAddAd}
        >
          <IhIcon name="plus" size={12} />
          {t('rails.ads.newAd')}
        </Button>
      </div>
    </div>
  );
}

function TemplatesDrawer({ onApplyTemplate }: AdsLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<TemplateCategoryKey>('all');
  const q = query.trim().toLowerCase();

  const filtered = useMemo(
    () =>
      ADS_TEMPLATES.filter((tpl) => {
        if (category !== 'all' && tpl.category !== category) return false;
        if (!q) return true;
        return tpl.category.includes(q) || tpl.format.includes(q);
      }),
    [category, q],
  );

  return (
    <div className="ads-ws__rail-panel" data-testid="ads-rail-left-templates">
      <div className="ads-ws__rail-panel-head">
        <h2>{t('rails.templates.title')}</h2>
        <StatusChip tone="info">{t('left.ready')}</StatusChip>
      </div>
      <div className="ads-ws__rail-panel-body ads-ws__left-stack">
        <label className="ads-ws__search">
          <IhIcon name="search" size={12} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('rails.templates.search')}
            aria-label={t('rails.templates.search')}
            data-testid="ads-template-search"
          />
        </label>
        <Field label={t('rails.templates.category')}>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as TemplateCategoryKey)}
            data-testid="ads-template-category"
          >
            {TEMPLATE_CATEGORIES.map((key) => (
              <option key={key} value={key}>
                {t(`rails.templates.categories.${key}`)}
              </option>
            ))}
          </select>
        </Field>
        <div className="ads-ws__template-row" data-testid="ads-template-grid">
          {filtered.map((tpl) => (
            <button
              key={tpl.id}
              type="button"
              className="ads-ws__template"
              data-testid={`ads-template-${tpl.id}`}
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

function ComponentsDrawer({ onInsertComponent }: AdsLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();

  return (
    <div className="ads-ws__rail-panel" data-testid="ads-rail-left-components">
      <div className="ads-ws__rail-panel-head">
        <h2>{t('rails.components.title')}</h2>
        <StatusChip tone="info">{t('left.ready')}</StatusChip>
      </div>
      <div className="ads-ws__rail-panel-body ads-ws__left-stack">
        <label className="ads-ws__search">
          <IhIcon name="search" size={12} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('rails.components.search')}
            aria-label={t('rails.components.search')}
            data-testid="ads-component-search"
          />
        </label>
        {COMPONENT_LIBRARY.map((group) => {
          const items = group.items.filter((item) => {
            if (!q) return true;
            return t(`rails.components.items.${item.key}`).toLowerCase().includes(q);
          });
          if (items.length === 0) return null;
          return (
            <div key={group.group} className="ads-ws__comp-group">
              <p className="ads-ws__section-label">{t(`rails.components.groups.${group.group}`)}</p>
              <div className="ads-ws__component-grid">
                {items.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    className="ads-ws__component-card"
                    data-testid={`ads-component-${item.key}`}
                    onClick={() => onInsertComponent(item.key)}
                  >
                    <span className="ads-ws__component-card-icon">
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

function TextDrawer({ onInsertComponent, onToast }: AdsLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');

  return (
    <div className="ads-ws__rail-panel" data-testid="ads-rail-left-text">
      <div className="ads-ws__rail-panel-head">
        <h2>{t('rails.text.title')}</h2>
      </div>
      <div className="ads-ws__rail-panel-body ads-ws__left-stack">
        <p className="ads-ws__muted">{t('rails.text.help')}</p>
        {(['title', 'text', 'cta'] as const).map((key) => (
          <Button
            key={key}
            variant="secondary"
            size="sm"
            onClick={() => {
              onInsertComponent(key);
              onToast(
                t('rails.components.toasts.inserted', {
                  name: t(`rails.components.items.${key}`),
                }),
              );
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

function MediaDrawer({ onInsertComponent, onToast }: AdsLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');

  return (
    <div className="ads-ws__rail-panel" data-testid="ads-rail-left-media">
      <div className="ads-ws__rail-panel-head">
        <h2>{t('rails.media.title')}</h2>
      </div>
      <div className="ads-ws__rail-panel-body ads-ws__left-stack">
        <p className="ads-ws__muted">{t('rails.media.help')}</p>
        {(['image', 'video', 'logo'] as const).map((key) => (
          <Button
            key={key}
            variant="secondary"
            size="sm"
            onClick={() => {
              onInsertComponent(key);
              onToast(
                t('rails.components.toasts.inserted', {
                  name: t(`rails.components.items.${key}`),
                }),
              );
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

function BrandDrawer({ onToast }: AdsLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');

  return (
    <div className="ads-ws__rail-panel" data-testid="ads-rail-left-brand">
      <div className="ads-ws__rail-panel-head">
        <h2>{t('rails.brand.title')}</h2>
      </div>
      <div className="ads-ws__rail-panel-body ads-ws__left-stack">
        <p className="ads-ws__muted">{t('rails.brand.help')}</p>
        <p className="ads-ws__section-label">{t('rails.brand.colors')}</p>
        <div className="ads-ws__chip-row">
          {BRAND_COLORS.map((color) => (
            <button
              key={color}
              type="button"
              className="ads-ws__chip"
              style={{
                background: color,
                color: color === '#FFFFFF' ? '#111' : '#fff',
              }}
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

function LeftSettingsDrawer({ onToast }: AdsLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');

  return (
    <div className="ads-ws__rail-panel" data-testid="ads-rail-left-settings">
      <div className="ads-ws__rail-panel-head">
        <h2>{t('rails.leftSettings.title')}</h2>
      </div>
      <div className="ads-ws__rail-panel-body ads-ws__left-stack">
        <p className="ads-ws__muted">{t('rails.leftSettings.help')}</p>
        <label className="ads-ws__toggle-row">
          <span>{t('rails.leftSettings.autoSave')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="ads-ws__toggle-row">
          <span>{t('rails.leftSettings.showGuides')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <Button variant="secondary" size="sm" onClick={() => onToast(t('rails.leftSettings.saved'))}>
          {t('rails.leftSettings.apply')}
        </Button>
      </div>
    </div>
  );
}

export type AdsRightRailDrawerProps = {
  id: AdsRightRailId;
  onSelectTab: (id: AdsRightRailId) => void;
  ad: AdCreative;
  patchAd: (patch: Partial<AdCreative>) => void;
  brandLogo: boolean;
  setBrandLogo: (v: boolean) => void;
  bgMode: BgMode;
  setBgMode: (v: BgMode) => void;
  markDirty: () => void;
  onToast: (msg: string) => void;
};

export function AdsRightRailDrawer(props: AdsRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');

  return (
    <div className="ads-ws__rail-panel" data-testid={`ads-rail-right-${props.id}`}>
      <div className="ads-ws__rail-panel-head ads-ws__prop-tabs-head">
        <div className="ads-ws__prop-tabs" role="tablist" aria-label={t('right.aria')}>
          {(['content', 'targeting', 'pixel', 'settings'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={props.id === tab}
              className={`ads-ws__prop-tab${props.id === tab ? ' is-active' : ''}`}
              data-testid={`ads-prop-tab-${tab}`}
              onClick={() => props.onSelectTab(tab)}
            >
              {t(`rails.labels.${tab}`)}
            </button>
          ))}
        </div>
      </div>
      {props.id === 'content' ? <ContentDrawer {...props} /> : null}
      {props.id === 'targeting' ? <TargetingDrawer {...props} /> : null}
      {props.id === 'pixel' ? <PixelDrawer {...props} /> : null}
      {props.id === 'settings' ? <SettingsDrawer {...props} /> : null}
      <PerformanceEstimate />
    </div>
  );
}

function PerformanceEstimate() {
  const t = useTranslations('creativeStudio.ds.adsBuilder');

  return (
    <div className="ads-ws__perf-card" data-testid="ads-perf-estimate">
      <h3>{t('performance.title')}</h3>
      <div className="ads-ws__perf-grid">
        <div>
          <span>{t('performance.reach')}</span>
          <strong>{PERFORMANCE_ESTIMATE.reach}</strong>
        </div>
        <div>
          <span>{t('performance.clicks')}</span>
          <strong>{PERFORMANCE_ESTIMATE.clicks}</strong>
        </div>
        <div>
          <span>{t('performance.ctr')}</span>
          <strong>{PERFORMANCE_ESTIMATE.ctr}</strong>
        </div>
      </div>
    </div>
  );
}

function ContentDrawer({
  ad,
  patchAd,
  brandLogo,
  setBrandLogo,
  bgMode,
  setBgMode,
  markDirty,
  onToast,
}: AdsRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');
  const headlineMax = 40;
  const descMax = 125;

  return (
    <div className="ads-ws__rail-panel-body ads-ws__left-stack" data-testid="ads-content-drawer">
      <Field label={`${t('rails.content.headline')} (${ad.headline.length}/${headlineMax})`}>
        <input
          value={ad.headline}
          maxLength={headlineMax}
          onChange={(e) => {
            patchAd({ headline: e.target.value });
            markDirty();
          }}
          data-testid="ads-content-headline"
        />
      </Field>

      <Field label={`${t('rails.content.description')} (${ad.description.length}/${descMax})`}>
        <textarea
          rows={3}
          value={ad.description}
          maxLength={descMax}
          onChange={(e) => {
            patchAd({ description: e.target.value });
            markDirty();
          }}
          data-testid="ads-content-description"
        />
      </Field>

      <Field label={t('rails.content.cta')}>
        <select
          value={ad.cta}
          onChange={(e) => {
            patchAd({ cta: e.target.value as CtaKey });
            markDirty();
          }}
          data-testid="ads-content-cta"
        >
          {CTA_OPTIONS.map((key) => (
            <option key={key} value={key}>
              {t(`rails.content.ctaOptions.${key}`)}
            </option>
          ))}
        </select>
      </Field>

      <Field label={t('rails.content.targetUrl')}>
        <input
          type="url"
          value={ad.targetUrl}
          onChange={(e) => {
            patchAd({ targetUrl: e.target.value });
            markDirty();
          }}
          data-testid="ads-content-url"
        />
      </Field>

      <p className="ads-ws__section-label">{t('rails.content.image')}</p>
      <div className="ads-ws__featured">
        <img src={ad.thumbUrl} alt="" />
        <div className="ads-ws__featured-actions">
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

      <p className="ads-ws__section-label">{t('rails.content.brandColors')}</p>
      <div className="ads-ws__chip-row">
        {BRAND_COLORS.map((color) => (
          <button
            key={color}
            type="button"
            className="ads-ws__chip"
            style={{ background: color, minWidth: '1.75rem', minHeight: '1.75rem' }}
            aria-label={color}
            onClick={() => {
              markDirty();
              onToast(t('rails.brand.colorApplied', { color }));
            }}
          />
        ))}
      </div>

      <p className="ads-ws__section-label">{t('rails.content.brandLogo')}</p>
      <div className="ads-ws__logo-row">
        <span className="ads-ws__logo-preview" aria-hidden="true">
          IH
        </span>
        <label className="ads-ws__toggle">
          <input
            type="checkbox"
            checked={brandLogo}
            onChange={(e) => {
              setBrandLogo(e.target.checked);
              markDirty();
            }}
            data-testid="ads-brand-logo-toggle"
          />
          <span>{t('rails.content.logoVisible')}</span>
        </label>
      </div>

      <p className="ads-ws__section-label">{t('rails.content.background')}</p>
      <div className="ads-ws__bg-mode" role="group">
        {(['color', 'image', 'gradient'] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            className={bgMode === mode ? 'is-active' : undefined}
            data-testid={`ads-bg-${mode}`}
            onClick={() => {
              setBgMode(mode);
              markDirty();
            }}
          >
            {t(`rails.content.bgModes.${mode}`)}
          </button>
        ))}
      </div>
    </div>
  );
}

function TargetingDrawer({ markDirty }: AdsRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');

  return (
    <div className="ads-ws__rail-panel-body ads-ws__left-stack" data-testid="ads-targeting-drawer">
      <p className="ads-ws__muted">{t('rails.targeting.help')}</p>
      <Field label={t('rails.targeting.audience')}>
        <select defaultValue="lookalike" onChange={() => markDirty()} data-testid="ads-targeting-audience">
          <option value="lookalike">{t('rails.targeting.audiences.lookalike')}</option>
          <option value="interest">{t('rails.targeting.audiences.interest')}</option>
          <option value="retarget">{t('rails.targeting.audiences.retarget')}</option>
          <option value="custom">{t('rails.targeting.audiences.custom')}</option>
        </select>
      </Field>
      <Field label={t('rails.targeting.locations')}>
        <input
          defaultValue={t('rails.targeting.locationsDefault')}
          onChange={() => markDirty()}
          data-testid="ads-targeting-locations"
        />
      </Field>
      <Field label={t('rails.targeting.age')}>
        <select defaultValue="25-54" onChange={() => markDirty()}>
          <option value="18-24">18–24</option>
          <option value="25-54">25–54</option>
          <option value="35-65">35–65</option>
        </select>
      </Field>
      <label className="ads-ws__toggle-row">
        <span>{t('rails.targeting.excludeConverters')}</span>
        <input type="checkbox" defaultChecked onChange={() => markDirty()} />
      </label>
    </div>
  );
}

function PixelDrawer({ markDirty, onToast }: AdsRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');

  return (
    <div className="ads-ws__rail-panel-body ads-ws__left-stack" data-testid="ads-pixel-drawer">
      <p className="ads-ws__muted">{t('rails.pixel.help')}</p>
      <Field label={t('rails.pixel.metaPixel')}>
        <input
          defaultValue="IH-META-••••9281"
          onChange={() => markDirty()}
          data-testid="ads-pixel-meta"
        />
      </Field>
      <Field label={t('rails.pixel.googleTag')}>
        <input
          defaultValue="GT-IH••••4412"
          onChange={() => markDirty()}
          data-testid="ads-pixel-google"
        />
      </Field>
      <Field label={t('rails.pixel.conversionEvent')}>
        <select defaultValue="lead" onChange={() => markDirty()}>
          <option value="lead">{t('rails.pixel.events.lead')}</option>
          <option value="view">{t('rails.pixel.events.view')}</option>
          <option value="schedule">{t('rails.pixel.events.schedule')}</option>
        </select>
      </Field>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => onToast(t('rails.pixel.verified'))}
        data-testid="ads-pixel-verify"
      >
        {t('rails.pixel.verify')}
      </Button>
    </div>
  );
}

function SettingsDrawer({ onToast, ad }: AdsRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');

  return (
    <div className="ads-ws__rail-panel-body ads-ws__left-stack" data-testid="ads-settings-drawer">
      <details className="ads-ws__accordion" open>
        <summary>{t('rails.settings.ad')}</summary>
        <p className="ads-ws__muted">
          {t('rails.settings.adHelp', {
            platform: t(`platforms.${ad.platform}`),
            format: t(`formats.${ad.format}`),
            size: formatDimensions(ad.width, ad.height),
          })}
        </p>
        <label className="ads-ws__toggle-row">
          <span>{t('rails.settings.safeArea')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="ads-ws__toggle-row">
          <span>{t('rails.settings.autoOptimize')}</span>
          <input type="checkbox" defaultChecked />
        </label>
      </details>
      <details className="ads-ws__accordion" open>
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
      <details className="ads-ws__accordion">
        <summary>{t('rails.settings.advanced')}</summary>
        <label className="ads-ws__toggle-row">
          <span>{t('rails.settings.gridSnap')}</span>
          <input type="checkbox" defaultChecked />
        </label>
        <label className="ads-ws__toggle-row">
          <span>{t('rails.settings.showGuides')}</span>
          <input type="checkbox" defaultChecked />
        </label>
      </details>
    </div>
  );
}

export type AdsZoomToolbarProps = {
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

export function AdsZoomToolbar({
  engine,
  canvasLocked,
  onToggleLock,
  isFullscreen,
  onToggleFullscreen,
}: AdsZoomToolbarProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');
  const percent = Math.round(engine.zoomPercent);

  function zoomBy(delta: number) {
    if (canvasLocked) return;
    engine.setPercent(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, percent + delta)));
  }

  return (
    <div
      className="ads-ws__zoom-bar"
      role="toolbar"
      aria-label={t('canvas.zoomBarAria')}
      data-testid="ads-zoom-bar"
    >
      <div className="ads-ws__zoom-bar-modes" role="group">
        <button
          type="button"
          className={`ads-ws__fit-btn${engine.mode === 'fit' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'fit'}
          data-testid="ads-ftv-fit"
          disabled={canvasLocked}
          onClick={() => engine.fitToView()}
        >
          {t('canvas.fitModes.fit')}
        </button>
        <button
          type="button"
          className={`ads-ws__fit-btn${engine.mode === 'actual' ? ' is-active' : ''}`}
          aria-pressed={engine.mode === 'actual'}
          data-testid="ads-ftv-actual"
          disabled={canvasLocked}
          onClick={() => engine.actualSize()}
        >
          {t('canvas.fitModes.actual')}
        </button>
      </div>

      <AdsZoomControls
        percent={percent}
        disabledOut={percent <= ZOOM_MIN || canvasLocked}
        disabledIn={percent >= ZOOM_MAX || canvasLocked}
        onZoomOut={() => zoomBy(-ZOOM_STEP)}
        onZoomIn={() => zoomBy(ZOOM_STEP)}
        onReset={() => {
          if (!canvasLocked) engine.actualSize();
        }}
      />

      <label className="ads-ws__auto-fit" data-testid="ads-auto-fit">
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
        className={`ads-ws__fit-btn${canvasLocked ? ' is-active' : ''}`}
        aria-pressed={canvasLocked}
        data-testid="ads-lock-canvas"
        onClick={onToggleLock}
      >
        {t('canvas.lockCanvas')}
      </button>

      <button
        type="button"
        className={`ads-ws__fit-btn${isFullscreen ? ' is-active' : ''}`}
        aria-pressed={isFullscreen}
        data-testid="ads-fullscreen-zoom"
        onClick={onToggleFullscreen}
      >
        {t('canvas.fullscreenShort')}
      </button>
    </div>
  );
}
