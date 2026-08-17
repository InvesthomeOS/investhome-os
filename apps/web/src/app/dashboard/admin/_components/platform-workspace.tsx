'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useLocale, useTranslations } from 'next-intl';
import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';

import { PageHeader } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import { platformApi, type PlatformFeatureFlag, type PlatformModule, type PlatformOverview } from '@/lib/api/platform';
import { useAuth } from '@/lib/auth/auth-context';

import { KpiGrid, SecSection, StatusBadge } from './sec-ui';
import { useAdminToast } from './use-admin-toast';

export type PlatformSection =
  | 'overview'
  | 'modules'
  | 'feature-flags'
  | 'entitlements'
  | 'external-users'
  | 'api-clients'
  | 'api-scopes'
  | 'webhooks'
  | 'integrations'
  | 'health'
  | 'audit';

const NAV: Array<{ section: PlatformSection; href: Route; labelKey: string }> = [
  { section: 'overview', href: '/dashboard/admin/platform' as Route, labelKey: 'overview' },
  { section: 'modules', href: '/dashboard/admin/platform/modules' as Route, labelKey: 'modules' },
  { section: 'feature-flags', href: '/dashboard/admin/platform/feature-flags' as Route, labelKey: 'featureFlags' },
  { section: 'entitlements', href: '/dashboard/admin/platform/entitlements' as Route, labelKey: 'entitlements' },
  { section: 'external-users', href: '/dashboard/admin/platform/external-users' as Route, labelKey: 'externalUsers' },
  { section: 'api-clients', href: '/dashboard/admin/platform/api-clients' as Route, labelKey: 'apiClients' },
  { section: 'api-scopes', href: '/dashboard/admin/platform/api-scopes' as Route, labelKey: 'apiScopes' },
  { section: 'webhooks', href: '/dashboard/admin/platform/webhooks' as Route, labelKey: 'webhooks' },
  { section: 'integrations', href: '/dashboard/admin/platform/integrations' as Route, labelKey: 'integrations' },
  { section: 'health', href: '/dashboard/admin/platform/health' as Route, labelKey: 'health' },
  { section: 'audit', href: '/dashboard/admin/platform/audit' as Route, labelKey: 'audit' },
];

function nameOf(item: { name_en?: string; name_tr?: string }, locale: string) {
  return locale === 'tr' ? item.name_tr || item.name_en : item.name_en || item.name_tr;
}

function isConnectableIntegration(item: Record<string, unknown>) {
  return item.connectable === true || String(item.code) === 'canva';
}

