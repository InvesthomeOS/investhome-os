'use client';

import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import {
  Button,
  Card,
  CardContent,
  CardHeader,
  Dialog,
  Input,
  RightRailCard,
  Select,
  StatusChip,
  Tabs,
} from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import type {
  SettingsCategoryId,
  SettingsIntegration,
  SettingsNotification,
  SettingsWorkspacePreview,
} from '../settings-model';

const STUB_CATEGORIES: SettingsCategoryId[] = ['users', 'billing', 'system'];

const SECTION_BY_CATEGORY: Partial<Record<SettingsCategoryId, SettingsCategoryId>> = {
  general: 'general',
  crm: 'crm',
  ai: 'ai',
  notifications: 'notifications',
  integrations: 'integrations',
  security: 'security',
};

type EditorKind =
  | 'overview'
  | 'general'
  | 'crm'
  | 'notifications'
  | 'ai'
  | 'integrations'
  | 'security'
  | 'rail';

type EditorTarget = {
  kind: EditorKind;
  title: string;
  entityId?: string;
};

function UsageMeter({
  label,
  used,
  limit,
  pct,
  progressLabel,
}: {
  label: string;
  used: string;
  limit: string;
  pct: number;
  progressLabel: string;
}) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div className="crm-settings__meter">
      <div className="crm-settings__meter-head">
        <span>{label}</span>
        <strong>
          {used} / {limit}
        </strong>
      </div>
      <div
        className="crm-settings__meter-track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(clamped)}
        aria-label={progressLabel}
      >
        <span style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}

function DefRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="crm-settings__def-row">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function RailFooter({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <button type="button" className="crm-settings__rail-link" onClick={onClick}>
      {label}
      <span aria-hidden="true">›</span>
    </button>
  );
}

