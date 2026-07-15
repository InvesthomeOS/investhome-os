'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  applyMaterialPackage,
  fetchMaterialPackages,
  fetchStylePresets,
  saveDesignVersion,
  type DesignParameters,
  type DesignProject,
  type DesignVersion,
  type MaterialPackage,
  type StylePreset,
} from '@/lib/api/design';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

interface MaterialsStyleProps {
  design: DesignProject;
  latestVersion: DesignVersion | null;
  onVersionSaved: () => void;
}

function Swatch({ color, label }: { color: string; label: string }) {
  return (
    <div className="design-materials__swatch" title={label}>
      <span className="design-materials__swatch-color" style={{ backgroundColor: color }} />
      <span className="design-materials__swatch-label">{label}</span>
    </div>
  );
}

export function MaterialsStyle({ design, latestVersion, onVersionSaved }: MaterialsStyleProps) {
  const t = useTranslations('design.materialsStyle');
  const tCommon = useTranslations('common');
  const { user } = useAuth();

  const [presets, setPresets] = useState<StylePreset[]>([]);
  const [packages, setPackages] = useState<MaterialPackage[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);
  const [selectedPackageId, setSelectedPackageId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSave = user ? hasPermission(user, 'design', 'save_version') : false;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [presetRes, packageRes] = await Promise.all([
        fetchStylePresets(),
        fetchMaterialPackages(),
      ]);
      setPresets(presetRes.items);
      setPackages(packageRes.items);
      const params = latestVersion?.design_parameters;
      setSelectedPresetId(params?.selected_style_preset_id ?? null);
      setSelectedPackageId(params?.selected_material_package_id ?? null);
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [latestVersion, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedPreset = presets.find((p) => p.id === selectedPresetId) ?? null;
  const selectedPackage = packages.find((p) => p.id === selectedPackageId) ?? null;

  const buildParameters = (): DesignParameters => {
    const base = latestVersion?.design_parameters ?? {
      mode: 'basic_overlay',
      palette: 'default',
      regions: [],
      backgroundColor: '#F5F0E8',
    };
    return {
      ...base,
      selected_style_preset_id: selectedPresetId,
      selected_material_package_id: selectedPackageId,
      color_overlays: selectedPreset?.color_palette
        ? [{ source: 'style_preset', palette: selectedPreset.color_palette }]
        : base.color_overlays ?? [],
    };
  };

  const handleSaveStyle = async () => {
    if (!canSave || !selectedPresetId) return;
    setSaving(true);
    setError(null);
    try {
      await saveDesignVersion(design.id, buildParameters());
      onVersionSaved();
    } catch {
      setError(t('saveError'));
    } finally {
      setSaving(false);
    }
  };

  const handleApplyMaterials = async () => {
    if (!canSave || !selectedPackageId) return;
    setSaving(true);
    setError(null);
    try {
      await applyMaterialPackage(design.id, selectedPackageId, buildParameters());
      onVersionSaved();
    } catch {
      setError(t('saveError'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p className="leads__state">{tCommon('loading')}</p>;
  }

  return (
    <div className="design-materials">
      <h3 className="leads-form__section-title">{t('title')}</h3>
      {error && <p className="leads__state leads__state--error">{error}</p>}

      <section className="design-materials__section">
        <h4>{t('stylePreset')}</h4>
        <select
          className="leads__select"
          value={selectedPresetId ?? ''}
          onChange={(e) => setSelectedPresetId(e.target.value || null)}
        >
          <option value="">{t('selectPreset')}</option>
          {presets.map((preset) => (
            <option key={preset.id} value={preset.id}>
              {preset.name}{preset.is_system_preset ? ` (${t('system')})` : ''}
            </option>
          ))}
        </select>
        {selectedPreset && (
          <div className="design-materials__swatches">
            {selectedPreset.color_palette &&
              Object.entries(selectedPreset.color_palette).map(([key, color]) => (
                <Swatch key={key} color={color} label={key} />
              ))}
            {selectedPreset.description && <p>{selectedPreset.description}</p>}
          </div>
        )}
        {canSave && (
          <button type="button" className="leads__button leads__button--primary" disabled={saving || !selectedPresetId} onClick={() => void handleSaveStyle()}>
            {saving ? tCommon('loading') : t('saveStyle')}
          </button>
        )}
      </section>

      <section className="design-materials__section">
        <h4>{t('materialPackage')}</h4>
        <select
          className="leads__select"
          value={selectedPackageId ?? ''}
          onChange={(e) => setSelectedPackageId(e.target.value || null)}
        >
          <option value="">{t('selectPackage')}</option>
          {packages.map((pkg) => (
            <option key={pkg.id} value={pkg.id}>{pkg.name}</option>
          ))}
        </select>
        {selectedPackage && (
          <dl className="leads-detail__grid design-materials__package-details">
            {(['flooring', 'wall_finish', 'countertop', 'cabinetry', 'metal_finish'] as const).map((field) =>
              selectedPackage[field] ? (
                <div key={field}>
                  <dt>{t(`fields.${field}`)}</dt>
                  <dd>{selectedPackage[field]}</dd>
                </div>
              ) : null,
            )}
          </dl>
        )}
        {selectedPackage?.color_palette && (
          <div className="design-materials__swatches">
            {Object.entries(selectedPackage.color_palette).map(([key, color]) => (
              <Swatch key={key} color={color} label={key} />
            ))}
          </div>
        )}
        {canSave && (
          <button type="button" className="leads__button leads__button--primary" disabled={saving || !selectedPackageId} onClick={() => void handleApplyMaterials()}>
            {saving ? tCommon('loading') : t('applyMaterials')}
          </button>
        )}
      </section>
    </div>
  );
}
