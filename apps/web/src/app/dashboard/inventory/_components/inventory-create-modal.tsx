'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Dialog, Select } from '@investhome/ui';

import {
  type Building,
  type Floor,
  type InventoryAsset,
  type InventoryAssetInput,
} from '@/lib/api/inventory';
import type { Project } from '@/lib/api/projects';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

interface InventoryCreateModalProps {
  mode: 'create' | 'edit' | null;
  asset: InventoryAsset | null;
  projects: Project[];
  buildings: Building[];
  floors: Floor[];
  submitting: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (input: InventoryAssetInput) => void;
  onProjectChange: (projectId: string) => void;
  onBuildingChange: (buildingId: string) => void;
}

const EMPTY_FORM: InventoryAssetInput = {
  project_id: '',
  building_id: null,
  floor_id: null,
  display_id: '',
  legal_identifier: null,
  asset_type: 'residential_unit',
  usage_type: 'residential',
  unit_subtype: null,
  bedrooms: null,
  bathrooms: null,
  interior_area_sqft: null,
  exterior_area_sqft: null,
  total_area_sqft: null,
  orientation: null,
  view_type: null,
  currency: 'USD',
  release_date: null,
  delivery_date: null,
  description: null,
  notes: null,
};

export function InventoryCreateModal({
  mode,
  asset,
  projects,
  buildings,
  floors,
  submitting,
  error,
  onClose,
  onSubmit,
  onProjectChange,
  onBuildingChange,
}: InventoryCreateModalProps) {
  const t = useTranslations('inventory');
  const tCommon = useTranslations('common');
  const { assetTypeOptions, usageTypeOptions } = useInventoryLabels();
  const [form, setForm] = useState<InventoryAssetInput>(EMPTY_FORM);

  useEffect(() => {
    if (mode === 'edit' && asset) {
      setForm({
        project_id: asset.project_id,
        building_id: asset.building_id,
        floor_id: asset.floor_id,
        display_id: asset.display_id,
        legal_identifier: asset.legal_identifier,
        asset_type: asset.asset_type,
        usage_type: asset.usage_type,
        unit_subtype: asset.unit_subtype,
        bedrooms: asset.bedrooms ? Number(asset.bedrooms) : null,
        bathrooms: asset.bathrooms ? Number(asset.bathrooms) : null,
        interior_area_sqft: asset.interior_area_sqft ? Number(asset.interior_area_sqft) : null,
        exterior_area_sqft: asset.exterior_area_sqft ? Number(asset.exterior_area_sqft) : null,
        total_area_sqft: asset.total_area_sqft ? Number(asset.total_area_sqft) : null,
        orientation: asset.orientation,
        view_type: asset.view_type,
        currency: asset.currency,
        release_date: asset.release_date,
        delivery_date: asset.delivery_date,
        description: asset.description,
        notes: asset.notes,
      });
      onProjectChange(asset.project_id);
      if (asset.building_id) onBuildingChange(asset.building_id);
      return;
    }
    if (mode === 'create') {
      setForm(EMPTY_FORM);
    }
  }, [asset, mode, onBuildingChange, onProjectChange]);

  const projectOptions = useMemo(
    () => projects.map((p) => ({ value: p.id, label: p.project_name })),
    [projects],
  );

  const buildingOptions = useMemo(
    () => buildings.map((b) => ({ value: b.id, label: `${b.code} — ${b.name}` })),
    [buildings],
  );

  const floorOptions = useMemo(
    () =>
      floors.map((f) => ({
        value: f.id,
        label: f.display_name ?? f.level_code ?? String(f.floor_number),
      })),
    [floors],
  );

  if (!mode) return null;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    onSubmit({
      ...form,
      display_id: form.display_id.trim(),
      legal_identifier: form.legal_identifier?.trim() || null,
      unit_subtype: form.unit_subtype?.trim() || null,
      orientation: form.orientation?.trim() || null,
      view_type: form.view_type?.trim() || null,
      description: form.description?.trim() || null,
      notes: form.notes?.trim() || null,
      building_id: form.building_id || null,
      floor_id: form.floor_id || null,
    });
  };

  const isLandParcel = form.asset_type === 'land_parcel';

  return (
    <Dialog
      open
      onClose={onClose}
      title={mode === 'create' ? t('form.createTitle') : t('form.editTitle')}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            {tCommon('cancel')}
          </Button>
          <Button variant="primary" onClick={handleSubmit} disabled={submitting || !form.project_id || !form.display_id}>
            {submitting ? tCommon('saving') : tCommon('save')}
          </Button>
        </>
      }
    >
      {error && <p className="leads__state leads__state--error">{error}</p>}
      {mode === 'edit' && asset && (
        <p className="inventory__modal-subtitle">
          {t('form.systemCode')}: <strong>{asset.system_code}</strong>
        </p>
      )}
      <form className="leads-form" onSubmit={handleSubmit}>
        <Select
          label={t('form.project')}
          value={form.project_id}
          required
          onChange={(event) => {
            const projectId = event.target.value;
            setForm((current) => ({
              ...current,
              project_id: projectId,
              building_id: null,
              floor_id: null,
            }));
            onProjectChange(projectId);
          }}
        >
          <option value="">{t('form.selectProject')}</option>
          {projectOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>

        <label className="ih-field">
          <span className="ih-field__label">{t('form.displayId')}</span>
          <input
            className="ih-input"
            value={form.display_id}
            required
            onChange={(event) => setForm((current) => ({ ...current, display_id: event.target.value }))}
          />
        </label>

        <label className="ih-field">
          <span className="ih-field__label">{t('form.legalIdentifier')}</span>
          <input
            className="ih-input"
            value={form.legal_identifier ?? ''}
            onChange={(event) =>
              setForm((current) => ({ ...current, legal_identifier: event.target.value || null }))
            }
          />
        </label>

        <Select
          label={t('form.assetType')}
          value={form.asset_type}
          onChange={(event) =>
            setForm((current) => ({
              ...current,
              asset_type: event.target.value as InventoryAssetInput['asset_type'],
            }))
          }
        >
          {assetTypeOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>

        <Select
          label={t('form.usageType')}
          value={form.usage_type}
          onChange={(event) =>
            setForm((current) => ({
              ...current,
              usage_type: event.target.value as InventoryAssetInput['usage_type'],
            }))
          }
        >
          {usageTypeOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>

        {!isLandParcel && (
          <>
            <Select
              label={t('form.building')}
              value={form.building_id ?? ''}
              onChange={(event) => {
                const buildingId = event.target.value || null;
                setForm((current) => ({ ...current, building_id: buildingId, floor_id: null }));
                if (buildingId) onBuildingChange(buildingId);
              }}
            >
              <option value="">{t('form.selectBuilding')}</option>
              {buildingOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>

            <Select
              label={t('form.floor')}
              value={form.floor_id ?? ''}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  floor_id: event.target.value || null,
                }))
              }
              disabled={!form.building_id}
            >
              <option value="">{t('form.selectFloor')}</option>
              {floorOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </>
        )}

        <label className="ih-field">
          <span className="ih-field__label">{t('form.unitSubtype')}</span>
          <input
            className="ih-input"
            value={form.unit_subtype ?? ''}
            onChange={(event) =>
              setForm((current) => ({ ...current, unit_subtype: event.target.value || null }))
            }
          />
        </label>

        <div className="inventory__form-grid">
          <label className="ih-field">
            <span className="ih-field__label">{t('form.bedrooms')}</span>
            <input
              className="ih-input"
              type="number"
              min={0}
              step={0.5}
              value={form.bedrooms ?? ''}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  bedrooms: event.target.value ? Number(event.target.value) : null,
                }))
              }
            />
          </label>
          <label className="ih-field">
            <span className="ih-field__label">{t('form.bathrooms')}</span>
            <input
              className="ih-input"
              type="number"
              min={0}
              step={0.5}
              value={form.bathrooms ?? ''}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  bathrooms: event.target.value ? Number(event.target.value) : null,
                }))
              }
            />
          </label>
        </div>

        <div className="inventory__form-grid">
          <label className="ih-field">
            <span className="ih-field__label">{t('form.interiorArea')}</span>
            <input
              className="ih-input"
              type="number"
              min={0}
              value={form.interior_area_sqft ?? ''}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  interior_area_sqft: event.target.value ? Number(event.target.value) : null,
                }))
              }
            />
          </label>
          <label className="ih-field">
            <span className="ih-field__label">{t('form.exteriorArea')}</span>
            <input
              className="ih-input"
              type="number"
              min={0}
              value={form.exterior_area_sqft ?? ''}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  exterior_area_sqft: event.target.value ? Number(event.target.value) : null,
                }))
              }
            />
          </label>
          <label className="ih-field">
            <span className="ih-field__label">{t('form.totalArea')}</span>
            <input
              className="ih-input"
              type="number"
              min={0}
              value={form.total_area_sqft ?? ''}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  total_area_sqft: event.target.value ? Number(event.target.value) : null,
                }))
              }
            />
          </label>
        </div>

        <div className="inventory__form-grid">
          <label className="ih-field">
            <span className="ih-field__label">{t('form.orientation')}</span>
            <input
              className="ih-input"
              value={form.orientation ?? ''}
              onChange={(event) =>
                setForm((current) => ({ ...current, orientation: event.target.value || null }))
              }
            />
          </label>
          <label className="ih-field">
            <span className="ih-field__label">{t('form.viewType')}</span>
            <input
              className="ih-input"
              value={form.view_type ?? ''}
              onChange={(event) =>
                setForm((current) => ({ ...current, view_type: event.target.value || null }))
              }
            />
          </label>
        </div>

        <div className="inventory__form-grid">
          <label className="ih-field">
            <span className="ih-field__label">{t('form.releaseDate')}</span>
            <input
              className="ih-input"
              type="date"
              value={form.release_date ?? ''}
              onChange={(event) =>
                setForm((current) => ({ ...current, release_date: event.target.value || null }))
              }
            />
          </label>
          <label className="ih-field">
            <span className="ih-field__label">{t('form.deliveryDate')}</span>
            <input
              className="ih-input"
              type="date"
              value={form.delivery_date ?? ''}
              onChange={(event) =>
                setForm((current) => ({ ...current, delivery_date: event.target.value || null }))
              }
            />
          </label>
        </div>

        <label className="ih-field">
          <span className="ih-field__label">{t('form.description')}</span>
          <textarea
            className="ih-input ih-input--textarea"
            value={form.description ?? ''}
            onChange={(event) =>
              setForm((current) => ({ ...current, description: event.target.value || null }))
            }
            rows={2}
          />
        </label>

        <label className="ih-field">
          <span className="ih-field__label">{t('form.notes')}</span>
          <textarea
            className="ih-input ih-input--textarea"
            value={form.notes ?? ''}
            onChange={(event) =>
              setForm((current) => ({ ...current, notes: event.target.value || null }))
            }
            rows={2}
          />
        </label>
      </form>
    </Dialog>
  );
}
