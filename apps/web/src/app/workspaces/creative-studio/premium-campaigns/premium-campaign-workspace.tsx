'use client';

/** Phase 13.0 FINAL — HUMAN_APPROVED production UI. Do not redesign. */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, SegmentedControl, TextArea } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { CsPageHeader } from '../_components/cs-page-header';
import { CsZoomControls } from '../_components/cs-zoom-controls';
import { PREMIUM_CAMPAIGNS_ROUTE } from '../_components/ds/creative-studio-ds-model';
import {
  approvePremiumCampaign,
  fetchCreativeStudioMediaBlob,
  getPremiumCampaign,
  getPremiumCampaignDownloadUrl,
  revertPremiumCampaign,
  revisePremiumCampaign,
  type PremiumCampaignDetail,
  type PremiumCampaignFormatId,
} from '@/lib/api/creative-studio';
import { ApiError } from '@/lib/api/client';

import '../_components/ds/creative-studio-ds.css';
import './premium-campaigns.css';

const FORMAT_ORDER: PremiumCampaignFormatId[] = ['4:5', '9:16', '1:1'];
const EXAMPLE_KEYS = ['price', 'copy', 'visual', 'family'] as const;

function aspectClass(fmt: PremiumCampaignFormatId): string {
  if (fmt === '4:5') return 'is-45';
  if (fmt === '9:16') return 'is-916';
  return 'is-11';
}

