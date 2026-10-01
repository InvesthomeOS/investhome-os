'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, SegmentedControl, TextArea } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { CsPageHeader } from '../_components/cs-page-header';
import { CsZoomControls } from '../_components/cs-zoom-controls';
import { QUICK_CREATIVE_ROUTE } from '../_components/ds/creative-studio-ds-model';
import {
  approveQuickCreative,
  fetchCreativeStudioMediaBlob,
  generateQuickCreative,
  getQuickCreativeDownloadUrl,
  getQuickCreativeProject,
  listQuickCreativeProjects,
  replaceQuickCreativeImage,
  reviseQuickCreative,
  varyQuickCreative,
  type QuickCreativeFormatId,
  type QuickCreativePhoto,
  type QuickCreativeProject,
  type QuickCreativeProjectDetail,
  type QuickCreativeResult,
} from '@/lib/api/creative-studio';
import { ApiError } from '@/lib/api/client';

import '../_components/ds/creative-studio-ds.css';
import './hizli-tasarim.css';

const FORMAT_ORDER: QuickCreativeFormatId[] = ['4:5', '9:16', '1:1', '16:9'];
const EXAMPLE_KEYS = ['launch', 'invest', 'dc', 'interior'] as const;

function aspectClass(fmt: QuickCreativeFormatId): string {
  if (fmt === '4:5') return 'is-45';
  if (fmt === '9:16') return 'is-916';
  if (fmt === '1:1') return 'is-11';
  return 'is-169';
}