export function PlatformWorkspace({ section }: { section: PlatformSection }) {
  const t = useTranslations('platformAdmin');
  const locale = useLocale();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();
  const { notifySuccess, notifyError } = useAdminToast();
  const canView = hasPermission(user, 'platform', 'view') || hasPermission(user, 'security', 'view');
  const canManage = hasPermission(user, 'platform', 'manage') || hasPermission(user, 'security', 'manage');

  const [denied, setDenied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [modules, setModules] = useState<PlatformModule[]>([]);
  const [deps, setDeps] = useState<{ has_cycle: boolean; cycle: string[]; visualization: Array<{ id: string; depends_on: string[]; health: string }> } | null>(null);
  const [depsError, setDepsError] = useState<string | null>(null);
  const [flags, setFlags] = useState<PlatformFeatureFlag[]>([]);
  const [killBanner, setKillBanner] = useState<string | null>(null);
  const [entitlements, setEntitlements] = useState<Array<Record<string, unknown>>>([]);
  const [entResult, setEntResult] = useState<string | null>(null);
  const [externalUsers, setExternalUsers] = useState<Array<Record<string, unknown>>>([]);
  const [apiClients, setApiClients] = useState<Array<Record<string, unknown>>>([]);
  const [apiScopes, setApiScopes] = useState<Array<Record<string, unknown>>>([]);
  const [scopeNote, setScopeNote] = useState('');
  const [scopeResult, setScopeResult] = useState<string | null>(null);
  const [webhooks, setWebhooks] = useState<Array<Record<string, unknown>>>([]);
  const [deliveries, setDeliveries] = useState<Array<Record<string, unknown>>>([]);
  const [sigResult, setSigResult] = useState<string | null>(null);
  const [integrations, setIntegrations] = useState<Array<Record<string, unknown>>>([]);
  const [canvaBusy, setCanvaBusy] = useState(false);
  const [health, setHealth] = useState<PlatformOverview['health'] | null>(null);
  const [moduleHealth, setModuleHealth] = useState<Array<Record<string, unknown>>>([]);
  const [killSwitches, setKillSwitches] = useState<{ modules: PlatformModule[]; flags: PlatformFeatureFlag[] } | null>(null);
  const [envControls, setEnvControls] = useState<Record<string, unknown> | null>(null);
  const [audit, setAudit] = useState<Array<Record<string, unknown>>>([]);
  const [archAudit, setArchAudit] = useState<Array<{ capability: string; status: string; reuse: string; notes: string }>>([]);
  const [selectedModule, setSelectedModule] = useState<PlatformModule | null>(null);
  const [selectedFlag, setSelectedFlag] = useState<PlatformFeatureFlag | null>(null);
  const [selectedEntitlement, setSelectedEntitlement] = useState<Record<string, unknown> | null>(null);
  const [selectedExternal, setSelectedExternal] = useState<Record<string, unknown> | null>(null);
  const [selectedClient, setSelectedClient] = useState<Record<string, unknown> | null>(null);
  const [selectedDelivery, setSelectedDelivery] = useState<Record<string, unknown> | null>(null);
  const [selectedIntegration, setSelectedIntegration] = useState<Record<string, unknown> | null>(null);
  const [failedWebhookDemo, setFailedWebhookDemo] = useState(false);

  const load = useCallback(async () => {
    if (authLoading) return;
    if (!user || !canView) {
      setDenied(true);
      setLoading(false);
      return;
    }
    setDenied(false);
    setLoading(true);
    try {
      if (section === 'overview') {
        const o = await platformApi.overview();
        setOverview(o);
        setArchAudit(o.architecture_audit || []);
      } else if (section === 'modules') {
        const [m, d] = await Promise.all([platformApi.modules(), platformApi.dependencies()]);
        setModules(m.items);
        setDeps(d);
      } else if (section === 'feature-flags') {
        setFlags((await platformApi.featureFlags()).items);
      } else if (section === 'entitlements') {
        setEntitlements((await platformApi.entitlements()).items);
      } else if (section === 'external-users') {
        setExternalUsers((await platformApi.externalUsers()).items);
      } else if (section === 'api-clients') {
        setApiClients((await platformApi.apiClients()).items);
      } else if (section === 'api-scopes') {
        const s = await platformApi.apiScopes();
        setApiScopes(s.items);
        setScopeNote(s.note);
      } else if (section === 'webhooks') {
        const [w, d] = await Promise.all([platformApi.webhooks(), platformApi.deliveries()]);
        setWebhooks(w.items);
        setDeliveries(d.items);
      } else if (section === 'integrations') {
        setIntegrations((await platformApi.integrations()).items);
      } else if (section === 'health') {
        const [h, mh, ks, env] = await Promise.all([
          platformApi.health(),
          platformApi.moduleHealth(),
          platformApi.killSwitches(),
          platformApi.environment(),
        ]);
        setHealth(h);
        setModuleHealth(mh.items);
        setKillSwitches(ks);
        setEnvControls(env);
      } else if (section === 'audit') {
        setAudit((await platformApi.externalAudit()).items);
      }
    } catch (err) {
      setDenied(true);
      notifyError(err, t('loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [authLoading, user, canView, section, notifyError, t]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (section !== 'integrations') return;
    const connected = searchParams.get('canva');
    const canvaError = searchParams.get('canva_error');
    if (connected === 'connected') {
      notifySuccess(t('canva.connectedToast'));
    } else if (canvaError) {
      notifyError(null, t('canva.errorToast', { code: canvaError }));
    }
    if (connected || canvaError) {
      const url = new URL(window.location.href);
      url.searchParams.delete('canva');
      url.searchParams.delete('canva_error');
      window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`);
    }
  }, [section, searchParams, notifySuccess, notifyError, t]);

  const integrationStatusLabel = (status: string) => {
    if (status === 'connected') return t('canva.statusConnected');
    if (status === 'not_connected') return t('canva.statusNotConnected');
    return status.replace(/_/g, ' ');
  };

  const connectCanva = async () => {
    if (!canManage || canvaBusy) return;
    setCanvaBusy(true);
    try {
      const { authorize_url } = await platformApi.canvaAuthorize();
      window.location.href = authorize_url;
    } catch (err) {
      setCanvaBusy(false);
      notifyError(err, t('canva.connectFailed'));
    }
  };

  const disconnectCanva = async () => {
    if (!canManage || canvaBusy) return;
    setCanvaBusy(true);
    try {
      await platformApi.canvaDisconnect();
      notifySuccess(t('canva.disconnectedToast'));
      await load();
      setSelectedIntegration((prev) =>
        prev && String(prev.code) === 'canva'
          ? { ...prev, status: 'not_connected', configured: false }
          : prev,
      );
    } catch (err) {
      notifyError(err, t('canva.disconnectFailed'));
    } finally {
      setCanvaBusy(false);
    }
  };

  const renderConnectActions = (item: Record<string, unknown>, stopRowClick = false) => {
    if (!isConnectableIntegration(item) || !canManage) return null;
    const connected = String(item.status) === 'connected';
    return (
      <div className="platform-actions" data-canva-actions>
        {connected ? (
          <button
            type="button"
            className="admin-btn admin-btn--danger"
            data-canva-disconnect
            disabled={canvaBusy}
            onClick={(ev) => {
              if (stopRowClick) ev.stopPropagation();
              void disconnectCanva();
            }}
          >
            {t('canva.disconnect')}
          </button>
        ) : (
          <button
            type="button"
            className="admin-btn"
            data-canva-connect
            disabled={canvaBusy}
            onClick={(ev) => {
              if (stopRowClick) ev.stopPropagation();
              void connectCanva();
            }}
          >
            {t('canva.connect')}
          </button>
        )}
      </div>
    );
  };

  const titles: Record<PlatformSection, string> = {
    overview: t('titles.overview'),
    modules: t('titles.modules'),
    'feature-flags': t('titles.featureFlags'),
    entitlements: t('titles.entitlements'),
    'external-users': t('titles.externalUsers'),
    'api-clients': t('titles.apiClients'),
    'api-scopes': t('titles.apiScopes'),
    webhooks: t('titles.webhooks'),
    integrations: t('titles.integrations'),
    health: t('titles.health'),
    audit: t('titles.audit'),
  };

  if (authLoading || loading) {
    return (
      <main className="dashboard platform-workspace" data-platform-workspace={section}>
        <PageHeader eyebrow={t('eyebrow')} title={titles[section]} subtitle={t('loading')} />
      </main>
    );
  }

  if (denied) {
    return (
      <main className="dashboard platform-workspace platform-workspace--denied" data-platform-workspace={section} data-platform-denied>
        <PageHeader eyebrow={t('eyebrow')} title={t('permissionDenied')} subtitle={t('permissionDeniedHint')} />
        <p className="platform-denied-banner" role="alert">{t('permissionDenied')}</p>
      </main>
    );
  }

  return (
    <main className="dashboard platform-workspace" data-platform-workspace={section}>
      <PageHeader eyebrow={t('eyebrow')} title={titles[section]} subtitle={t('subtitle')} />
      <nav className="platform-subnav" aria-label={t('subnavLabel')}>
        {NAV.map((item) => (
          <Link
            key={item.section}
            href={item.href}
            className={`platform-subnav__link${section === item.section ? ' is-active' : ''}`}
            aria-current={section === item.section ? 'page' : undefined}
          >
            {t(`nav.${item.labelKey}`)}
          </Link>
        ))}
      </nav>

      {killBanner ? (
        <div className="platform-kill-banner" data-platform-kill-switch role="status">
          {t('killSwitchActive', { key: killBanner })}
        </div>
      ) : null}

      {section === 'overview' && overview ? (
        <>
          <KpiGrid items={overview.health.kpis} />
          <SecSection title={t('sections.health')} description={t('sections.healthHint')}>
            <div className="platform-meta-row">
              <StatusBadge status={overview.health.status} />
              <span>{t('environment')}: {overview.health.environment}</span>
              <StatusBadge status={overview.health.mga_status} />
              <span data-billing-note>{t('billingOutOfScope')}</span>
            </div>
          </SecSection>
          <SecSection title={t('sections.recommendedPilot')} description={locale === 'tr' ? overview.recommended_next_pilot.reason_tr : overview.recommended_next_pilot.reason_en}>
            <p data-recommended-pilot>
              <strong>{overview.recommended_next_pilot.code}</strong> ({overview.recommended_next_pilot.phase}) —{' '}
              {overview.recommended_next_pilot.implemented_in_g15a ? t('pilotBuilt') : t('pilotNotBuilt')}
            </p>
          </SecSection>
          <SecSection title={t('sections.architectureAudit')} description={t('sections.architectureAuditHint')}>
            <div className="sec-table-wrap">
              <table className="sec-table" data-architecture-audit>
                <thead>
                  <tr>
                    <th>{t('cols.capability')}</th>
                    <th>{t('cols.status')}</th>
                    <th>{t('cols.notes')}</th>
                  </tr>
                </thead>
                <tbody>
                  {archAudit.map((row) => (
                    <tr key={row.capability} data-audit-status={row.status}>
                      <td>{row.capability}</td>
                      <td><StatusBadge status={row.status.toLowerCase().replace(/ /g, '_')} /></td>
                      <td>{row.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SecSection>
          <SecSection title={t('sections.roadmap')}>
            <ul className="platform-roadmap" data-platform-roadmap>
              {Object.entries(overview.roadmap).map(([k, v]) => (
                <li key={k}><code>{k}</code> — <StatusBadge status={v} /></li>
              ))}
            </ul>
          </SecSection>
        </>
      ) : null}

      {section === 'modules' ? (
        <>
          <SecSection title={t('sections.moduleRegistry')} description={t('sections.moduleRegistryHint')}>
            <div className="sec-table-wrap">
              <table className="sec-table" data-platform-modules>
                <thead>
                  <tr>
                    <th>{t('cols.module')}</th>
                    <th>{t('cols.lifecycle')}</th>
                    <th>{t('cols.effective')}</th>
                    <th>{t('cols.dependsOn')}</th>
                    <th>{t('cols.key')}</th>
                    <th>{t('cols.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {modules.map((m) => (
                    <tr
                      key={m.code}
                      data-module-code={m.code}
                      data-lifecycle={m.lifecycle_status}
                      onClick={() => setSelectedModule(m)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td>
                        <strong>{nameOf(m, locale)}</strong>
                        <div className="platform-muted">{locale === 'tr' ? m.description_tr : m.description_en}</div>
                        {m.block_reason ? <div className="platform-block-reason" data-block-reason>{m.block_reason}</div> : null}
                      </td>
                      <td><StatusBadge status={m.lifecycle_status} /></td>
                      <td><StatusBadge status={m.effective_enabled ? 'enabled' : 'disabled'} /></td>
                      <td><code>{m.depends_on.join(', ') || '—'}</code></td>
                      <td>{m.key_immutable ? <StatusBadge status="immutable" /> : <StatusBadge status="editable" />}</td>
                      <td>
                        {canManage && m.lifecycle_status !== 'blocked' ? (
                          <div className="platform-actions">
                            <button type="button" className="admin-btn" onClick={() => void platformApi.updateModule(m.code, { enabled: !m.enabled }).then(() => { notifySuccess(t('saved')); return load(); }).catch((e) => notifyError(e, t('saveFailed')))}>
                              {m.enabled ? t('disable') : t('enable')}
                            </button>
                            <button type="button" className="admin-btn admin-btn--danger" data-kill-switch-btn={m.code} onClick={() => void platformApi.updateModule(m.code, { kill_switch: !m.kill_switch }).then(() => { setKillBanner(m.code); notifySuccess(t('saved')); return load(); }).catch((e) => notifyError(e, t('saveFailed')))}>
                              {t('killSwitch')}
                            </button>
                          </div>
                        ) : (
                          <span className="platform-muted">{t('noActions')}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {selectedModule ? (
              <aside className="platform-detail" data-module-detail data-disabled-module-state={!selectedModule.effective_enabled ? true : undefined}>
                <h3>{nameOf(selectedModule, locale)}</h3>
                <p><code>{selectedModule.code}</code></p>
                <p>{locale === 'tr' ? selectedModule.description_tr : selectedModule.description_en}</p>
                <div className="platform-meta-row">
                  <StatusBadge status={selectedModule.lifecycle_status} />
                  <StatusBadge status={selectedModule.effective_enabled ? 'enabled' : 'disabled'} />
                  {selectedModule.kill_switch ? <StatusBadge status="kill_switch" /> : null}
                </div>
                {!selectedModule.effective_enabled ? (
                  <p className="platform-block-reason" data-disabled-module-state>
                    Module effectively disabled (lifecycle={selectedModule.lifecycle_status}, env={String(selectedModule.env_enabled)}, kill={String(selectedModule.kill_switch)})
                  </p>
                ) : null}
                {selectedModule.block_reason ? <p className="platform-block-reason">{selectedModule.block_reason}</p> : null}
                <p className="platform-muted">depends_on: {selectedModule.depends_on.join(', ') || '—'}</p>
              </aside>
            ) : null}
          </SecSection>
          <SecSection title={t('sections.dependencies')} description={t('sections.dependenciesHint')}>
            <div data-dependency-map>
              {deps?.has_cycle ? <p className="platform-block-reason">{t('cycleDetected')}: {deps.cycle.join(' → ')}</p> : <p className="platform-muted">{t('noCycle')}</p>}
              <ul className="platform-list">
                {(deps?.visualization || []).map((n) => (
                  <li key={n.id}><code>{n.id}</code> → {(n.depends_on || []).join(', ') || '—'} <StatusBadge status={n.health} /></li>
                ))}
              </ul>
            </div>
            {canManage ? (
              <div className="platform-actions">
                <button
                  type="button"
                  className="admin-btn admin-btn--danger"
                  data-circular-deps-test
                  onClick={() =>
                    void platformApi.depsPreview('core_os', ['platform_admin']).then((r) => {
                      // Then create cycle platform_admin -> core_os already exists, so core_os -> platform_admin cycles
                      setDepsError(r.ok ? t('unexpectedOk') : (r.error || t('cycleRejected')));
                    })
                  }
                >
                  {t('testCircularReject')}
                </button>
                {depsError ? <p className="platform-check-result" data-circular-result role="status">{depsError}</p> : null}
              </div>
            ) : null}
          </SecSection>
        </>
      ) : null}

      {section === 'feature-flags' ? (
        <SecSection title={t('sections.featureFlags')} description={t('sections.featureFlagsHint')}>
          <div className="sec-table-wrap">
            <table className="sec-table" data-platform-flags>
              <thead>
                <tr>
                  <th>{t('cols.flag')}</th>
                  <th>{t('cols.source')}</th>
                  <th>{t('cols.effective')}</th>
                  <th>{t('cols.targeting')}</th>
                  <th>{t('cols.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {flags.map((f) => (
                  <tr
                    key={f.key}
                    data-flag-key={f.key}
                    data-effective={String(f.effective_enabled)}
                    onClick={() => setSelectedFlag(f)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td><code>{f.key}</code>{f.kill_switch ? <StatusBadge status="kill_switch" /> : null}</td>
                    <td>{f.source} · {f.rollout_percent}%</td>
                    <td><StatusBadge status={f.effective_enabled ? 'enabled' : 'disabled'} /></td>
                    <td className="platform-muted">roles: {(f.target_roles || []).join(', ') || '—'} · env: {f.environment_scope || 'all'}</td>
                    <td>
                      {canManage ? (
                        <div className="platform-actions">
                          <button type="button" className="admin-btn" data-flag-toggle={f.key} onClick={() => void platformApi.updateFeatureFlag(f.key, { enabled: !f.enabled, kill_switch: false }).then(() => { notifySuccess(t('saved')); return load(); })}>{f.enabled ? t('disable') : t('enable')}</button>
                          <button type="button" className="admin-btn admin-btn--danger" data-flag-kill={f.key} onClick={() => void platformApi.updateFeatureFlag(f.key, { enabled: false, kill_switch: true }).then(() => { setKillBanner(f.key); notifySuccess(t('saved')); return load(); })}>{t('killSwitch')}</button>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
              </table>
            </div>
            {selectedFlag ? (
              <aside className="platform-detail" data-flag-detail>
                <h3><code>{selectedFlag.key}</code></h3>
                <div className="platform-meta-row">
                  <StatusBadge status={selectedFlag.effective_enabled ? 'enabled' : 'disabled'} />
                  <span>source={selectedFlag.source}</span>
                  <span>rollout={selectedFlag.rollout_percent}%</span>
                  <span>env={selectedFlag.environment_scope}</span>
                </div>
                <p className="platform-muted">roles: {(selectedFlag.target_roles || []).join(', ') || '—'}</p>
                <p className="platform-muted">companies: {(selectedFlag.target_companies || []).join(', ') || '—'}</p>
                <p className="platform-muted">users: {(selectedFlag.target_users || []).join(', ') || '—'}</p>
                {selectedFlag.notes ? <p>{selectedFlag.notes}</p> : null}
              </aside>
            ) : null}
          </SecSection>
      ) : null}

      {section === 'entitlements' ? (
        <SecSection title={t('sections.entitlements')} description={t('sections.entitlementsHint')}>
          <p className="platform-banner" data-billing-note>{t('billingOutOfScope')}</p>
          <div className="sec-table-wrap">
            <table className="sec-table" data-platform-entitlements>
              <thead>
                <tr><th>{t('cols.code')}</th><th>{t('cols.capability')}</th><th>{t('cols.effect')}</th><th>{t('cols.module')}</th></tr>
              </thead>
              <tbody>
                {entitlements.map((e) => (
                  <tr key={String(e.code)} onClick={() => setSelectedEntitlement(e)} style={{ cursor: 'pointer' }}>
                    <td><code>{String(e.code)}</code></td>
                    <td><code>{String(e.capability)}</code></td>
                    <td><StatusBadge status={String(e.effect)} /></td>
                    <td>{String(e.module_code ?? '—')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selectedEntitlement ? (
            <aside className="platform-detail" data-entitlement-detail>
              <h3><code>{String(selectedEntitlement.code)}</code></h3>
              <p>capability: <code>{String(selectedEntitlement.capability)}</code></p>
              <StatusBadge status={String(selectedEntitlement.effect)} />
              <p className="platform-muted">module: {String(selectedEntitlement.module_code ?? '—')}</p>
              <p className="platform-muted">notes: {String(selectedEntitlement.notes ?? '—')}</p>
            </aside>
          ) : null}
          <button type="button" className="admin-btn" data-entitlement-check onClick={() => void platformApi.checkEntitlement({ capability: 'project_budgets.view', external_type: 'contractor' }).then((r) => setEntResult(r.allowed ? t('entitlementAllowed', { reason: r.reason }) : t('entitlementDenied', { reason: r.reason })))}>
            {t('checkContractorBudgetDeny')}
          </button>
          {entResult ? <p className="platform-check-result" data-entitlement-result role="status">{entResult}</p> : null}
        </SecSection>
      ) : null}

      {section === 'external-users' ? (
        <SecSection title={t('sections.externalTypes')} description={t('sections.externalTypesHint')}>
          <div className="sec-table-wrap">
            <table className="sec-table" data-platform-external-users>
              <thead>
                <tr><th>{t('cols.type')}</th><th>{t('cols.scopes')}</th><th>{t('cols.budgets')}</th></tr>
              </thead>
              <tbody>
                {externalUsers.map((u) => (
                  <tr
                    key={String(u.code)}
                    data-external-type={String(u.code)}
                    onClick={() => setSelectedExternal(u)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <strong>{nameOf({ name_en: String(u.name_en), name_tr: String(u.name_tr) }, locale)}</strong>
                      <div className="platform-muted"><code>{String(u.code)}</code></div>
                    </td>
                    <td><code>{((u.default_scopes as string[]) || []).join(', ') || '—'}</code></td>
                    <td><StatusBadge status={u.can_see_budgets ? 'allowed' : 'denied'} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selectedExternal ? (
            <aside className="platform-detail" data-external-user-detail>
              <h3>{nameOf({ name_en: String(selectedExternal.name_en), name_tr: String(selectedExternal.name_tr) }, locale)}</h3>
              <p><code>{String(selectedExternal.code)}</code></p>
              <p>{String(locale === 'tr' ? selectedExternal.description_tr : selectedExternal.description_en)}</p>
              <p className="platform-muted">scopes: {((selectedExternal.default_scopes as string[]) || []).join(', ') || '—'}</p>
              <StatusBadge status={selectedExternal.can_see_budgets ? 'allowed' : 'denied'} />
              <pre className="platform-muted">{JSON.stringify(selectedExternal.isolation_rules || {}, null, 2)}</pre>
            </aside>
          ) : null}
        </SecSection>
      ) : null}

      {section === 'api-clients' ? (
        <SecSection title={t('sections.apiClients')} description={t('sections.apiClientsHint')}>
          {canManage ? (
            <button type="button" className="admin-btn" data-create-api-client onClick={() => void platformApi.createApiClient('G15A Demo Client', ['platform:read']).then((c) => { notifySuccess(t('apiClientCreated', { secret: String(c.secret ?? '') })); return load(); }).catch((e) => notifyError(e, t('saveFailed')))}>
              {t('createApiClient')}
            </button>
          ) : null}
          <div className="sec-table-wrap">
            <table className="sec-table" data-platform-api-clients>
              <thead>
                <tr><th>{t('cols.name')}</th><th>{t('cols.prefix')}</th><th>{t('cols.scopes')}</th><th>{t('cols.status')}</th><th>{t('cols.actions')}</th></tr>
              </thead>
              <tbody>
                {apiClients.length === 0 ? (
                  <tr><td colSpan={5}>{t('emptyApiClients')}</td></tr>
                ) : (
                  apiClients.map((c) => (
                    <tr key={String(c.id)} onClick={() => setSelectedClient(c)} style={{ cursor: 'pointer' }}>
                      <td>{String(c.name)}</td>
                      <td><code>{String(c.key_prefix)}</code></td>
                      <td><code>{((c.scopes as string[]) || []).join(', ') || '—'}</code></td>
                      <td><StatusBadge status={String(c.status)} /></td>
                      <td>
                        {canManage ? (
                          <div className="platform-actions">
                            <button type="button" className="admin-btn" data-rotate-client={String(c.id)} onClick={(ev) => { ev.stopPropagation(); void platformApi.rotateApiClient(String(c.id)).then((r) => { notifySuccess(t('rotated', { secret: String(r.secret ?? '') })); return load(); }); }}>{t('rotate')}</button>
                            <button type="button" className="admin-btn admin-btn--danger" data-revoke-client={String(c.id)} onClick={(ev) => { ev.stopPropagation(); void platformApi.revokeApiClient(String(c.id)).then(() => { notifySuccess(t('revoked')); return load(); }); }}>{t('revoke')}</button>
                          </div>
                        ) : null}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {selectedClient ? (
            <aside className="platform-detail" data-api-client-detail>
              <h3>{String(selectedClient.name)}</h3>
              <p>prefix: <code>{String(selectedClient.key_prefix)}</code></p>
              <StatusBadge status={String(selectedClient.status)} />
              <p className="platform-muted">scopes: {((selectedClient.scopes as string[]) || []).join(', ') || '—'}</p>
              <p className="platform-muted">id: {String(selectedClient.id)}</p>
            </aside>
          ) : null}
          <button type="button" className="admin-btn" data-scope-check onClick={() => void platformApi.checkApiScope('invalid-key', 'platform:write').then((r) => setScopeResult(r.allowed ? t('scopeAllowed') : t('scopeRejected', { reason: r.reason })))}>
            {t('demoScopeReject')}
          </button>
          {scopeResult ? <p className="platform-check-result" data-scope-result role="status">{scopeResult}</p> : null}
        </SecSection>
      ) : null}

      {section === 'api-scopes' ? (
        <SecSection title={t('sections.apiScopes')} description={t('sections.apiScopesHint')}>
          <p className="platform-banner" data-no-wildcards>{scopeNote || t('noWildcards')}</p>
          <div className="sec-table-wrap">
            <table className="sec-table" data-platform-api-scopes>
              <thead>
                <tr><th>{t('cols.code')}</th><th>{t('cols.name')}</th><th>{t('cols.category')}</th></tr>
              </thead>
              <tbody>
                {apiScopes.map((s) => (
                  <tr key={String(s.code)}>
                    <td><code>{String(s.code)}</code></td>
                    <td>{nameOf({ name_en: String(s.name_en), name_tr: String(s.name_tr) }, locale)}</td>
                    <td>{String(s.category)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SecSection>
      ) : null}

      {section === 'webhooks' ? (
        <>
          <SecSection title={t('sections.webhooks')} description={t('sections.webhooksHint')}>
            {canManage ? (
              <div className="platform-actions">
                <button
                  type="button"
                  className="admin-btn"
                  data-create-webhook
                  onClick={() =>
                    void (async () => {
                      const created = await platformApi.createWebhook('G15A Hook', 'https://example.com/hooks/ih', ['platform.module.updated']);
                      const secret = String(created.secret ?? '');
                      const id = String(created.id ?? '');
                      const payload = { module: 'platform_admin', at: new Date().toISOString() };
                      const enq = await platformApi.enqueueWebhook(id, 'platform.ping', payload, secret);
                      const verify = await platformApi.verifySignature(secret, payload, String(enq.signature_header ?? ''));
                      setSigResult(verify.valid ? t('signatureValid') : t('signatureInvalid'));
                      notifySuccess(t('webhookCreated'));
                      await load();
                    })().catch((e) => notifyError(e, t('saveFailed')))
                  }
                >
                  {t('createWebhookDemo')}
                </button>
                <button
                  type="button"
                  className="admin-btn admin-btn--danger"
                  data-fail-webhook-demo
                  onClick={() =>
                    void (async () => {
                      const created = await platformApi.createWebhook(
                        'G15A Fail Hook',
                        'https://example.com/hooks/fail',
                        ['platform.fail'],
                      );
                      const secret = String(created.secret ?? '');
                      const id = String(created.id ?? '');
                      const enq = await platformApi.enqueueWebhook(
                        id,
                        'platform.fail',
                        { fail: true },
                        secret,
                      );
                      const deliveryId = String(enq.id ?? '');
                      if (deliveryId) {
                        await platformApi.deadLetterDelivery(deliveryId);
                      }
                      setFailedWebhookDemo(true);
                      setSelectedDelivery({
                        id: deliveryId,
                        event_type: 'platform.fail',
                        status: 'dead',
                        signature_header: enq.signature_header,
                        error_message: 'Dead-lettered after max retries (demo)',
                      });
                      notifySuccess(t('saved'));
                      await load();
                    })().catch((e) => notifyError(e, t('saveFailed')))
                  }
                >
                  Demo failed webhook
                </button>
              </div>
            ) : null}
            {sigResult ? <p className="platform-check-result" data-signature-result role="status">{sigResult}</p> : null}
            {failedWebhookDemo ? (
              <div className="platform-kill-banner" data-failed-webhook-state role="status">
                Webhook delivery failed / dead-lettered — retries exhausted
              </div>
            ) : null}
            <div className="sec-table-wrap">
              <table className="sec-table" data-platform-webhooks>
                <thead>
                  <tr><th>{t('cols.name')}</th><th>{t('cols.url')}</th><th>{t('cols.status')}</th></tr>
                </thead>
                <tbody>
                  {webhooks.length === 0 ? <tr><td colSpan={3}>{t('emptyWebhooks')}</td></tr> : webhooks.map((w) => (
                    <tr key={String(w.id)}>
                      <td>{String(w.name)}</td>
                      <td><code>{String(w.target_url)}</code></td>
                      <td><StatusBadge status={String(w.last_status || (w.enabled ? 'enabled' : 'disabled'))} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SecSection>
          <SecSection title={t('sections.deliveries')} description={t('sections.deliveriesHint')}>
            <div className="sec-table-wrap">
              <table className="sec-table" data-platform-deliveries>
                <thead>
                  <tr><th>{t('cols.event')}</th><th>{t('cols.status')}</th><th>{t('cols.signature')}</th></tr>
                </thead>
                <tbody>
                  {deliveries.length === 0 ? <tr><td colSpan={3}>{t('emptyDeliveries')}</td></tr> : deliveries.map((d) => (
                    <tr
                      key={String(d.id)}
                      data-delivery-status={String(d.status)}
                      onClick={() => setSelectedDelivery(d)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td>{String(d.event_type)}</td>
                      <td><StatusBadge status={String(d.status)} /></td>
                      <td><code className="sec-code">{String(d.signature_header || '—').slice(0, 48)}…</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {selectedDelivery ? (
              <aside
                className="platform-detail"
                data-webhook-delivery-detail
                data-failed-webhook-state={String(selectedDelivery.status) === 'dead' || String(selectedDelivery.status) === 'failed' ? true : undefined}
              >
                <h3>{String(selectedDelivery.event_type)}</h3>
                <StatusBadge status={String(selectedDelivery.status)} />
                <p className="platform-muted">id: {String(selectedDelivery.id)}</p>
                <p className="platform-muted">signature: {String(selectedDelivery.signature_header ?? '—')}</p>
                {selectedDelivery.error_message ? (
                  <p className="platform-block-reason">{String(selectedDelivery.error_message)}</p>
                ) : null}
              </aside>
            ) : null}
          </SecSection>
        </>
      ) : null}

      {section === 'integrations' ? (
        <SecSection title={t('sections.integrations')} description={t('sections.integrationsHint')}>
          <div className="sec-table-wrap">
            <table className="sec-table" data-platform-integrations>
              <thead>
                <tr>
                  <th>{t('cols.integration')}</th>
                  <th>{t('cols.category')}</th>
                  <th>{t('cols.status')}</th>
                  <th>{t('cols.notes')}</th>
                  <th>{t('cols.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {integrations.map((i) => (
                  <tr
                    key={String(i.code)}
                    data-integration={String(i.code)}
                    data-status={String(i.status)}
                    data-connectable={isConnectableIntegration(i) ? 'true' : undefined}
                    onClick={() => setSelectedIntegration(i)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td><strong>{nameOf({ name_en: String(i.name_en), name_tr: String(i.name_tr) }, locale)}</strong></td>
                    <td>{String(i.category)}</td>
                    <td>
                      <StatusBadge status={String(i.status)}>
                        {integrationStatusLabel(String(i.status))}
                      </StatusBadge>
                    </td>
                    <td>{String(i.block_reason || ((i.env_keys as string[]) || []).join(', ') || '—')}</td>
                    <td>{renderConnectActions(i, true)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selectedIntegration ? (
            <aside className="platform-detail" data-integration-detail data-integration-code={String(selectedIntegration.code)}>
              <h3>{nameOf({ name_en: String(selectedIntegration.name_en), name_tr: String(selectedIntegration.name_tr) }, locale)}</h3>
              <StatusBadge status={String(selectedIntegration.status)}>
                {integrationStatusLabel(String(selectedIntegration.status))}
              </StatusBadge>
              <p>{String(locale === 'tr' ? selectedIntegration.description_tr : selectedIntegration.description_en)}</p>
              {selectedIntegration.block_reason ? (
                <p className="platform-block-reason">{String(selectedIntegration.block_reason)}</p>
              ) : null}
              <p className="platform-muted">env: {((selectedIntegration.env_keys as string[]) || []).join(', ') || '—'}</p>
              {renderConnectActions(selectedIntegration)}
            </aside>
          ) : null}
        </SecSection>
      ) : null}

      {section === 'health' ? (
        <>
          {health ? <KpiGrid items={health.kpis} /> : null}
          <SecSection title={t('sections.moduleHealth')} description={t('sections.moduleHealthHint')}>
            <div className="sec-table-wrap">
              <table className="sec-table" data-module-health>
                <thead>
                  <tr><th>{t('cols.module')}</th><th>{t('cols.health')}</th><th>{t('cols.effective')}</th></tr>
                </thead>
                <tbody>
                  {moduleHealth.map((m) => (
                    <tr key={String(m.code)}>
                      <td><code>{String(m.code)}</code></td>
                      <td><StatusBadge status={String(m.health)} /></td>
                      <td><StatusBadge status={m.effective_enabled ? 'enabled' : 'disabled'} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SecSection>
          <SecSection title={t('sections.killSwitches')} description={t('sections.killSwitchesHint')}>
            <ul className="platform-list" data-kill-switches>
              {(killSwitches?.modules || []).map((m) => (
                <li key={m.code}>module <code>{m.code}</code></li>
              ))}
              {(killSwitches?.flags || []).map((f) => (
                <li key={f.key}>flag <code>{f.key}</code></li>
              ))}
              {!killSwitches?.modules.length && !killSwitches?.flags.length ? <li>{t('noKillSwitches')}</li> : null}
            </ul>
          </SecSection>
          <SecSection title={t('sections.environment')} description={t('sections.environmentHint')}>
            <pre className="platform-muted" data-environment-controls>{JSON.stringify({ environment: envControls?.environment, auth_enabled: envControls?.auth_enabled }, null, 2)}</pre>
          </SecSection>
        </>
      ) : null}

      {section === 'audit' ? (
        <SecSection title={t('sections.externalAccess')} description={t('sections.externalAccessHint')}>
          {canManage ? (
            <div className="platform-actions">
              <button
                type="button"
                className="admin-btn"
                data-record-audit
                onClick={() =>
                  void platformApi
                    .recordExternalAudit({
                      action: 'probe',
                      resource: 'platform',
                      outcome: 'allowed',
                      external_type: 'contractor',
                      detail: 'G15A audit probe',
                    })
                    .then(() => {
                      notifySuccess(t('saved'));
                      return load();
                    })
                }
              >
                {t('recordAuditProbe')}
              </button>
              <button
                type="button"
                className="admin-btn admin-btn--danger"
                data-record-expired-audit
                onClick={() =>
                  void platformApi
                    .recordExternalAudit({
                      action: 'access',
                      resource: 'external_session',
                      outcome: 'expired',
                      external_type: 'contractor',
                      detail: 'External access token/session expired (demo)',
                    })
                    .then(() => {
                      notifySuccess(t('saved'));
                      return load();
                    })
                }
              >
                Record expired access
              </button>
            </div>
          ) : null}
          {audit.some((row) => String(row.outcome) === 'expired') ? (
            <div className="platform-kill-banner" data-expired-access-state role="status">
              Expired access detected — external session/token no longer valid
            </div>
          ) : null}
          <div className="sec-table-wrap">
            <table className="sec-table" data-platform-audit>
              <thead>
                <tr><th>{t('cols.when')}</th><th>{t('cols.type')}</th><th>{t('cols.action')}</th><th>{t('cols.resource')}</th><th>{t('cols.outcome')}</th></tr>
              </thead>
              <tbody>
                {audit.length === 0 ? <tr><td colSpan={5}>{t('emptyAudit')}</td></tr> : audit.map((row) => (
                  <tr key={String(row.id)} data-audit-outcome={String(row.outcome)}>
                    <td>{String(row.created_at ?? '—')}</td>
                    <td>{String(row.external_type ?? '—')}</td>
                    <td>{String(row.action)}</td>
                    <td>{String(row.resource)}</td>
                    <td><StatusBadge status={String(row.outcome)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SecSection>
      ) : null}
    </main>
  );
}