export function PremiumCampaignWorkspace({ familyId }: { familyId: string }) {
  const t = useTranslations('creativeStudio.ds');
  const [campaign, setCampaign] = useState<PremiumCampaignDetail | null>(null);
  const [format, setFormat] = useState<PremiumCampaignFormatId>('9:16');
  const [instruction, setInstruction] = useState('');
  const [scope, setScope] = useState<'selected' | 'campaign'>('selected');
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageTone, setMessageTone] = useState<'ok' | 'err'>('ok');
  const [compare, setCompare] = useState<'after' | 'before'>('after');
  const [zoom, setZoom] = useState(100);
  const [urls, setUrls] = useState<Record<string, string>>({});

  const selected = useMemo(() => {
    if (!campaign) return null;
    return campaign.formats.find((item) => item.format === format) ?? campaign.selected;
  }, [campaign, format]);

  const previewAssetId = useMemo(() => {
    if (!selected) return null;
    if (compare === 'before' && selected.compare) return selected.compare.before_asset_id;
    if (compare === 'after' && selected.compare) return selected.compare.after_asset_id;
    return selected.preview_asset_id;
  }, [compare, selected]);

  useEffect(() => {
    let cancelled = false;
    void getPremiumCampaign(familyId, '9:16')
      .then((detail) => {
        if (cancelled) return;
        setCampaign(detail);
        setFormat(detail.selected_format);
      })
      .catch(() => {
        if (!cancelled) setMessage(t('premium.loadError'));
      });
    return () => {
      cancelled = true;
    };
  }, [familyId, t]);

  useEffect(() => {
    if (!previewAssetId || urls[previewAssetId]) return;
    let cancelled = false;
    void fetchCreativeStudioMediaBlob(previewAssetId).then((blob) => {
      if (cancelled) return;
      const url = URL.createObjectURL(blob);
      setUrls((prev) => ({ ...prev, [previewAssetId]: url }));
    });
    return () => {
      cancelled = true;
    };
  }, [previewAssetId, urls]);

  const applyResult = useCallback((detail: PremiumCampaignDetail) => {
    setCampaign(detail);
    if (detail.selected_format) setFormat(detail.selected_format);
    const result = detail.result;
    if (result?.message) {
      setMessage(result.message);
      setMessageTone(result.ok ? 'ok' : 'err');
    } else if (result && !result.ok) {
      setMessage(t('premium.loadError'));
      setMessageTone('err');
    } else {
      setMessage(null);
    }
    if (result?.ok && result.code === 'REVISED') setCompare('after');
  }, [t]);

  async function onSubmit() {
    if (!instruction.trim() || working) return;
    setWorking(true);
    setMessage(t('premium.working'));
    setMessageTone('ok');
    try {
      const detail = await revisePremiumCampaign(familyId, {
        instruction: instruction.trim(),
        format,
        scope,
      });
      applyResult(detail);
    } catch (error) {
      const text = error instanceof ApiError ? error.message : t('premium.loadError');
      setMessage(text);
      setMessageTone('err');
    } finally {
      setWorking(false);
    }
  }

  async function onApprove() {
    const detail = await approvePremiumCampaign(familyId, format);
    applyResult(detail);
  }

  async function onRevert() {
    const detail = await revertPremiumCampaign(familyId, format);
    applyResult(detail);
    setCompare('after');
  }

  async function onDownload() {
    const response = await fetch(getPremiumCampaignDownloadUrl(familyId, format), {
      credentials: 'include',
      cache: 'no-store',
    });
    if (!response.ok) return;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${campaign?.title || 'kampanya'}-${format.replace(':', 'x')}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  const formatOptions = FORMAT_ORDER.filter((fmt) =>
    (campaign?.available_formats ?? []).includes(fmt),
  ).map((fmt) => ({ value: fmt, label: t(`premium.formats.${fmt}`) }));

  return (
    <main className="dashboard pc-page pc-page--workspace" data-testid="premium-campaign-workspace">
      <CsPageHeader
        title={campaign?.title || t('premium.listTitle')}
        subtitle={campaign?.subtitle || campaign?.project}
        titleIcon="target"
        breadcrumbs={[
          { href: '/workspaces/creative-studio', label: t('premium.studio') },
          { href: PREMIUM_CAMPAIGNS_ROUTE, label: t('premium.campaigns') },
          { label: campaign?.title || t('premium.listTitle'), current: true },
        ]}
        breadcrumbAria={t('premium.campaigns')}
        className="pc-campaign-header"
        testId="premium-campaign-header"
      />

      <div className="pc-workspace">
        <section className="pc-preview" aria-label={t(`premium.formats.${format}`)}>
          <div className="pc-preview__toolbar">
            <CsZoomControls
              className="pc-zoom"
              percent={zoom}
              onZoomOut={() => setZoom((value) => Math.max(50, value - 25))}
              onZoomIn={() => setZoom((value) => Math.min(200, value + 25))}
              onReset={() => setZoom(100)}
              disabledOut={zoom <= 50}
              disabledIn={zoom >= 200}
              ariaLabel={t('premium.zoomAria')}
              zoomOutLabel={t('premium.zoomOut')}
              zoomInLabel={t('premium.zoomIn')}
              resetTitle={t('premium.fit')}
              testIdPrefix="pc"
            />
            {selected?.compare ? (
              <SegmentedControl
                ariaLabel={t('premium.compareAria')}
                value={compare}
                onChange={(next) => setCompare(next as 'before' | 'after')}
                options={[
                  { value: 'before', label: t('premium.before') },
                  { value: 'after', label: t('premium.after') },
                ]}
              />
            ) : null}
            <div className="pc-actions">
              <Button
                variant={selected?.can_approve ? 'primary' : 'secondary'}
                size="sm"
                disabled={!selected?.can_approve || working}
                onClick={() => void onApprove()}
                data-testid="pc-approve"
              >
                {t('premium.approve')}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={!selected?.can_revert || working}
                onClick={() => void onRevert()}
                data-testid="pc-revert"
              >
                {t('premium.revert')}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={!selected?.preview_asset_id || working}
                onClick={() => void onDownload()}
                data-testid="pc-download"
              >
                <IhIcon name="inbox" size={12} />
                {t('premium.download')}
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled
                title={campaign?.publishing.message}
                data-testid="pc-publish"
              >
                {t('premium.publish')}
              </Button>
            </div>
          </div>
          <div className="pc-preview__stage">
            <div
              className={`pc-preview__frame ${aspectClass(format)}`}
              style={{ transform: `scale(${zoom / 100})` }}
            >
              {previewAssetId && urls[previewAssetId] ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={urls[previewAssetId]} alt="" />
              ) : (
                <span className="pc-card__ph" />
              )}
            </div>
          </div>
        </section>

        <aside className="pc-rail" data-testid="pc-revision-controls">
          {formatOptions.length > 0 ? (
            <SegmentedControl
              className="pc-format-seg"
              ariaLabel={t('premium.formatSelectorAria')}
              value={format}
              onChange={(next) => {
                setFormat(next as PremiumCampaignFormatId);
                setCompare('after');
                setZoom(100);
              }}
              options={formatOptions}
            />
          ) : null}

          <TextArea
            id="pc-instruction"
            label={t('premium.instructionLabel')}
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            placeholder={t('premium.instructionPlaceholder')}
            rows={5}
            data-testid="pc-instruction"
          />

          <SegmentedControl
            ariaLabel={t('premium.scopeAria')}
            value={scope}
            onChange={(next) => setScope(next as 'selected' | 'campaign')}
            options={[
              { value: 'selected', label: t('premium.scopeSelected') },
              { value: 'campaign', label: t('premium.scopeCampaign') },
            ]}
          />

          <Button
            variant="primary"
            size="sm"
            disabled={!instruction.trim() || working}
            onClick={() => void onSubmit()}
            data-testid="pc-apply"
          >
            {working ? t('premium.working') : t('premium.apply')}
          </Button>

          {message ? (
            <p className={`pc-message is-${messageTone}`} data-testid="pc-result">
              {message}
            </p>
          ) : null}

          <div className="pc-examples" aria-label={t('premium.examplesAria')}>
            {EXAMPLE_KEYS.map((key) => (
              <button
                key={key}
                type="button"
                className="pc-example"
                title={t(`premium.examples.${key}`)}
                onClick={() => setInstruction(t(`premium.examples.${key}`))}
              >
                {t(`premium.exampleChips.${key}`)}
              </button>
            ))}
          </div>
        </aside>
      </div>
    </main>
  );
}