export function QuickCreativeWorkspace() {
  const t = useTranslations('creativeStudio.ds');
  const [projects, setProjects] = useState<QuickCreativeProject[]>([]);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [detail, setDetail] = useState<QuickCreativeProjectDetail | null>(null);
  const [format, setFormat] = useState<QuickCreativeFormatId>('4:5');
  const [prompt, setPrompt] = useState('');
  const [revision, setRevision] = useState('');
  const [creative, setCreative] = useState<QuickCreativeResult | null>(null);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageTone, setMessageTone] = useState<'ok' | 'err'>('ok');
  const [zoom, setZoom] = useState(100);
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [pickerOpen, setPickerOpen] = useState(false);

  const selectedProject = useMemo(
    () => projects.find((item) => item.id === projectId) ?? detail?.project ?? null,
    [detail, projectId, projects],
  );

  const previewAssetId = creative?.preview_asset_id ?? null;
  const photos: QuickCreativePhoto[] = creative?.photos ?? detail?.photos ?? [];

  useEffect(() => {
    let cancelled = false;
    void listQuickCreativeProjects()
      .then((payload) => {
        if (cancelled) return;
        setProjects(payload.items);
        const temple = payload.items.find((item) => item.live) ?? payload.items[0];
        if (temple) setProjectId(temple.id);
      })
      .catch(() => {
        if (!cancelled) setMessage(t('quick.loadError'));
      });
    return () => {
      cancelled = true;
    };
  }, [t]);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    void getQuickCreativeProject(projectId)
      .then((next) => {
        if (cancelled) return;
        setDetail(next);
        setCreative(null);
        setRevision('');
        setZoom(100);
      })
      .catch(() => {
        if (!cancelled) setMessage(t('quick.loadError'));
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, t]);

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

  useEffect(() => {
    if (!pickerOpen) return;
    const missing = photos.filter((photo) => !urls[photo.id]);
    if (missing.length === 0) return;
    let cancelled = false;
    void Promise.all(
      missing.map(async (photo) => {
        const blob = await fetchCreativeStudioMediaBlob(photo.id);
        return { id: photo.id, url: URL.createObjectURL(blob) };
      }),
    ).then((loaded) => {
      if (cancelled) return;
      setUrls((prev) => {
        const next = { ...prev };
        for (const item of loaded) next[item.id] = item.url;
        return next;
      });
    });
    return () => {
      cancelled = true;
    };
  }, [pickerOpen, photos, urls]);

  const applyCreative = useCallback((next: QuickCreativeResult) => {
    setCreative(next);
    if (next.format === '4:5' || next.format === '9:16' || next.format === '1:1' || next.format === '16:9') {
      setFormat(next.format);
    }
    setMessage(null);
  }, []);

  async function run(action: () => Promise<QuickCreativeResult>, pending: string) {
    if (working) return;
    setWorking(true);
    setMessage(pending);
    setMessageTone('ok');
    try {
      applyCreative(await action());
    } catch (error) {
      const text = error instanceof ApiError ? error.message : t('quick.loadError');
      setMessage(text);
      setMessageTone('err');
    } finally {
      setWorking(false);
    }
  }

  function onGenerate() {
    if (!projectId || !prompt.trim()) return;
    void run(
      () =>
        generateQuickCreative({
          project_id: projectId,
          request: prompt.trim(),
          format,
        }),
      t('quick.generating'),
    );
  }

  function onRevise() {
    if (!creative?.campaign_id || !revision.trim()) return;
    void run(
      () => reviseQuickCreative(creative.campaign_id, revision.trim()),
      t('quick.working'),
    );
  }

  function onDownload() {
    if (!creative?.campaign_id) return;
    void (async () => {
      const response = await fetch(getQuickCreativeDownloadUrl(creative.campaign_id), {
        credentials: 'include',
        cache: 'no-store',
      });
      if (!response.ok) return;
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${creative.project_name || 'tasarim'}-${format.replace(':', 'x')}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1500);
    })();
  }

  const ready = Boolean(detail?.ready);
  const formatOptions = FORMAT_ORDER.map((fmt) => ({
    value: fmt,
    label: t(`quick.formats.${fmt}`),
  }));

  return (
    <main className="dashboard qc-page qc-page--workspace" data-testid="quick-creative-workspace">
      <CsPageHeader
        title={t('quick.title')}
        subtitle={selectedProject ? selectedProject.name : t('quick.subtitle')}
        titleIcon="sparkles"
        breadcrumbs={[
          { href: '/workspaces/creative-studio', label: t('quick.studio') },
          { href: QUICK_CREATIVE_ROUTE, label: t('quick.title'), current: true },
        ]}
        breadcrumbAria={t('quick.title')}
        className="qc-campaign-header"
        testId="quick-creative-header"
      />

      <div className="qc-workspace">
        <section className="qc-preview" aria-label={t(`quick.formats.${format}`)}>
          <div className="qc-preview__toolbar">
            <CsZoomControls
              className="qc-zoom"
              percent={zoom}
              onZoomOut={() => setZoom((value) => Math.max(50, value - 25))}
              onZoomIn={() => setZoom((value) => Math.min(200, value + 25))}
              onReset={() => setZoom(100)}
              disabledOut={zoom <= 50}
              disabledIn={zoom >= 200}
              ariaLabel={t('quick.zoomAria')}
              zoomOutLabel={t('quick.zoomOut')}
              zoomInLabel={t('quick.zoomIn')}
              resetTitle={t('quick.fit')}
              testIdPrefix="qc"
            />
            {creative ? (
              <div className="qc-actions">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={working}
                  onClick={() => void run(() => approveQuickCreative(creative.campaign_id), t('quick.working'))}
                  data-testid="qc-approve"
                >
                  {t('quick.approve')}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={working}
                  onClick={() => void run(() => varyQuickCreative(creative.campaign_id), t('quick.generating'))}
                  data-testid="qc-vary"
                >
                  {t('quick.vary')}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={working || photos.length === 0}
                  onClick={() => setPickerOpen(true)}
                  data-testid="qc-replace-image"
                >
                  {t('quick.replaceImage')}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={working || !previewAssetId}
                  onClick={() => void onDownload()}
                  data-testid="qc-download"
                >
                  <IhIcon name="inbox" size={12} />
                  {t('quick.download')}
                </Button>
              </div>
            ) : null}
          </div>
          <div className="qc-preview__stage">
            <div
              className={`qc-preview__frame ${aspectClass(format)}`}
              style={{ transform: `scale(${zoom / 100})` }}
            >
              {previewAssetId && urls[previewAssetId] ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={urls[previewAssetId]} alt="" />
              ) : (
                <span className="qc-preview__empty">{t('quick.emptyPreview')}</span>
              )}
            </div>
          </div>
        </section>

        <aside className="qc-rail" data-testid="qc-controls">
          <div className="qc-projects" role="listbox" aria-label={t('quick.projectsAria')} data-testid="qc-project-selector">
            {projects.map((item) => (
              <button
                key={item.id}
                type="button"
                role="option"
                aria-selected={item.id === projectId}
                className={`qc-project${item.id === projectId ? ' is-active' : ''}`}
                onClick={() => setProjectId(item.id)}
                data-testid={item.live ? 'qc-project-temple' : undefined}
              >
                <strong>{item.name}</strong>
                <span>
                  {[item.city, item.state].filter(Boolean).join(', ') || item.code}
                </span>
              </button>
            ))}
          </div>

          <p className={`qc-assets${ready ? ' is-ready' : ''}`} data-testid="qc-assets">
            {ready
              ? t('quick.assetsReady', { count: detail?.photo_count ?? photos.length })
              : t('quick.assetsMissing')}
          </p>

          <SegmentedControl
            className="qc-format-seg"
            ariaLabel={t('quick.formatsAria')}
            value={format}
            onChange={(next) => {
              setFormat(next as QuickCreativeFormatId);
              setZoom(100);
            }}
            options={formatOptions}
          />

          {!creative ? (
            <>
              <TextArea
                id="qc-prompt"
                label={t('quick.promptLabel')}
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder={t('quick.promptPlaceholder')}
                rows={5}
                data-testid="qc-prompt"
              />
              <div className="qc-examples" aria-label={t('quick.examplesAria')}>
                {EXAMPLE_KEYS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className="qc-example"
                    onClick={() => setPrompt(t(`quick.examples.${key}`))}
                  >
                    {t(`quick.examples.${key}`)}
                  </button>
                ))}
              </div>
              <Button
                variant="primary"
                size="sm"
                disabled={!prompt.trim() || !ready || working || !projectId}
                onClick={() => onGenerate()}
                data-testid="qc-generate"
              >
                {working ? t('quick.generating') : t('quick.generate')}
              </Button>
            </>
          ) : (
            <>
              <p className="qc-meta" data-testid="qc-creative-meta">
                {creative.project_name} · {t(`quick.formats.${format}`)}
                {creative.selected_photo_label ? ` · ${creative.selected_photo_label}` : ''}
              </p>
              <TextArea
                id="qc-revision"
                label={t('quick.reviseLabel')}
                value={revision}
                onChange={(event) => setRevision(event.target.value)}
                placeholder={t('quick.revisePlaceholder')}
                rows={4}
                data-testid="qc-revision"
              />
              <Button
                variant="primary"
                size="sm"
                disabled={!revision.trim() || working}
                onClick={() => onRevise()}
                data-testid="qc-apply"
              >
                {working ? t('quick.working') : t('quick.apply')}
              </Button>
            </>
          )}

          {message ? (
            <p className={`qc-message is-${messageTone}`} data-testid="qc-result">
              {message}
            </p>
          ) : null}
        </aside>
      </div>

      {pickerOpen ? (
        <div className="qc-picker" role="dialog" aria-label={t('quick.pickerTitle')} data-testid="qc-photo-picker">
          <div className="qc-picker__panel">
            <div className="qc-picker__head">
              <strong>{t('quick.pickerTitle')}</strong>
              <Button variant="secondary" size="sm" onClick={() => setPickerOpen(false)}>
                {t('quick.pickerClose')}
              </Button>
            </div>
            <div className="qc-picker__grid">
              {photos.map((photo) => (
                <button
                  key={photo.id}
                  type="button"
                  className="qc-picker__item"
                  disabled={working}
                  onClick={() => {
                    if (!creative) return;
                    setPickerOpen(false);
                    void run(
                      () => replaceQuickCreativeImage(creative.campaign_id, photo.id),
                      t('quick.working'),
                    );
                  }}
                >
                  {urls[photo.id] ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={urls[photo.id]} alt="" />
                  ) : (
                    <span className="qc-picker__ph" />
                  )}
                  <span>{photo.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
