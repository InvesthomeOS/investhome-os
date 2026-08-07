'use client';

import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  QUICK_AI_ACTIONS,
  type AiActionKey,
  type WbAsset,
  type WbProject,
  type WbVersion,
} from './website-builder-model';

export type WbLeftRailId = 'brief' | 'assets' | 'brand' | 'settings' | 'advanced';
export type WbRightRailId = 'score' | 'suggestions' | 'quickActions' | 'export' | 'history';

type CollapseProps = {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  testId?: string;
};

function RailCollapse({ title, open, onToggle, children, testId }: CollapseProps) {
  return (
    <section className="wb-ws__collapse" data-testid={testId}>
      <button
        type="button"
        className="wb-ws__collapse-trigger"
        aria-expanded={open}
        onClick={onToggle}
      >
        <span>{title}</span>
        <IhIcon name={open ? 'chevronDown' : 'chevronRight'} size={12} />
      </button>
      {open ? <div className="wb-ws__collapse-body">{children}</div> : null}
    </section>
  );
}

function Field({
  id,
  label,
  children,
}: {
  id?: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="wb-ws__prop">
      <label htmlFor={id}>{label}</label>
      {children}
    </div>
  );
}

function MetricRow({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  const tone = value >= 80 ? 'success' : value >= 65 ? 'info' : 'warning';
  return (
    <div className="wb-ws__rail-metric" data-testid="wb-rail-metric">
      <div className="wb-ws__rail-metric-head">
        <span>{label}</span>
        <StatusChip tone={tone}>{value}</StatusChip>
      </div>
      <div className="wb-ws__rail-metric-bar" aria-hidden="true">
        <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

export type WbLeftRailDrawerProps = {
  id: WbLeftRailId;
  project: WbProject;
  brief: string;
  setBrief: (v: string) => void;
  language: string;
  setLanguage: (v: string) => void;
  tone: string;
  setTone: (v: string) => void;
  ctaPrimary: string;
  setCtaPrimary: (v: string) => void;
  ctaSecondary: string;
  setCtaSecondary: (v: string) => void;
  goal: string;
  setGoal: (v: string) => void;
  audience: string;
  setAudience: (v: string) => void;
  mainMessage: string;
  setMainMessage: (v: string) => void;
  openGroups: Record<string, boolean>;
  toggleGroup: (key: string) => void;
  selectedAssets: string[];
  toggleAsset: (id: string) => void;
  /** Media Library (or sample fallback) assets for the Assets rail. */
  libraryAssets: WbAsset[];
  onUploadAsset?: () => void;
  uploadingAsset?: boolean;
  mediaStatus?: 'idle' | 'loading' | 'ready' | 'error';
  onRetryMedia?: () => void;
  device: string;
  setDevice: (v: 'desktop' | 'tablet' | 'mobile') => void;
  metaTitle: string;
  setMetaTitle: (v: string) => void;
  metaDesc: string;
  setMetaDesc: (v: string) => void;
  slug: string;
  setSlug: (v: string) => void;
};

export function WbLeftRailDrawer(props: WbLeftRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.websiteBuilder');
  const { id, openGroups, toggleGroup } = props;

  if (id === 'brief') {
    return (
      <div className="wb-ws__rail-panel" data-testid="wb-rail-left-brief">
        <div className="wb-ws__rail-panel-head">
          <h2>{t('rails.brief.title')}</h2>
          <StatusChip tone="info">{props.project.name}</StatusChip>
        </div>
        <div className="wb-ws__rail-panel-body">
          <RailCollapse
            title={t('rails.brief.groups.goal')}
            open={openGroups['brief-goal'] !== false}
            onToggle={() => toggleGroup('brief-goal')}
            testId="wb-rail-brief-goal"
          >
            <Field id="wb-rail-project" label={t('fields.project')}>
              <span>{props.project.name}</span>
            </Field>
            <Field id="wb-rail-goal" label={t('rails.brief.goal')}>
              <textarea
                id="wb-rail-goal"
                rows={2}
                value={props.goal}
                onChange={(e) => props.setGoal(e.target.value)}
              />
            </Field>
          </RailCollapse>
          <RailCollapse
            title={t('rails.brief.groups.audience')}
            open={!!openGroups['brief-audience']}
            onToggle={() => toggleGroup('brief-audience')}
            testId="wb-rail-brief-audience"
          >
            <Field id="wb-rail-audience" label={t('rails.brief.audience')}>
              <textarea
                id="wb-rail-audience"
                rows={2}
                value={props.audience}
                onChange={(e) => props.setAudience(e.target.value)}
              />
            </Field>
            <Field id="wb-rail-message" label={t('rails.brief.message')}>
              <textarea
                id="wb-rail-message"
                rows={2}
                value={props.mainMessage}
                onChange={(e) => props.setMainMessage(e.target.value)}
              />
            </Field>
          </RailCollapse>
          <RailCollapse
            title={t('rails.brief.groups.cta')}
            open={!!openGroups['brief-cta']}
            onToggle={() => toggleGroup('brief-cta')}
            testId="wb-rail-brief-cta"
          >
            <Field id="wb-rail-cta-primary" label={t('fields.ctaPrimary')}>
              <input
                id="wb-rail-cta-primary"
                value={props.ctaPrimary}
                onChange={(e) => props.setCtaPrimary(e.target.value)}
              />
            </Field>
            <Field id="wb-rail-cta-secondary" label={t('fields.ctaSecondary')}>
              <input
                id="wb-rail-cta-secondary"
                value={props.ctaSecondary}
                onChange={(e) => props.setCtaSecondary(e.target.value)}
              />
            </Field>
            <Field id="wb-rail-lang" label={t('fields.language')}>
              <select
                id="wb-rail-lang"
                value={props.language}
                onChange={(e) => props.setLanguage(e.target.value)}
              >
                <option value="tr">{t('options.language.tr')}</option>
                <option value="en">{t('options.language.en')}</option>
                <option value="bi">{t('options.language.bi')}</option>
              </select>
            </Field>
            <Field id="wb-rail-tone" label={t('fields.tone')}>
              <select
                id="wb-rail-tone"
                value={props.tone}
                onChange={(e) => props.setTone(e.target.value)}
              >
                <option value="luxury">{t('options.tone.luxury')}</option>
                <option value="investor">{t('options.tone.investor')}</option>
                <option value="corporate">{t('options.tone.corporate')}</option>
                <option value="simple">{t('options.tone.simple')}</option>
              </select>
            </Field>
          </RailCollapse>
          <RailCollapse
            title={t('rails.brief.groups.instructions')}
            open={!!openGroups['brief-ai']}
            onToggle={() => toggleGroup('brief-ai')}
            testId="wb-rail-brief-ai"
          >
            <Field id="wb-rail-brief" label={t('rails.brief.instructions')}>
              <textarea
                id="wb-rail-brief"
                rows={4}
                value={props.brief}
                onChange={(e) => props.setBrief(e.target.value)}
              />
            </Field>
          </RailCollapse>
        </div>
      </div>
    );
  }

  if (id === 'assets') {
    const library = props.libraryAssets ?? [];
    const byKinds = (...kinds: WbAsset['kind'][]) =>
      library.filter((a) => kinds.includes(a.kind));
    const groups: Array<{ key: string; title: string; defaultOpen?: boolean; items: WbAsset[] }> = [
      {
        key: 'images',
        title: t('rails.assets.groups.images'),
        defaultOpen: true,
        items: byKinds('images', 'logos'),
      },
      {
        key: 'videos',
        title: t('rails.assets.groups.videos'),
        items: byKinds('videos'),
      },
      {
        key: 'plans',
        title: t('rails.assets.groups.plans'),
        items: byKinds('floorPlans', 'dwg'),
      },
      {
        key: 'docs',
        title: t('rails.assets.groups.docs'),
        items: byKinds('pdf', 'documents', 'brochure', 'investorDeck', 'word', 'powerpoint'),
      },
      {
        key: 'library',
        title: t('rails.assets.groups.library'),
        items: byKinds('brand', 'logos'),
      },
    ];
    return (
      <div className="wb-ws__rail-panel" data-testid="wb-rail-left-assets">
        <div className="wb-ws__rail-panel-head">
          <h2>{t('rails.assets.title')}</h2>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={props.uploadingAsset}
            onClick={() => props.onUploadAsset?.()}
          >
            <IhIcon name="plus" size={12} />
            {props.uploadingAsset ? t('rails.assets.uploading') : t('rails.assets.upload')}
          </Button>
        </div>
        <div className="wb-ws__rail-panel-body">
          <p className="wb-ws__muted">{t('rails.assets.gallery', { project: props.project.name })}</p>
          {props.mediaStatus === 'error' ? (
            <p className="wb-ws__muted">
              {t('rails.assets.loadFailed')}{' '}
              <button type="button" className="wb-ws__asset-action" onClick={() => props.onRetryMedia?.()}>
                {t('rails.assets.retry')}
              </button>
            </p>
          ) : null}
          {props.mediaStatus === 'loading' && library.length === 0 ? (
            <p className="wb-ws__muted">{t('rails.assets.loading')}</p>
          ) : null}
          {groups.map((g) => {
            const open = openGroups[`assets-${g.key}`] ?? !!g.defaultOpen;
            return (
              <RailCollapse
                key={g.key}
                title={`${g.title} (${g.items.length})`}
                open={open}
                onToggle={() => toggleGroup(`assets-${g.key}`)}
                testId={`wb-rail-assets-${g.key}`}
              >
                <ul className="wb-ws__rail-asset-list">
                  {g.items.length === 0 ? (
                    <li className="wb-ws__muted">{t('rails.assets.empty')}</li>
                  ) : (
                    g.items.map((asset) => {
                      const selected = props.selectedAssets.includes(asset.id);
                      return (
                        <li key={asset.id}>
                          <button
                            type="button"
                            className={`wb-ws__rail-asset${selected ? ' is-selected' : ''}`}
                            aria-pressed={selected}
                            onClick={() => props.toggleAsset(asset.id)}
                          >
                            <span className="wb-ws__rail-asset-name">{asset.filename}</span>
                            <span className="wb-ws__rail-asset-meta">
                              {selected
                                ? t('rails.assets.inUse')
                                : t('rails.assets.available')}
                            </span>
                          </button>
                        </li>
                      );
                    })
                  )}
                </ul>
              </RailCollapse>
            );
          })}
        </div>
      </div>
    );
  }

  if (id === 'brand') {
    return (
      <div className="wb-ws__rail-panel" data-testid="wb-rail-left-brand">
        <div className="wb-ws__rail-panel-head">
          <h2>{t('rails.brand.title')}</h2>
          <StatusChip tone="success">{t('rails.brand.compliant')}</StatusChip>
        </div>
        <div className="wb-ws__rail-panel-body">
          <RailCollapse
            title={t('rails.brand.groups.logo')}
            open={openGroups['brand-logo'] !== false}
            onToggle={() => toggleGroup('brand-logo')}
          >
            <Field label={t('rails.brand.logo')}>
              <span>Investhome master logo</span>
            </Field>
            <Field label={t('rails.brand.watermark')}>
              <span>{t('rails.brand.watermarkOff')}</span>
            </Field>
          </RailCollapse>
          <RailCollapse
            title={t('rails.brand.groups.colors')}
            open={!!openGroups['brand-colors']}
            onToggle={() => toggleGroup('brand-colors')}
          >
            <Field label={t('fields.colors')}>
              <div className="wb-ws__color-row">
                <span className="wb-ws__swatch wb-ws__swatch--navy" />
                <span className="wb-ws__swatch wb-ws__swatch--cyan" />
                <span className="wb-ws__swatch wb-ws__swatch--ink" />
                <span className="wb-ws__swatch wb-ws__swatch--surface" />
              </div>
            </Field>
          </RailCollapse>
          <RailCollapse
            title={t('rails.brand.groups.type')}
            open={!!openGroups['brand-type']}
            onToggle={() => toggleGroup('brand-type')}
          >
            <Field label={t('fields.typography')}>
              <span>{t('options.typography')}</span>
            </Field>
            <Field label={t('fields.buttons')}>
              <span>{t('options.buttons')}</span>
            </Field>
          </RailCollapse>
          <RailCollapse
            title={t('rails.brand.groups.style')}
            open={!!openGroups['brand-style']}
            onToggle={() => toggleGroup('brand-style')}
          >
            <Field label={t('rails.brand.iconStyle')}>
              <span>{t('rails.brand.iconStyleValue')}</span>
            </Field>
            <Field label={t('rails.brand.imageTreatment')}>
              <span>{t('rails.brand.imageTreatmentValue')}</span>
            </Field>
          </RailCollapse>
          <RailCollapse
            title={t('rails.brand.groups.protect')}
            open={!!openGroups['brand-protect']}
            onToggle={() => toggleGroup('brand-protect')}
          >
            <div className="wb-ws__asset-usage">
              <p className="wb-ws__asset-usage-title">{t('rails.brand.compliance')}</p>
              <p className="wb-ws__muted">{t('rails.brand.complianceOk')}</p>
            </div>
          </RailCollapse>
        </div>
      </div>
    );
  }

  if (id === 'settings') {
    return (
      <div className="wb-ws__rail-panel" data-testid="wb-rail-left-settings">
        <div className="wb-ws__rail-panel-head">
          <h2>{t('rails.settings.title')}</h2>
        </div>
        <div className="wb-ws__rail-panel-body">
          <RailCollapse
            title={t('rails.settings.groups.view')}
            open={openGroups['settings-view'] !== false}
            onToggle={() => toggleGroup('settings-view')}
          >
            <Field label={t('rails.settings.device')}>
              <div className="wb-ws__chip-row">
                {(['desktop', 'tablet', 'mobile'] as const).map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={`wb-ws__chip${props.device === d ? ' is-active' : ''}`}
                    onClick={() => props.setDevice(d)}
                  >
                    {t(`canvas.device.${d}`)}
                  </button>
                ))}
              </div>
            </Field>
            <Field label={t('rails.settings.pageWidth')}>
              <span>{t('rails.settings.pageWidthValue')}</span>
            </Field>
            <Field label={t('rails.settings.canvasBg')}>
              <span>{t('rails.settings.canvasBgValue')}</span>
            </Field>
          </RailCollapse>
          <RailCollapse
            title={t('rails.settings.groups.grid')}
            open={!!openGroups['settings-grid']}
            onToggle={() => toggleGroup('settings-grid')}
          >
            <Field label={t('rails.settings.grid')}>
              <span>{t('rails.settings.gridValue')}</span>
            </Field>
            <Field label={t('rails.settings.spacing')}>
              <span>{t('options.spacing')}</span>
            </Field>
          </RailCollapse>
          <RailCollapse
            title={t('rails.settings.groups.nav')}
            open={!!openGroups['settings-nav']}
            onToggle={() => toggleGroup('settings-nav')}
          >
            <Field label={t('rails.settings.header')}>
              <span>{t('rails.settings.headerValue')}</span>
            </Field>
            <Field label={t('rails.settings.stickyNav')}>
              <span>{t('rails.settings.stickyOn')}</span>
            </Field>
          </RailCollapse>
          <RailCollapse
            title={t('rails.settings.groups.preview')}
            open={!!openGroups['settings-preview']}
            onToggle={() => toggleGroup('settings-preview')}
          >
            <Field label={t('rails.settings.previewPrefs')}>
              <span>{t('rails.settings.previewPrefsValue')}</span>
            </Field>
            <Field label={t('rails.settings.a11y')}>
              <span>{t('rails.settings.a11yValue')}</span>
            </Field>
          </RailCollapse>
        </div>
      </div>
    );
  }

  // advanced
  return (
    <div className="wb-ws__rail-panel" data-testid="wb-rail-left-advanced">
      <div className="wb-ws__rail-panel-head">
        <h2>{t('rails.advanced.title')}</h2>
      </div>
      <div className="wb-ws__rail-panel-body">
        <RailCollapse
          title={t('rails.advanced.groups.seo')}
          open={openGroups['adv-seo'] !== false}
          onToggle={() => toggleGroup('adv-seo')}
        >
          <Field id="wb-rail-meta-title" label={t('fields.metaTitle')}>
            <input
              id="wb-rail-meta-title"
              value={props.metaTitle}
              onChange={(e) => props.setMetaTitle(e.target.value)}
            />
          </Field>
          <Field id="wb-rail-meta-desc" label={t('fields.metaDescription')}>
            <textarea
              id="wb-rail-meta-desc"
              rows={3}
              value={props.metaDesc}
              onChange={(e) => props.setMetaDesc(e.target.value)}
            />
          </Field>
          <Field id="wb-rail-slug" label={t('fields.slug')}>
            <input
              id="wb-rail-slug"
              value={props.slug}
              onChange={(e) => props.setSlug(e.target.value)}
            />
          </Field>
          <Field label={t('fields.openGraph')}>
            <span>{t('options.openGraph', { project: props.project.name })}</span>
          </Field>
        </RailCollapse>
        <RailCollapse
          title={t('rails.advanced.groups.analytics')}
          open={!!openGroups['adv-analytics']}
          onToggle={() => toggleGroup('adv-analytics')}
        >
          <Field label={t('rails.advanced.tracking')}>
            <span>G-XXXX · not connected</span>
          </Field>
          <Field label={t('rails.advanced.analytics')}>
            <span>{t('rails.advanced.analyticsValue')}</span>
          </Field>
        </RailCollapse>
        <RailCollapse
          title={t('rails.advanced.groups.integrations')}
          open={!!openGroups['adv-integrations']}
          onToggle={() => toggleGroup('adv-integrations')}
        >
          <Field label={t('rails.advanced.crm')}>
            <span>{t('rails.advanced.crmValue')}</span>
          </Field>
          <Field label={t('rails.advanced.forms')}>
            <span>{t('rails.advanced.formsValue')}</span>
          </Field>
        </RailCollapse>
        <RailCollapse
          title={t('rails.advanced.groups.code')}
          open={!!openGroups['adv-code']}
          onToggle={() => toggleGroup('adv-code')}
        >
          <Field label={t('rails.advanced.customCode')}>
            <span>{t('rails.advanced.customCodeValue')}</span>
          </Field>
        </RailCollapse>
        <RailCollapse
          title={t('rails.advanced.groups.tech')}
          open={!!openGroups['adv-tech']}
          onToggle={() => toggleGroup('adv-tech')}
        >
          <Field label={t('rails.advanced.techPublish')}>
            <span>{t('rails.advanced.techPublishValue')}</span>
          </Field>
        </RailCollapse>
      </div>
    </div>
  );
}

export type WbRightRailDrawerProps = {
  id: WbRightRailId;
  project: WbProject;
  scores: {
    overall: number;
    seo: number;
    brand: number;
    readability: number;
    mobile: number;
    performance: number;
    conversion: number;
  };
  suggestions: Array<{
    id: string;
    title: string;
    severity: 'high' | 'medium' | 'low';
    category: string;
    explanation: string;
  }>;
  onApplySuggestion: (id: string) => void;
  onDismissSuggestion: (id: string) => void;
  onApplyAll: () => void;
  onQuickAction: (key: AiActionKey | string) => void;
  onPreview: () => void;
  onPublish: () => void;
  onSaveVersion: () => void;
  publishStatus: string;
  versions: WbVersion[];
  activeVersionId: string;
  onRestoreVersion: (id: string) => void;
};

export function WbRightRailDrawer(props: WbRightRailDrawerProps) {
  const t = useTranslations('creativeStudio.ds.websiteBuilder');
  const { id } = props;

  if (id === 'score') {
    return (
      <div className="wb-ws__rail-panel" data-testid="wb-rail-right-score">
        <div className="wb-ws__rail-panel-head">
          <h2>{t('rails.score.title')}</h2>
          <StatusChip tone="success">{props.scores.overall}</StatusChip>
        </div>
        <div className="wb-ws__rail-panel-body">
          <MetricRow label={t('rails.score.overall')} value={props.scores.overall} />
          <MetricRow label={t('rails.score.seo')} value={props.scores.seo} />
          <MetricRow label={t('rails.score.brand')} value={props.scores.brand} />
          <MetricRow label={t('rails.score.readability')} value={props.scores.readability} />
          <MetricRow label={t('rails.score.mobile')} value={props.scores.mobile} />
          <MetricRow label={t('rails.score.performance')} value={props.scores.performance} />
          <MetricRow label={t('rails.score.conversion')} value={props.scores.conversion} />
        </div>
      </div>
    );
  }

  if (id === 'suggestions') {
    return (
      <div className="wb-ws__rail-panel" data-testid="wb-rail-right-suggestions">
        <div className="wb-ws__rail-panel-head">
          <h2>{t('rails.suggestions.title')}</h2>
          <Button type="button" size="sm" variant="secondary" onClick={props.onApplyAll}>
            {t('rails.suggestions.applyAll')}
          </Button>
        </div>
        <div className="wb-ws__rail-panel-body">
          {props.suggestions.map((s) => (
            <article key={s.id} className="wb-ws__rail-suggestion" data-testid={`wb-suggestion-${s.id}`}>
              <div className="wb-ws__rail-suggestion-head">
                <strong>{s.title}</strong>
                <StatusChip tone={s.severity === 'high' ? 'warning' : 'info'}>
                  {t(`rails.suggestions.severity.${s.severity}`)}
                </StatusChip>
              </div>
              <p className="wb-ws__muted">
                {s.category} · {s.explanation}
              </p>
              <div className="wb-ws__rail-suggestion-actions">
                <Button
                  type="button"
                  size="sm"
                  variant="primary"
                  onClick={() => props.onApplySuggestion(s.id)}
                >
                  {t('rails.suggestions.apply')}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => props.onDismissSuggestion(s.id)}
                >
                  {t('rails.suggestions.dismiss')}
                </Button>
              </div>
            </article>
          ))}
        </div>
      </div>
    );
  }

  if (id === 'quickActions') {
    const actions: Array<{ key: string; label: string; icon: (typeof QUICK_AI_ACTIONS)[number]['icon'] }> = [
      { key: 'hero', label: t('rails.quick.hero'), icon: 'design' },
      { key: 'rewrite', label: t('rails.quick.rewrite'), icon: 'documents' },
      { key: 'cta', label: t('rails.quick.cta'), icon: 'quickAction' },
      { key: 'image', label: t('rails.quick.image'), icon: 'inventory' },
      { key: 'addSection', label: t('rails.quick.addSection'), icon: 'plus' },
      { key: 'mobile', label: t('rails.quick.mobile'), icon: 'projects' },
      { key: 'seo', label: t('rails.quick.seo'), icon: 'trendingUp' },
      { key: 'conversion', label: t('rails.quick.conversion'), icon: 'sparkles' },
      { key: 'background', label: t('rails.quick.background'), icon: 'design' },
    ];
    return (
      <div className="wb-ws__rail-panel" data-testid="wb-rail-right-quick">
        <div className="wb-ws__rail-panel-head">
          <h2>{t('rails.quick.title')}</h2>
        </div>
        <div className="wb-ws__rail-panel-body wb-ws__rail-quick-grid">
          {actions.map((a) => (
            <Button
              key={a.key}
              type="button"
              size="sm"
              variant="secondary"
              className="wb-ws__rail-quick-btn"
              onClick={() => props.onQuickAction(a.key)}
              data-testid={`wb-rail-quick-${a.key}`}
            >
              <IhIcon name={a.icon} size={14} />
              {a.label}
            </Button>
          ))}
        </div>
      </div>
    );
  }

  if (id === 'export') {
    return (
      <div className="wb-ws__rail-panel" data-testid="wb-rail-right-export">
        <div className="wb-ws__rail-panel-head">
          <h2>{t('rails.export.title')}</h2>
          <StatusChip tone="info">{props.publishStatus}</StatusChip>
        </div>
        <div className="wb-ws__rail-panel-body">
          <div className="wb-ws__rail-export-actions">
            <Button type="button" size="sm" variant="secondary" onClick={props.onPreview}>
              <IhIcon name="design" size={14} />
              {t('preview')}
            </Button>
            <Button type="button" size="sm" variant="primary" onClick={props.onPublish}>
              <IhIcon name="inbox" size={14} />
              {t('publish')}
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={props.onSaveVersion}>
              {t('rails.export.saveVersion')}
            </Button>
            <Button type="button" size="sm" variant="secondary">
              {t('rails.export.share')}
            </Button>
            <Button type="button" size="sm" variant="secondary">
              {t('rails.export.html')}
            </Button>
          </div>
          <div className="wb-ws__publish-card">
            <div className="wb-ws__publish-row">
              <span>{t('rails.export.deploy')}</span>
              <span>{t('rails.export.deployReady')}</span>
            </div>
            <div className="wb-ws__publish-row">
              <span>{t('rails.export.domain')}</span>
              <span>investhome.com</span>
            </div>
            <div className="wb-ws__publish-row">
              <span>{t('fields.status')}</span>
              <span>{props.publishStatus}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // history
  return (
    <div className="wb-ws__rail-panel" data-testid="wb-rail-right-history">
      <div className="wb-ws__rail-panel-head">
        <h2>{t('rails.history.title')}</h2>
      </div>
      <div className="wb-ws__rail-panel-body">
        <ul className="wb-ws__rail-history-list">
          {props.versions.map((v) => {
            const current = v.id === props.activeVersionId;
            return (
              <li
                key={v.id}
                className={`wb-ws__rail-history-item${current ? ' is-current' : ''}`}
                data-testid={`wb-history-${v.id}`}
              >
                <div>
                  <strong>
                    {v.label}
                    {current ? ` · ${t('rails.history.current')}` : ''}
                  </strong>
                  <p className="wb-ws__muted">
                    {v.updatedAt} · {v.status}
                    {v.comment ? ` · ${v.comment}` : ''}
                  </p>
                </div>
                {!current ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => props.onRestoreVersion(v.id)}
                  >
                    {t('rails.history.restore')}
                  </Button>
                ) : null}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
