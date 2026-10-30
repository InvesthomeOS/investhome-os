'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { Route } from 'next';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';

import {
  archiveOffice,
  createDepartment,
  createOffice,
  createTeam,
  fetchBrandAssets,
  fetchBrands,
  fetchCompanyProfile,
  fetchDepartments,
  fetchOffices,
  fetchPreferences,
  fetchProviderStatuses,
  fetchSupportedOptions,
  fetchTeams,
  linkBrandAsset,
  setDefaultBrand,
  updateBrand,
  updateCompanyProfile,
  updatePreferences,
  type BrandAsset,
  type BrandProfile,
  type CompanyProfile,
  type Department,
  type Office,
  type PreferenceItem,
  type ProviderStatus,
  type SupportedOptions,
  type Team,
} from '@/lib/api/company-foundation';
import { hasPermission } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { useCompanyBranding } from '@/lib/company/company-context';
import {
  isSettingsTabAllowed,
  visibleSettingsEntries,
  type SettingsGroupId,
} from '@/lib/settings/settings-catalog';

function BrandPreviewPanel({ brand }: { brand: BrandProfile | null }) {
  const t = useTranslations('settings.brandPreview');
  if (!brand) {
    return <p>{t('noBrand')}</p>;
  }
  const radius = brand.border_radius_style === 'sharp' ? '0' : brand.border_radius_style === 'round' ? '999px' : '8px';
  return (
    <div className="settings-brand-preview" style={{ background: brand.background_color ?? '#f8fafc' }}>
      <div className="settings-brand-preview__header" style={{ background: brand.primary_color ?? '#1e3a5f' }}>
        <span style={{ color: '#fff', fontFamily: brand.font_heading ?? 'inherit' }}>{brand.brand_name}</span>
      </div>
      <div className="settings-brand-preview__body" style={{ color: brand.text_primary_color ?? '#0f172a' }}>
        <h3 style={{ fontFamily: brand.font_heading ?? 'inherit' }}>{t('sampleHeading')}</h3>
        <p style={{ fontFamily: brand.font_body ?? 'inherit', color: brand.text_secondary_color ?? '#64748b' }}>
          {t('sampleBody')}
        </p>
        <button
          type="button"
          className="auth-form__submit"
          style={{ background: brand.accent_color ?? '#0ea5e9', borderRadius: radius, maxWidth: '12rem' }}
        >
          {t('sampleButton')}
        </button>
        <div className="settings-brand-preview__card" style={{ background: brand.surface_color ?? '#fff', borderRadius: radius }}>
          {t('sampleCard')}
        </div>
        <div className="settings-brand-preview__alerts">
          <span style={{ color: brand.success_color ?? '#16a34a' }}>{t('success')}</span>
          <span style={{ color: brand.warning_color ?? '#d97706' }}>{t('warning')}</span>
          <span style={{ color: brand.error_color ?? '#dc2626' }}>{t('error')}</span>
        </div>
      </div>
    </div>
  );
}

function PreferenceEditor({
  items,
  canEdit,
  onSave,
}: {
  items: PreferenceItem[];
  canEdit: boolean;
  onSave: (updates: Record<string, unknown>) => Promise<void>;
}) {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const initial: Record<string, string> = {};
    for (const item of items) {
      if (item.is_secret) continue;
      initial[item.preference_key] =
        typeof item.value === 'string' || typeof item.value === 'number'
          ? String(item.value)
          : JSON.stringify(item.value ?? '');
    }
    setDraft(initial);
  }, [items]);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const updates: Record<string, unknown> = {};
      for (const item of items) {
        if (item.is_secret) continue;
        const raw = draft[item.preference_key];
        if (raw === undefined) continue;
        if (raw.startsWith('[') || raw.startsWith('{')) {
          try {
            updates[item.preference_key] = JSON.parse(raw);
          } catch {
            updates[item.preference_key] = raw;
          }
        } else if (/^\d+$/.test(raw)) {
          updates[item.preference_key] = Number(raw);
        } else {
          updates[item.preference_key] = raw;
        }
      }
      await onSave(updates);
      setMessage(t('saved'));
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : t('saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="admin-detail">
      {items.map((item) => (
        <label key={item.preference_key} className="auth-form__field">
          <span>{item.preference_key}</span>
          <input
            value={item.is_secret ? '••••••••' : (draft[item.preference_key] ?? '')}
            disabled={!canEdit || item.is_secret}
            onChange={(event) =>
              setDraft((prev) => ({ ...prev, [item.preference_key]: event.target.value }))
            }
          />
        </label>
      ))}
      {canEdit && (
        <button className="auth-form__submit" type="button" disabled={saving} onClick={() => void handleSave()}>
          {saving ? tCommon('loading') : t('savePreferences')}
        </button>
      )}
      {message && <p className="auth-form__success">{message}</p>}
    </div>
  );
}

