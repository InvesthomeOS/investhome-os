'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  fetchDesignSourceRegions,
  saveDesignVersion,
  type DesignParameters,
  type DesignProject,
  type DesignSourceRegion,
  type DesignVersion,
} from '@/lib/api/design';
import { drawingPreviewUrl } from '@/lib/api/drawing-intelligence';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

const DEFAULT_PALETTE = [
  '#E8D5B7',
  '#C4B5A0',
  '#A8C5DA',
  '#B5D4C8',
  '#D4C5E8',
  '#F5E6D3',
  '#D9E4EC',
  '#E8C4C4',
];

interface ColorStudioProps {
  design: DesignProject;
  latestVersion: DesignVersion | null;
  onVersionSaved: () => void;
}

function buildInitialParameters(
  mode: string,
  regions: DesignSourceRegion[],
  latestVersion: DesignVersion | null,
): DesignParameters {
  if (latestVersion?.design_parameters) {
    return latestVersion.design_parameters;
  }
  if (mode === 'room_regions' && regions.length > 0) {
    return {
      mode: 'room_regions',
      palette: 'default',
      regions: regions.map((region, index) => ({
        id: region.id,
        label: region.label,
        color: DEFAULT_PALETTE[index % DEFAULT_PALETTE.length] ?? '#E8D5B7',
      })),
      backgroundColor: '#FFFFFF',
    };
  }
  return {
    mode: 'basic_overlay',
    palette: 'default',
    regions: [],
    backgroundColor: '#F5F0E8',
  };
}

export function ColorStudio({ design, latestVersion, onVersionSaved }: ColorStudioProps) {
  const t = useTranslations('design.colorStudio');
  const tCommon = useTranslations('common');
  const { user } = useAuth();

  const [regions, setRegions] = useState<DesignSourceRegion[]>([]);
  const [mode, setMode] = useState<'basic_overlay' | 'room_regions'>('basic_overlay');
  const [parameters, setParameters] = useState<DesignParameters | null>(null);
  const [showAfter, setShowAfter] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSave = user ? hasPermission(user, 'design', 'save_version') : false;

  const loadRegions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchDesignSourceRegions(design.id);
      const nextMode = response.mode === 'room_regions' ? 'room_regions' : 'basic_overlay';
      setMode(nextMode);
      setRegions(response.regions);
      setParameters(buildInitialParameters(nextMode, response.regions, latestVersion));
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [design.id, latestVersion, t]);

  useEffect(() => {
    void loadRegions();
  }, [loadRegions]);

  const overlayStyle = useMemo(() => {
    if (!parameters) return {};
    if (parameters.mode === 'basic_overlay') {
      return { backgroundColor: parameters.backgroundColor ?? '#F5F0E8' };
    }
    return { backgroundColor: parameters.backgroundColor ?? '#FFFFFF' };
  }, [parameters]);

  const handleRegionColorChange = (regionId: string, color: string) => {
    if (!parameters) return;
    setParameters({
      ...parameters,
      regions: parameters.regions.map((region) =>
        region.id === regionId ? { ...region, color } : region,
      ),
    });
  };

  const handleBackgroundChange = (color: string) => {
    if (!parameters) return;
    setParameters({ ...parameters, backgroundColor: color });
  };

  const handleReset = () => {
    setParameters(buildInitialParameters(mode, regions, null));
  };

  const handleSave = async () => {
    if (!parameters || !canSave) return;
    setSaving(true);
    setError(null);
    try {
      await saveDesignVersion(design.id, parameters);
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
    <div className="design-color-studio">
      <div className="design-color-studio__header">
        <div>
          <h3 className="leads-form__section-title">{t('title')}</h3>
          <p className="design-color-studio__mode-label">
            {mode === 'room_regions' ? t('modeRoomRegions') : t('modeBasicOverlay')}
          </p>
        </div>
        <div className="design-color-studio__actions">
          <button
            type="button"
            className="leads__button leads__button--secondary"
            onClick={() => setShowAfter((prev) => !prev)}
          >
            {showAfter ? t('showBefore') : t('showAfter')}
          </button>
          <button type="button" className="leads__button leads__button--ghost" onClick={handleReset}>
            {t('reset')}
          </button>
          {canSave && (
            <button
              type="button"
              className="leads__button leads__button--primary"
              disabled={saving}
              onClick={() => void handleSave()}
            >
              {saving ? tCommon('loading') : t('saveVersion')}
            </button>
          )}
        </div>
      </div>

      {error && <p className="leads__state leads__state--error">{error}</p>}

      <div className="design-color-studio__layout">
        <div className="design-color-studio__preview">
          <div className="design-color-studio__preview-pane">
            <span className="design-color-studio__preview-label">
              {showAfter ? t('afterLabel') : t('beforeLabel')}
            </span>
            <div className="design-color-studio__preview-frame">
              <iframe
                title={design.title}
                src={drawingPreviewUrl(design.document_id)}
                className="documents-preview__frame"
              />
              {showAfter && parameters && (
                <div className="design-color-studio__overlay" style={overlayStyle}>
                  {parameters.mode === 'room_regions' &&
                    parameters.regions.map((region) => (
                      <div
                        key={region.id}
                        className="design-color-studio__region-chip"
                        style={{ backgroundColor: region.color }}
                        title={region.label ?? region.id}
                      >
                        {region.label ?? region.id}
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <aside className="design-color-studio__controls">
          <h4 className="leads-form__section-title">{t('palette')}</h4>
          <div className="design-color-studio__palette">
            {DEFAULT_PALETTE.map((color) => (
              <button
                key={color}
                type="button"
                className="design-color-studio__swatch"
                style={{ backgroundColor: color }}
                aria-label={color}
                onClick={() => handleBackgroundChange(color)}
              />
            ))}
          </div>

          {mode === 'basic_overlay' ? (
            <label className="leads-form__field">
              <span>{t('backgroundColor')}</span>
              <input
                type="color"
                value={parameters?.backgroundColor ?? '#F5F0E8'}
                onChange={(event) => handleBackgroundChange(event.target.value)}
              />
            </label>
          ) : (
            <div className="design-color-studio__regions">
              {parameters?.regions.map((region) => (
                <label key={region.id} className="design-color-studio__region-row">
                  <span>{region.label ?? region.id}</span>
                  <input
                    type="color"
                    value={region.color}
                    onChange={(event) => handleRegionColorChange(region.id, event.target.value)}
                  />
                </label>
              ))}
            </div>
          )}

          {mode === 'basic_overlay' && (
            <p className="design-color-studio__hint">{t('basicOverlayHint')}</p>
          )}
        </aside>
      </div>
    </div>
  );
}