export function CrmSettingsWorkspace({
  preview,
}: {
  preview: SettingsWorkspacePreview;
}) {
  const t = useTranslations('crm.settings');
  const tabsId = useId();
  const mainRef = useRef<HTMLDivElement>(null);
  const [activeCategory, setActiveCategory] = useState<SettingsCategoryId>('general');
  const [toast, setToast] = useState<string | null>(null);
  const [editor, setEditor] = useState<EditorTarget | null>(null);
  const [draft, setDraft] = useState(preview);
  const [generalForm, setGeneralForm] = useState(preview.general);
  const [aiForm, setAiForm] = useState(preview.ai);
  const [notifications, setNotifications] = useState(preview.notifications);
  const [integrations, setIntegrations] = useState(
    preview.integrations.filter((item) => item.id !== 'microsoft365'),
  );
  const [crmCounts, setCrmCounts] = useState(
    Object.fromEntries(preview.crmEntities.map((e) => [e.id, e.count])) as Record<string, number>,
  );
  const [securityNote, setSecurityNote] = useState('');
  const [railNote, setRailNote] = useState('');
  const [historyOpen, setHistoryOpen] = useState(false);

  const showStub = STUB_CATEGORIES.includes(activeCategory);

  const categoryTabs = preview.categories.map((category) => ({
    id: category.id,
    label: t(`nav.categories.${category.id}.label`),
  }));

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (showStub || activeCategory === 'general' || !mainRef.current) return;
    const section = SECTION_BY_CATEGORY[activeCategory];
    if (!section) return;
    const el = mainRef.current.querySelector<HTMLElement>(`[data-section="${section}"]`);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [activeCategory, showStub]);

  const openEditor = (target: EditorTarget) => {
    setEditor(target);
    setGeneralForm(draft.general);
    setAiForm(draft.ai);
    setNotifications([...draft.notifications]);
    setSecurityNote('');
    setRailNote('');
  };

  const closeEditor = () => setEditor(null);

  const saveEditor = () => {
    if (!editor) return;
    if (editor.kind === 'general' || editor.kind === 'overview') {
      setDraft((prev) => ({ ...prev, general: generalForm }));
    }
    if (editor.kind === 'ai') {
      setDraft((prev) => ({ ...prev, ai: aiForm }));
    }
    if (editor.kind === 'notifications') {
      const next = editor.entityId
        ? notifications.map((n) =>
            n.id === editor.entityId ? { ...n, enabled: !n.enabled } : n,
          )
        : notifications;
      setNotifications(next);
      setDraft((prev) => ({ ...prev, notifications: next }));
    }
    if (editor.kind === 'crm' && editor.entityId) {
      setCrmCounts((prev) => ({
        ...prev,
        [editor.entityId!]: (prev[editor.entityId!] ?? 0) + 1,
      }));
    }
    if (editor.kind === 'integrations' && editor.entityId) {
      setToast(t('integrations.status.notConfigured'));
      setEditor(null);
      return;
    }
    setToast(t('actions.saveSuccess'));
    setEditor(null);
  };

  const exportSettings = () => {
    const blob = new Blob([JSON.stringify(draft, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'crm-settings-export.json';
    a.click();
    URL.revokeObjectURL(url);
    setToast(t('actions.exportSuccess'));
  };

  const onCategoryChange = (id: string) => {
    setActiveCategory(id as SettingsCategoryId);
  };

  const focusSection = SECTION_BY_CATEGORY[activeCategory];
  const sectionClass = (id: SettingsCategoryId) =>
    `crm-settings__section${focusSection === id ? ' is-focused' : ''}`;

  const activeNotification = useMemo(
    () => notifications.find((n) => n.id === editor?.entityId) ?? null,
    [editor?.entityId, notifications],
  );
  const activeIntegration = useMemo(
    () => integrations.find((n) => n.id === editor?.entityId) ?? null,
    [editor?.entityId, integrations],
  );

  return (
    <div className="crm-settings" data-testid="crm-settings-workspace">
      {toast ? (
        <div className="crm-settings__toast" role="status" aria-live="polite">
          {toast}
        </div>
      ) : null}

      <div className="crm-settings__layout">
        <div className="crm-settings__center" ref={mainRef}>
          <section className="crm-settings__overview" aria-label={t('overview.aria')}>
            <div className="crm-settings__overview-left">
              <h1>{t('title')}</h1>
              <p>{t('overview.subtitle')}</p>
            </div>
            <div className="crm-settings__overview-actions">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setHistoryOpen(true)}
              >
                {t('overview.changeHistory')}
              </Button>
              <Button variant="secondary" size="sm" onClick={exportSettings}>
                {t('overview.export')}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() =>
                  openEditor({ kind: 'overview', title: t('overview.editSettings') })
                }
              >
                {t('overview.editSettings')}
              </Button>
            </div>
          </section>

          <div className="crm-settings__tabs-bar" id={tabsId}>
            <Tabs
              className="crm-settings__tabs"
              tabs={categoryTabs}
              activeId={activeCategory}
              onChange={onCategoryChange}
              ariaLabel={t('nav.aria')}
            />
            <div className="crm-settings__tabs-mobile">
              <Select
                className="crm-settings__tabs-select"
                aria-label={t('nav.aria')}
                value={activeCategory}
                onChange={(event) => onCategoryChange(event.target.value)}
              >
                {categoryTabs.map((tab) => (
                  <option key={tab.id} value={tab.id}>
                    {tab.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {showStub ? (
            <Card className="crm-settings__card crm-settings__card--stub">
              <CardHeader
                title={t(`nav.categories.${activeCategory}.label`)}
                description={t(`nav.categories.${activeCategory}.description`)}
              />
              <CardContent>
                <p className="crm-settings__stub-copy">{t('stub.message')}</p>
                <Button variant="secondary" size="sm" onClick={() => setActiveCategory('general')}>
                  {t('stub.cta')}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="crm-settings__config-grid">
              <div className="crm-settings__config-col crm-settings__config-col--left">
                <div data-section="general" className={sectionClass('general')}>
                  <Card className="crm-settings__card">
                    <CardHeader
                      title={t('general.title')}
                      action={
                        <Button
                          variant="secondary"
                          size="sm"
                          className="crm-settings__card-action"
                          onClick={() => openEditor({ kind: 'general', title: t('general.title') })}
                        >
                          {t('actions.edit')}
                        </Button>
                      }
                    />
                    <CardContent>
                      <dl className="crm-settings__def-grid" aria-label={t('general.title')}>
                        <DefRow label={t('general.company')}>
                          <strong>{draft.general.companyName}</strong>
                        </DefRow>
                        <DefRow label={t('general.language')}>
                          <strong>
                            {t(`general.languageOptions.${draft.general.language}`)}
                          </strong>
                        </DefRow>
                        <DefRow label={t('general.timezone')}>
                          <strong>
                            {t(`general.timezoneOptions.${draft.general.timezone}`)}
                          </strong>
                        </DefRow>
                        <DefRow label={t('general.companyId')}>
                          <strong className="crm-settings__mono">{draft.general.companyId}</strong>
                        </DefRow>
                        <DefRow label={t('general.logo')}>
                          <span className="crm-settings__logo-mark" aria-hidden="true">
                            {draft.general.logoInitials}
                          </span>
                        </DefRow>
                        <DefRow label={t('general.lastUpdated')}>
                          <strong>
                            {t(`general.lastUpdatedValues.${draft.general.lastUpdatedKey}`)}
                          </strong>
                        </DefRow>
                      </dl>
                    </CardContent>
                  </Card>
                </div>

                <div data-section="crm" className={sectionClass('crm')}>
                  <Card className="crm-settings__card">
                    <CardHeader title={t('crmSettings.title')} />
                    <CardContent>
                      <ul
                        className="crm-settings__row-list crm-settings__row-list--dense"
                        aria-label={t('crmSettings.aria')}
                      >
                        {preview.crmEntities.map((entity) => (
                          <li key={entity.id} className="crm-settings__row crm-settings__row--crm">
                            <span className="crm-settings__row-icon" aria-hidden="true">
                              <IhIcon name={entity.icon} size={13} />
                            </span>
                            <span className="crm-settings__row-copy">
                              <strong>{t(`crmSettings.entities.${entity.id}`)}</strong>
                              <em>{crmCounts[entity.id] ?? entity.count}</em>
                            </span>
                            <Button
                              variant="secondary"
                              size="sm"
                              className="crm-settings__row-action"
                              onClick={() =>
                                openEditor({
                                  kind: 'crm',
                                  title: t(`crmSettings.entities.${entity.id}`),
                                  entityId: entity.id,
                                })
                              }
                            >
                              {t('actions.manage')}
                            </Button>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </div>

                <div data-section="notifications" className={sectionClass('notifications')}>
                  <Card className="crm-settings__card">
                    <CardHeader title={t('notifications.title')} />
                    <CardContent>
                      <ul
                        className="crm-settings__row-list crm-settings__row-list--dense"
                        aria-label={t('notifications.aria')}
                      >
                        {notifications.map((channel: SettingsNotification) => {
                          const statusLabel = channel.enabled
                            ? t('notifications.status.on')
                            : t('notifications.status.off');
                          return (
                            <li
                              key={channel.id}
                              className="crm-settings__row crm-settings__row--notify"
                            >
                              <span className="crm-settings__row-icon" aria-hidden="true">
                                <IhIcon name={channel.icon} size={13} />
                              </span>
                              <span className="crm-settings__row-copy">
                                <strong>{t(`notifications.channels.${channel.id}`)}</strong>
                                <StatusChip
                                  tone={channel.enabled ? 'success' : 'danger'}
                                  className="crm-settings__status-chip"
                                >
                                  {statusLabel}
                                </StatusChip>
                              </span>
                              <Button
                                variant="secondary"
                                size="sm"
                                className="crm-settings__row-action"
                                onClick={() =>
                                  openEditor({
                                    kind: 'notifications',
                                    title: t(`notifications.channels.${channel.id}`),
                                    entityId: channel.id,
                                  })
                                }
                              >
                                {t('actions.manage')}
                              </Button>
                            </li>
                          );
                        })}
                      </ul>
                    </CardContent>
                  </Card>
                </div>
              </div>

              <div className="crm-settings__config-col crm-settings__config-col--right">
                <div data-section="ai" className={sectionClass('ai')}>
                  <Card className="crm-settings__card">
                    <CardHeader
                      title={t('ai.title')}
                      action={
                        <Button
                          variant="secondary"
                          size="sm"
                          className="crm-settings__card-action"
                          onClick={() => openEditor({ kind: 'ai', title: t('ai.title') })}
                        >
                          {t('actions.edit')}
                        </Button>
                      }
                    />
                    <CardContent>
                      <dl className="crm-settings__def-grid" aria-label={t('ai.title')}>
                        <DefRow label={t('ai.provider')}>
                          <strong>{t(`ai.providerOptions.${draft.ai.provider}`)}</strong>
                        </DefRow>
                        <DefRow label={t('ai.model')}>
                          <strong>{t(`ai.modelOptions.${draft.ai.model}`)}</strong>
                        </DefRow>
                        <DefRow label={t('ai.temperature')}>
                          <strong>{draft.ai.temperature}</strong>
                        </DefRow>
                        <DefRow label={t('ai.defaultLanguage')}>
                          <strong>
                            {t(`general.languageOptions.${draft.ai.defaultLanguage}`)}
                          </strong>
                        </DefRow>
                        <DefRow label={t('ai.promptPolicy')}>
                          <strong>
                            {t(`ai.promptPolicyValues.${draft.ai.promptPolicyKey}`)}
                          </strong>
                        </DefRow>
                        <DefRow label={t('ai.totalUsage')}>
                          <strong>{t(`ai.totalUsageValues.${draft.ai.totalUsageKey}`)}</strong>
                        </DefRow>
                      </dl>
                      <div className="crm-settings__card-meter">
                        <div
                          className="crm-settings__meter-track"
                          role="progressbar"
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-valuenow={Math.round(preview.aiRequests.pct)}
                          aria-label={t('rail.aiUsage.requestsProgressAria', {
                            pct: Math.round(preview.aiRequests.pct),
                          })}
                        >
                          <span
                            style={{
                              width: `${Math.max(0, Math.min(100, preview.aiRequests.pct))}%`,
                            }}
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <div data-section="integrations" className={sectionClass('integrations')}>
                  <Card className="crm-settings__card">
                    <CardHeader title={t('integrations.title')} />
                    <CardContent>
                      <ul
                        className="crm-settings__row-list crm-settings__row-list--integrations"
                        aria-label={t('integrations.aria')}
                      >
                        {integrations.map((integration: SettingsIntegration) => (
                          <li
                            key={integration.id}
                            className="crm-settings__row crm-settings__row--integration"
                          >
                            <span
                              className={`crm-settings__integration-mark is-${integration.tone}`}
                              aria-hidden="true"
                            >
                              {integration.mark}
                            </span>
                            <span className="crm-settings__row-copy crm-settings__row-copy--stack">
                              <strong>{t(`integrations.items.${integration.id}`)}</strong>
                              <span className="crm-settings__row-meta">
                                <StatusChip
                                  tone={integration.connected ? 'success' : 'danger'}
                                  className="crm-settings__status-chip"
                                >
                                  {integration.connected
                                    ? t('integrations.status.connected')
                                    : t('integrations.status.notConfigured')}
                                </StatusChip>
                                <em className="crm-settings__sync-text">
                                  {t(`integrations.lastSyncValues.${integration.lastSyncKey}`)}
                                </em>
                              </span>
                            </span>
                            <Button
                              variant="secondary"
                              size="sm"
                              className="crm-settings__row-action"
                              onClick={() =>
                                openEditor({
                                  kind: 'integrations',
                                  title: t(`integrations.items.${integration.id}`),
                                  entityId: integration.id,
                                })
                              }
                            >
                              {integration.connected
                                ? t('actions.manage')
                                : t('integrations.connect')}
                            </Button>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </div>

                <div data-section="security" className={sectionClass('security')}>
                  <Card className="crm-settings__card">
                    <CardHeader
                      title={t('security.title')}
                      action={
                        <Button
                          variant="secondary"
                          size="sm"
                          className="crm-settings__card-action"
                          onClick={() =>
                            openEditor({ kind: 'security', title: t('security.manage') })
                          }
                        >
                          {t('security.manage')}
                        </Button>
                      }
                    />
                    <CardContent>
                      <dl className="crm-settings__security-list" aria-label={t('security.aria')}>
                        {preview.security.map((item) => {
                          const value = t(`security.values.${item.id}.${item.valueKey}`);
                          const isMfa = item.id === 'mfa';
                          return (
                            <div key={item.id} className="crm-settings__security-row">
                              <dt>
                                <span
                                  className={`crm-settings__row-icon is-${item.tone}`}
                                  aria-hidden="true"
                                >
                                  <IhIcon name={item.icon} size={13} />
                                </span>
                                <span>{t(`security.items.${item.id}`)}</span>
                              </dt>
                              <dd>
                                {isMfa ? (
                                  <StatusChip tone="success" className="crm-settings__status-chip">
                                    {value}
                                  </StatusChip>
                                ) : (
                                  <strong>{value}</strong>
                                )}
                              </dd>
                            </div>
                          );
                        })}
                      </dl>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </div>
          )}
        </div>

        <aside className="crm-settings__rail" aria-label={t('rail.aria')}>
          <RightRailCard title={t('rail.health.title')} className="crm-settings__rail-card">
            <ul className="crm-settings__health-list">
              {preview.health.map((service) => (
                <li key={service.id}>
                  <span className="crm-settings__health-check" aria-hidden="true">
                    <IhIcon name="check" size={10} />
                  </span>
                  <strong>{t(`rail.health.services.${service.id}`)}</strong>
                  <em>{t('rail.health.healthy')}</em>
                </li>
              ))}
            </ul>
            <RailFooter
              label={t('rail.viewDetails')}
              onClick={() => openEditor({ kind: 'rail', title: t('rail.health.title') })}
            />
          </RightRailCard>

          <RightRailCard title={t('rail.license.title')} className="crm-settings__rail-card">
            <div className="crm-settings__license">
              <div className="crm-settings__license-plan">
                <strong>{t(`rail.license.plans.${preview.license.planKey}`)}</strong>
                <StatusChip tone="success" className="crm-settings__status-chip">
                  {t('rail.license.active')}
                </StatusChip>
              </div>
              <dl className="crm-settings__kv">
                <div>
                  <dt>{t('rail.license.expires')}</dt>
                  <dd>{t('rail.license.expiresValue')}</dd>
                </div>
                <div>
                  <dt>{t('rail.license.userLimit')}</dt>
                  <dd>
                    {preview.license.userLimit}/{preview.license.userLimitMax}
                  </dd>
                </div>
                <div>
                  <dt>{t('rail.license.activeUsers')}</dt>
                  <dd>{preview.license.activeUsers}</dd>
                </div>
              </dl>
            </div>
            <RailFooter
              label={t('rail.viewDetails')}
              onClick={() => openEditor({ kind: 'rail', title: t('rail.license.title') })}
            />
          </RightRailCard>

          <RightRailCard title={t('rail.aiUsage.title')} className="crm-settings__rail-card">
            <UsageMeter
              label={t('rail.aiUsage.requests')}
              used={t('rail.aiUsage.requestsUsed')}
              limit={t('rail.aiUsage.requestsLimit')}
              pct={preview.aiRequests.pct}
              progressLabel={t('rail.aiUsage.requestsProgressAria', {
                pct: Math.round(preview.aiRequests.pct),
              })}
            />
            <UsageMeter
              label={t('rail.aiUsage.tokens')}
              used={t('rail.aiUsage.tokensUsed')}
              limit={t('rail.aiUsage.tokensLimit')}
              pct={preview.aiTokens.pct}
              progressLabel={t('rail.aiUsage.tokensProgressAria', {
                pct: Math.round(preview.aiTokens.pct),
              })}
            />
            <RailFooter
              label={t('rail.viewDetails')}
              onClick={() => openEditor({ kind: 'rail', title: t('rail.aiUsage.title') })}
            />
          </RightRailCard>

          <RightRailCard title={t('rail.storage.title')} className="crm-settings__rail-card">
            <UsageMeter
              label={t('rail.storage.total')}
              used={t('rail.storage.used')}
              limit={t('rail.storage.limit')}
              pct={preview.storage.pct}
              progressLabel={t('rail.storage.progressAria', {
                pct: Math.round(preview.storage.pct),
              })}
            />
            <RailFooter
              label={t('rail.viewDetails')}
              onClick={() => openEditor({ kind: 'rail', title: t('rail.storage.title') })}
            />
          </RightRailCard>
        </aside>
      </div>

      <Dialog
        open={Boolean(editor)}
        onClose={closeEditor}
        title={editor?.title ?? t('actions.edit')}
        footer={
          <>
            <Button type="button" variant="secondary" onClick={closeEditor}>
              {t('actions.cancel')}
            </Button>
            <Button type="button" onClick={saveEditor}>
              {t('actions.save')}
            </Button>
          </>
        }
      >
        <div className="crm-settings__editor">
          {(editor?.kind === 'general' || editor?.kind === 'overview') && (
            <>
              <label className="crm-settings__editor-field">
                <span>{t('general.companyName')}</span>
                <Input
                  value={generalForm.companyName}
                  onChange={(e) =>
                    setGeneralForm((prev) => ({ ...prev, companyName: e.target.value }))
                  }
                />
              </label>
              <label className="crm-settings__editor-field">
                <span>{t('general.language')}</span>
                <Select
                  value={generalForm.language}
                  onChange={(e) =>
                    setGeneralForm((prev) => ({ ...prev, language: e.target.value }))
                  }
                >
                  <option value="tr">{t('general.languageOptions.tr')}</option>
                  <option value="en">{t('general.languageOptions.en')}</option>
                </Select>
              </label>
              <label className="crm-settings__editor-field">
                <span>{t('general.timezone')}</span>
                <Select
                  value={generalForm.timezone}
                  onChange={(e) =>
                    setGeneralForm((prev) => ({ ...prev, timezone: e.target.value }))
                  }
                >
                  <option value="europeIstanbul">
                    {t('general.timezoneOptions.europeIstanbul')}
                  </option>
                  <option value="europeLondon">{t('general.timezoneOptions.europeLondon')}</option>
                  <option value="americaNewYork">
                    {t('general.timezoneOptions.americaNewYork')}
                  </option>
                </Select>
              </label>
            </>
          )}

          {editor?.kind === 'ai' && (
            <>
              <label className="crm-settings__editor-field">
                <span>{t('ai.provider')}</span>
                <Select
                  value={aiForm.provider}
                  onChange={(e) => setAiForm((prev) => ({ ...prev, provider: e.target.value }))}
                >
                  <option value="openai">{t('ai.providerOptions.openai')}</option>
                  <option value="azure">{t('ai.providerOptions.azure')}</option>
                  <option value="anthropic">{t('ai.providerOptions.anthropic')}</option>
                </Select>
              </label>
              <label className="crm-settings__editor-field">
                <span>{t('ai.model')}</span>
                <Select
                  value={aiForm.model}
                  onChange={(e) => setAiForm((prev) => ({ ...prev, model: e.target.value }))}
                >
                  <option value="gpt4o">{t('ai.modelOptions.gpt4o')}</option>
                  <option value="gpt4oMini">{t('ai.modelOptions.gpt4oMini')}</option>
                  <option value="gpt41">{t('ai.modelOptions.gpt41')}</option>
                </Select>
              </label>
              <label className="crm-settings__editor-field">
                <span>{t('ai.temperature')}</span>
                <Input
                  value={aiForm.temperature}
                  onChange={(e) => setAiForm((prev) => ({ ...prev, temperature: e.target.value }))}
                />
              </label>
            </>
          )}

          {editor?.kind === 'crm' && (
            <p className="crm-settings__editor-copy">
              {t('crmSettings.manageHint', {
                name: editor.title,
                count: crmCounts[editor.entityId ?? ''] ?? 0,
              })}
            </p>
          )}

          {editor?.kind === 'notifications' && activeNotification && (
            <p className="crm-settings__editor-copy">
              {t('notifications.manageHint', {
                channel: editor.title,
                state: activeNotification.enabled
                  ? t('notifications.status.on')
                  : t('notifications.status.off'),
              })}
            </p>
          )}

          {editor?.kind === 'integrations' && activeIntegration && (
            <p className="crm-settings__editor-copy">
              {t('integrations.manageHint', {
                name: editor.title,
                state: activeIntegration.connected
                  ? t('integrations.status.connected')
                  : t('integrations.status.notConfigured'),
              })}
            </p>
          )}

          {editor?.kind === 'security' && (
            <label className="crm-settings__editor-field">
              <span>{t('security.noteLabel')}</span>
              <Input value={securityNote} onChange={(e) => setSecurityNote(e.target.value)} />
            </label>
          )}

          {editor?.kind === 'rail' && (
            <label className="crm-settings__editor-field">
              <span>{t('rail.noteLabel')}</span>
              <Input value={railNote} onChange={(e) => setRailNote(e.target.value)} />
            </label>
          )}
        </div>
      </Dialog>

      <Dialog
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        title={t('overview.changeHistory')}
        footer={
          <Button type="button" variant="secondary" onClick={() => setHistoryOpen(false)}>
            {t('actions.cancel')}
          </Button>
        }
      >
        <ul className="crm-settings__history-list">
          <li>{t('overview.history.item1')}</li>
          <li>{t('overview.history.item2')}</li>
          <li>{t('overview.history.item3')}</li>
        </ul>
      </Dialog>
    </div>
  );
}