function ProviderList({ providers }: { providers: ProviderStatus[] }) {
  const t = useTranslations('settings.providers');
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>{t('provider')}</th>
            <th>{t('status')}</th>
            <th>{t('configured')}</th>
          </tr>
        </thead>
        <tbody>
          {providers.map((provider) => (
            <tr key={provider.provider_id}>
              <td>{provider.provider_id}</td>
              <td>{provider.status}</td>
              <td>{provider.configured ? t('yes') : t('no')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SettingsWorkspace() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { refresh: refreshBranding } = useCompanyBranding();
  const catalogEntries = useMemo(() => visibleSettingsEntries(user), [user]);
  const platformTabs = catalogEntries.filter((entry) => entry.group === 'platform' && entry.tab);
  const integrationTabs = catalogEntries.filter((entry) => entry.group === 'integrations' && entry.tab);
  const crossLinks = catalogEntries.filter((entry) => entry.tab == null);
  const urlTab = searchParams.get('tab');
  const tabDenied = Boolean(urlTab && !isSettingsTabAllowed(user, urlTab));
  const activeTab =
    !tabDenied && urlTab && isSettingsTabAllowed(user, urlTab)
      ? urlTab
      : (platformTabs[0]?.tab ?? integrationTabs[0]?.tab ?? null);
  const canOpen = catalogEntries.some((entry) => entry.tab);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [offices, setOffices] = useState<Office[]>([]);
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [selectedBrandId, setSelectedBrandId] = useState<string | null>(null);
  const [brandDraft, setBrandDraft] = useState<BrandProfile | null>(null);
  const [assets, setAssets] = useState<BrandAsset[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [preferences, setPreferences] = useState<Record<string, PreferenceItem[]>>({});
  const [options, setOptions] = useState<SupportedOptions | null>(null);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const canUpdateSettings = user ? hasPermission(user, 'settings', 'update') : false;
  const canUpdateCompany = user ? hasPermission(user, 'company', 'update') : false;
  const canManageOffices = user ? hasPermission(user, 'offices', 'manage') : false;
  const canManageBrand = user ? hasPermission(user, 'brand', 'manage') : false;
  const canManageOrg = user ? hasPermission(user, 'organization', 'manage') : false;

  const defaultBrand = useMemo(() => brands.find((b) => b.is_default) ?? brands[0] ?? null, [brands]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [companyRes, officesRes, brandsRes, prefsRes, optionsRes, providersRes, deptRes] =
        await Promise.all([
          fetchCompanyProfile(),
          fetchOffices(),
          fetchBrands(),
          fetchPreferences(),
          fetchSupportedOptions(),
          fetchProviderStatuses(),
          fetchDepartments(),
        ]);
      setCompany(companyRes);
      setOffices(officesRes);
      setBrands(brandsRes);
      setPreferences(prefsRes.categories);
      setOptions(optionsRes);
      setProviders(providersRes.items);
      setDepartments(deptRes);
      const brand = brandsRes.find((b) => b.is_default) ?? brandsRes[0] ?? null;
      setSelectedBrandId(brand?.id ?? null);
      setBrandDraft(brand);
      if (brand) {
        setAssets(await fetchBrandAssets(brand.id));
      }
      if (deptRes[0]) {
        setTeams(await fetchTeams(deptRes[0].id));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (canOpen) {
      void load();
    } else {
      setLoading(false);
    }
  }, [canOpen, load]);

  useEffect(() => {
    if (!selectedBrandId) return;
    void fetchBrandAssets(selectedBrandId).then(setAssets).catch(() => setAssets([]));
    const brand = brands.find((b) => b.id === selectedBrandId) ?? null;
    setBrandDraft(brand);
  }, [selectedBrandId, brands]);

  const saveCompany = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!company || !canUpdateCompany) return;
    setMessage(null);
    const form = new FormData(event.currentTarget);
    const body: Record<string, string> = {};
    form.forEach((value, key) => {
      body[key] = String(value);
    });
    try {
      const updated = await updateCompanyProfile(body);
      setCompany(updated);
      setMessage(t('saved'));
      await refreshBranding();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : t('saveFailed'));
    }
  };

  const saveBrand = async () => {
    if (!brandDraft || !canManageBrand) return;
    setMessage(null);
    try {
      const updated = await updateBrand(brandDraft.id, {
        brand_name: brandDraft.brand_name,
        slogan: brandDraft.slogan,
        brand_description: brandDraft.brand_description,
        primary_color: brandDraft.primary_color,
        secondary_color: brandDraft.secondary_color,
        accent_color: brandDraft.accent_color,
        background_color: brandDraft.background_color,
        surface_color: brandDraft.surface_color,
        text_primary_color: brandDraft.text_primary_color,
        text_secondary_color: brandDraft.text_secondary_color,
        success_color: brandDraft.success_color,
        warning_color: brandDraft.warning_color,
        error_color: brandDraft.error_color,
        font_heading: brandDraft.font_heading,
        font_body: brandDraft.font_body,
        font_monospace: brandDraft.font_monospace,
        standard_disclaimer_tr: brandDraft.standard_disclaimer_tr,
        standard_disclaimer_en: brandDraft.standard_disclaimer_en,
        email_footer_tr: brandDraft.email_footer_tr,
        email_footer_en: brandDraft.email_footer_en,
      });
      setBrands((prev) => prev.map((b) => (b.id === updated.id ? updated : b)));
      setBrandDraft(updated);
      setMessage(t('saved'));
      await refreshBranding();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : t('saveFailed'));
    }
  };

  const handleSetDefaultBrand = async (brandId: string) => {
    if (!canManageBrand) return;
    const updated = await setDefaultBrand(brandId);
    setBrands((prev) => prev.map((b) => ({ ...b, is_default: b.id === updated.id })));
    await refreshBranding();
  };

  const handleArchiveOffice = async (officeId: string) => {
    if (!canManageOffices) return;
    await archiveOffice(officeId);
    setOffices((prev) => prev.filter((o) => o.id !== officeId));
  };

  const handleCreateOffice = async () => {
    if (!canManageOffices) return;
    const created = await createOffice({
      office_name: t('offices.newName'),
      office_code: `office-${Date.now()}`,
      office_type: 'other',
      country: company?.country,
    });
    setOffices((prev) => [...prev, created]);
  };

  const handleCreateDepartment = async () => {
    if (!canManageOrg) return;
    const created = await createDepartment({
      name: t('organization.newDepartment'),
      code: `dept-${Date.now()}`,
    });
    setDepartments((prev) => [...prev, created]);
  };

  const handleCreateTeam = async (departmentId: string) => {
    if (!canManageOrg) return;
    const created = await createTeam(departmentId, {
      name: t('organization.newTeam'),
      code: `team-${Date.now()}`,
    });
    setTeams((prev) => [...prev, created]);
  };

  const handleLinkAsset = async () => {
    if (!selectedBrandId || !canManageBrand) return;
    const documentId = window.prompt(t('brandAssets.documentIdPrompt'));
    if (!documentId) return;
    const asset = await linkBrandAsset(selectedBrandId, {
      document_id: documentId,
      asset_type: 'logo',
      title: t('brandAssets.linkedAsset'),
    });
    setAssets((prev) => [asset, ...prev]);
  };

  const savePrefs = async (updates: Record<string, unknown>) => {
    const next = await updatePreferences(updates);
    setPreferences(next.categories);
    await refreshBranding();
  };

  if (!canOpen) {
    return (
      <main className="dashboard">
        <p>{t('accessDenied')}</p>
      </main>
    );
  }

  const selectTab = (tab: string) => {
    router.replace(`/dashboard/settings?tab=${tab}` as Route);
  };

  const renderTabGroup = (group: SettingsGroupId, tabs: typeof platformTabs) => {
    if (!tabs.length) return null;
    return (
      <div className="settings-nav-group">
        <p className="settings-nav-group__label">{t(`groups.${group}`)}</p>
        <nav className="documents-tabs settings-tabs" aria-label={t(`groups.${group}`)}>
          {tabs.map((entry) => (
            <button
              key={entry.id}
              type="button"
              className={
                activeTab === entry.tab
                  ? 'documents-tabs__tab documents-tabs__tab--active'
                  : 'documents-tabs__tab'
              }
              aria-current={activeTab === entry.tab ? 'page' : undefined}
              onClick={() => selectTab(entry.tab ?? entry.id)}
            >
              {t(`tabs.${entry.tab}` as 'tabs.company')}
            </button>
          ))}
        </nav>
      </div>
    );
  };

  const crossGroups: SettingsGroupId[] = ['personal', 'crm', 'integrations', 'access', 'security'];

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('subtitle')}</p>
      </header>

      <div className="settings-nav-groups">
        {renderTabGroup('platform', platformTabs)}
        {renderTabGroup('integrations', integrationTabs)}
      </div>

      <div className="settings-related">
        {crossGroups.map((group) => {
          const links = crossLinks.filter((entry) => entry.group === group);
          if (!links.length) return null;
          return (
            <div key={group}>
              <p className="settings-nav-group__label">{t(`groups.${group}`)}</p>
              <div className="settings-related__links">
                {links.map((entry) => (
                  <Link key={entry.id} href={entry.href as Route}>
                    {t(`catalog.${entry.id}` as 'catalog.profile')}
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {loading && <p>{tCommon('loading')}</p>}
      {error && <p className="auth-form__error">{error}</p>}
      {message && <p className="auth-form__success">{message}</p>}
      {tabDenied && <p>{t('accessDenied')}</p>}

      {!loading && !tabDenied && activeTab === 'company' && company && (
        <form className="admin-detail auth-form" onSubmit={(e) => void saveCompany(e)}>
          {[
            'company_name',
            'legal_name',
            'short_name',
            'slogan',
            'primary_email',
            'primary_phone',
            'website',
            'country',
            'city',
            'default_language',
            'default_timezone',
            'default_currency',
          ].map((field) => (
            <label key={field} className="auth-form__field">
              <span>{t(`company.fields.${field}` as never)}</span>
              <input
                name={field}
                defaultValue={String((company as Record<string, unknown>)[field] ?? '')}
                disabled={!canUpdateCompany}
              />
            </label>
          ))}
          {canUpdateCompany && (
            <button className="auth-form__submit" type="submit">
              {t('saveCompany')}
            </button>
          )}
        </form>
      )}

      {!loading && !tabDenied && activeTab === 'offices' && (
        <section>
          {canManageOffices && (
            <button className="leads__button" type="button" onClick={() => void handleCreateOffice()}>
              {t('offices.add')}
            </button>
          )}
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>{t('offices.name')}</th>
                  <th>{t('offices.code')}</th>
                  <th>{t('offices.type')}</th>
                  <th>{t('offices.city')}</th>
                  <th>{t('offices.primary')}</th>
                  {canManageOffices && <th>{t('offices.actions')}</th>}
                </tr>
              </thead>
              <tbody>
                {offices.map((office) => (
                  <tr key={office.id}>
                    <td>{office.office_name}</td>
                    <td>{office.office_code}</td>
                    <td>{office.office_type}</td>
                    <td>{office.city ?? tCommon('noValue')}</td>
                    <td>{office.is_primary ? t('offices.yes') : t('offices.no')}</td>
                    {canManageOffices && (
                      <td>
                        <button type="button" className="leads__button leads__button--ghost" onClick={() => void handleArchiveOffice(office.id)}>
                          {t('offices.archive')}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {!loading && !tabDenied && activeTab === 'brand' && brandDraft && (
        <div className="settings-brand-layout">
          <div className="admin-detail auth-form">
            <label className="auth-form__field">
              <span>{t('brand.defaultSelector')}</span>
              <select
                value={selectedBrandId ?? ''}
                onChange={(event) => setSelectedBrandId(event.target.value)}
              >
                {brands.map((brand) => (
                  <option key={brand.id} value={brand.id}>
                    {brand.brand_name}
                    {brand.is_default ? ` (${t('brand.default')})` : ''}
                  </option>
                ))}
              </select>
            </label>
            {canManageBrand && selectedBrandId && !defaultBrand?.is_default && (
              <button type="button" className="leads__button" onClick={() => void handleSetDefaultBrand(selectedBrandId)}>
                {t('brand.setDefault')}
              </button>
            )}
            {[
              'brand_name',
              'slogan',
              'brand_description',
              'primary_color',
              'secondary_color',
              'accent_color',
              'font_heading',
              'font_body',
              'standard_disclaimer_tr',
              'standard_disclaimer_en',
            ].map((field) => (
              <label key={field} className="auth-form__field">
                <span>{t(`brand.fields.${field}` as never)}</span>
                {field.includes('disclaimer') || field === 'brand_description' ? (
                  <textarea
                    rows={3}
                    value={String((brandDraft as Record<string, unknown>)[field] ?? '')}
                    disabled={!canManageBrand}
                    onChange={(event) =>
                      setBrandDraft((prev) => (prev ? { ...prev, [field]: event.target.value } : prev))
                    }
                  />
                ) : (
                  <input
                    value={String((brandDraft as Record<string, unknown>)[field] ?? '')}
                    disabled={!canManageBrand}
                    onChange={(event) =>
                      setBrandDraft((prev) => (prev ? { ...prev, [field]: event.target.value } : prev))
                    }
                  />
                )}
              </label>
            ))}
            {canManageBrand && (
              <button className="auth-form__submit" type="button" onClick={() => void saveBrand()}>
                {t('saveBrand')}
              </button>
            )}
          </div>
          <BrandPreviewPanel brand={brandDraft} />
        </div>
      )}

      {!loading && !tabDenied && activeTab === 'brandAssets' && (
        <section>
          {canManageBrand && (
            <button className="leads__button" type="button" onClick={() => void handleLinkAsset()}>
              {t('brandAssets.link')}
            </button>
          )}
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>{t('brandAssets.title')}</th>
                  <th>{t('brandAssets.type')}</th>
                  <th>{t('brandAssets.document')}</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => (
                  <tr key={asset.id}>
                    <td>{asset.title ?? tCommon('noValue')}</td>
                    <td>{asset.asset_type}</td>
                    <td>{asset.document_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {!loading && !tabDenied && activeTab === 'organization' && (
        <section>
          {canManageOrg && (
            <button className="leads__button" type="button" onClick={() => void handleCreateDepartment()}>
              {t('organization.addDepartment')}
            </button>
          )}
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>{t('organization.name')}</th>
                  <th>{t('organization.code')}</th>
                </tr>
              </thead>
              <tbody>
                {departments.map((dept) => (
                  <tr key={dept.id}>
                    <td>{dept.name}</td>
                    <td>{dept.code}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {departments[0] != null && canManageOrg && (
            <button className="leads__button" type="button" onClick={() => void handleCreateTeam(departments[0]!.id)}>
              {t('organization.addTeam')}
            </button>
          )}
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>{t('organization.teamName')}</th>
                  <th>{t('organization.code')}</th>
                </tr>
              </thead>
              <tbody>
                {teams.map((team) => (
                  <tr key={team.id}>
                    <td>{team.name}</td>
                    <td>{team.code}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {!loading && !tabDenied && activeTab === 'localization' && (
        <PreferenceEditor
          items={preferences.general ?? []}
          canEdit={canUpdateSettings}
          onSave={savePrefs}
        />
      )}

      {!loading && !tabDenied && activeTab === 'currency' && (
        <div>
          <p>{t('currency.supported')}: {options?.currencies.join(', ')}</p>
          <PreferenceEditor
            items={[...(preferences.general ?? []), ...(preferences.finance ?? [])].filter((item) =>
              item.preference_key.includes('currency') || item.preference_key.includes('measurement') || item.preference_key.includes('area'),
            )}
            canEdit={canUpdateSettings}
            onSave={savePrefs}
          />
        </div>
      )}

      {!loading && !tabDenied && activeTab === 'documents' && (
        <PreferenceEditor items={preferences.documents ?? []} canEdit={canUpdateSettings} onSave={savePrefs} />
      )}

      {!loading && !tabDenied && activeTab === 'notifications' && (
        <PreferenceEditor items={preferences.notifications ?? []} canEdit={canUpdateSettings} onSave={savePrefs} />
      )}

      {!loading && !tabDenied && activeTab === 'ai' && (
        <div>
          <p>{t('readinessNotice')}</p>
          <ProviderList providers={providers.filter((p) => p.category === 'ai')} />
          <PreferenceEditor items={preferences.ai ?? []} canEdit={canUpdateSettings} onSave={savePrefs} />
        </div>
      )}

      {!loading && !tabDenied && activeTab === 'storage' && (
        <div>
          <p>{t('readinessNotice')}</p>
          <ProviderList providers={providers.filter((p) => p.category === 'storage')} />
          <PreferenceEditor items={preferences.storage ?? []} canEdit={canUpdateSettings} onSave={savePrefs} />
        </div>
      )}

      {!loading && !tabDenied && activeTab === 'integrations' && (
        <div>
          <p>{t('readinessNotice')}</p>
          <PreferenceEditor items={preferences.integrations ?? []} canEdit={canUpdateSettings} onSave={savePrefs} />
        </div>
      )}
    </main>
  );
}
