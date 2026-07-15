'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  compareDesignVersions,
  formatDesignDate,
  type DesignProject,
  type DesignVersion,
  type VersionCompareResult,
} from '@/lib/api/design';
import { useDesignLabels } from '@/lib/i18n/design-labels';

interface CompareVersionsProps {
  design: DesignProject;
  versions: DesignVersion[];
}

export function CompareVersions({ design, versions }: CompareVersionsProps) {
  const t = useTranslations('design.compareVersions');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getStatusLabel } = useDesignLabels();

  const [versionAId, setVersionAId] = useState('');
  const [versionBId, setVersionBId] = useState('');
  const [result, setResult] = useState<VersionCompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (versions.length >= 2) {
      setVersionAId(versions[1]?.id ?? '');
      setVersionBId(versions[0]?.id ?? '');
    } else if (versions.length === 1) {
      setVersionAId(versions[0]?.id ?? '');
    }
  }, [versions]);

  const handleCompare = useCallback(async () => {
    if (!versionAId || !versionBId || versionAId === versionBId) {
      setError(t('selectTwo'));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const compareResult = await compareDesignVersions(design.id, versionAId, versionBId);
      setResult(compareResult);
    } catch {
      setError(t('compareError'));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [design.id, versionAId, versionBId, t]);

  useEffect(() => {
    if (versionAId && versionBId && versionAId !== versionBId) {
      void handleCompare();
    }
  }, [versionAId, versionBId, handleCompare]);

  const versionLabel = (v: DesignVersion) => t('versionLabel', { number: v.version_number });

  return (
    <div className="design-compare">
      <h3 className="leads-form__section-title">{t('title')}</h3>
      <p className="design-compare__note">{t('honestNote')}</p>

      <div className="design-compare__selectors">
        <label className="leads-form__field">
          <span>{t('versionA')}</span>
          <select className="leads__select" value={versionAId} onChange={(e) => setVersionAId(e.target.value)}>
            <option value="">{t('selectVersion')}</option>
            {versions.map((v) => (
              <option key={v.id} value={v.id}>{versionLabel(v)} — {formatDesignDate(v.created_at, locale)}</option>
            ))}
          </select>
        </label>
        <label className="leads-form__field">
          <span>{t('versionB')}</span>
          <select className="leads__select" value={versionBId} onChange={(e) => setVersionBId(e.target.value)}>
            <option value="">{t('selectVersion')}</option>
            {versions.map((v) => (
              <option key={v.id} value={v.id}>{versionLabel(v)} — {formatDesignDate(v.created_at, locale)}</option>
            ))}
          </select>
        </label>
        <button type="button" className="leads__button leads__button--secondary" disabled={loading} onClick={() => void handleCompare()}>
          {loading ? tCommon('loading') : t('compare')}
        </button>
      </div>

      {error && <p className="leads__state leads__state--error">{error}</p>}

      {result && (
        <div className="design-compare__results">
          <div className="design-compare__panes">
            <article className="design-compare__pane">
              <h4>{versionLabel(result.version_a)}</h4>
              <p>{formatDesignDate(result.version_a.created_at, locale)}</p>
              <p>{result.version_a.design_parameters?.mode ?? tCommon('noValue')}</p>
            </article>
            <article className="design-compare__pane">
              <h4>{versionLabel(result.version_b)}</h4>
              <p>{formatDesignDate(result.version_b.created_at, locale)}</p>
              <p>{result.version_b.design_parameters?.mode ?? tCommon('noValue')}</p>
            </article>
          </div>

          <dl className="leads-detail__grid design-compare__diff">
            <div><dt>{t('diff.status')}</dt><dd>{getStatusLabel(result.design_status)}</dd></div>
            <div><dt>{t('diff.style')}</dt><dd>{result.diff.style_preset_a ?? '—'} → {result.diff.style_preset_b ?? '—'}{result.diff.style_preset_changed ? ' *' : ''}</dd></div>
            <div><dt>{t('diff.materials')}</dt><dd>{result.diff.material_package_a ?? '—'} → {result.diff.material_package_b ?? '—'}{result.diff.material_package_changed ? ' *' : ''}</dd></div>
            <div><dt>{t('diff.furnitureCount')}</dt><dd>{result.diff.furniture_count_a} → {result.diff.furniture_count_b}</dd></div>
            <div><dt>{t('diff.furnitureAdded')}</dt><dd>{result.diff.furniture_added.length ? result.diff.furniture_added.join(', ') : '—'}</dd></div>
            <div><dt>{t('diff.furnitureRemoved')}</dt><dd>{result.diff.furniture_removed.length ? result.diff.furniture_removed.join(', ') : '—'}</dd></div>
            <div><dt>{t('diff.furnitureMoved')}</dt><dd>{result.diff.furniture_moved.length ? result.diff.furniture_moved.join(', ') : '—'}</dd></div>
            <div><dt>{t('diff.colors')}</dt><dd>{result.diff.colors_changed ? (result.diff.color_diff_summary ?? t('diff.colorsChanged')) : t('diff.noChange')}</dd></div>
          </dl>
          <p className="design-compare__footnote">{result.comparison_note}</p>
        </div>
      )}
    </div>
  );
}
