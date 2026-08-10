'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Dialog, Input, StatusChip } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import {
  fetchProjectDriveStatus,
  syncProjectDrive,
  upsertProjectDriveMapping,
  type DriveSyncStatusValue,
  type ProjectDriveStatus,
} from '@/lib/api/projects';

function syncTone(status: DriveSyncStatusValue) {
  switch (String(status || '').toUpperCase()) {
    case 'SUCCESS':
      return 'success' as const;
    case 'RUNNING':
      return 'info' as const;
    case 'FAILED':
      return 'danger' as const;
    default:
      return 'default' as const;
  }
}

function formatWhen(iso: string | null | undefined, empty: string): string {
  if (!iso) return empty;
  const ms = Date.parse(iso);
  if (!Number.isFinite(ms)) return empty;
  return new Date(ms).toLocaleString();
}

function syncTypeLabel(
  status: ProjectDriveStatus | null,
  t: (key: string) => string,
): string {
  if (!status?.mapped) return t('syncType.none');
  if (status.force_full_sync) return t('syncType.fullPending');
  if (status.has_change_token) return t('syncType.incremental');
  return t('syncType.full');
}

function sanitizeError(message: string | null | undefined, fallback: string): string {
  if (!message) return fallback;
  const trimmed = message.trim();
  if (!trimmed) return fallback;
  // Never surface tokens / credentials if a provider error leaks them.
  if (/token|refresh_token|client_secret|bearer\s+[a-z0-9._-]+/i.test(trimmed)) {
    return fallback;
  }
  return trimmed.length > 280 ? `${trimmed.slice(0, 277)}…` : trimmed;
}

function statusLabelFor(
  status: DriveSyncStatusValue | undefined,
  t: (key: string) => string,
): string {
  const key = String(status || 'IDLE').toUpperCase();
  if (key === 'SUCCESS') return t('status.SUCCESS');
  if (key === 'RUNNING') return t('status.RUNNING');
  if (key === 'FAILED') return t('status.FAILED');
  if (key === 'IDLE') return t('status.IDLE');
  return key;
}

interface ProjectDriveSyncPanelProps {
  projectId: string;
}

export function ProjectDriveSyncPanel({ projectId }: ProjectDriveSyncPanelProps) {
  const t = useTranslations('projects.detail.drive');
  const { user } = useAuth();
  const canSync = hasPermission(user, 'creative_studio', 'sync_drive');

  const [status, setStatus] = useState<ProjectDriveStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [mapping, setMapping] = useState(false);
  const [folderIdDraft, setFolderIdDraft] = useState('');
  const [mapError, setMapError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [forceConfirmOpen, setForceConfirmOpen] = useState(false);
  const syncLockRef = useRef(false);
  const toastTimerRef = useRef<number | null>(null);

  const showToast = useCallback((message: string) => {
    setToast(message);
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current);
    toastTimerRef.current = window.setTimeout(() => setToast(null), 2800);
  }, []);

  const refreshStatus = useCallback(async () => {
    setLoadError(null);
    try {
      const next = await fetchProjectDriveStatus(projectId);
      setStatus(next);
    } catch (err) {
      const message = err instanceof Error ? err.message : t('loadError');
      setLoadError(sanitizeError(message, t('loadError')));
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    setLoading(true);
    void refreshStatus();
    return () => {
      if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current);
    };
  }, [refreshStatus]);

  const runSync = useCallback(
    async (forceFull: boolean) => {
      if (!canSync || syncLockRef.current) return;
      syncLockRef.current = true;
      setSyncing(true);
      try {
        const result = await syncProjectDrive(projectId, { forceFull });
        showToast(
          t('toasts.syncDone', {
            created: result.created,
            updated: result.updated,
            missing: result.missing,
          }),
        );
        await refreshStatus();
      } catch (err) {
        const message = err instanceof Error ? err.message : t('toasts.syncFailed');
        showToast(sanitizeError(message, t('toasts.syncFailed')));
        await refreshStatus();
      } finally {
        syncLockRef.current = false;
        setSyncing(false);
      }
    },
    [canSync, projectId, refreshStatus, showToast, t],
  );

  const onToggleAutoSync = useCallback(async () => {
    if (!canSync || !status?.mapped || !status.drive_folder_id || toggling) return;
    setToggling(true);
    try {
      await upsertProjectDriveMapping(projectId, {
        drive_folder_id: status.drive_folder_id,
        drive_sync_enabled: !status.drive_sync_enabled,
      });
      showToast(
        !status.drive_sync_enabled ? t('toasts.autoOn') : t('toasts.autoOff'),
      );
      await refreshStatus();
    } catch (err) {
      const message = err instanceof Error ? err.message : t('toasts.toggleFailed');
      showToast(sanitizeError(message, t('toasts.toggleFailed')));
    } finally {
      setToggling(false);
    }
  }, [canSync, projectId, refreshStatus, showToast, status, t, toggling]);

  const onSaveMapping = useCallback(async () => {
    const folderId = folderIdDraft.trim();
    if (!canSync || !folderId || mapping) return;
    setMapping(true);
    setMapError(null);
    try {
      await upsertProjectDriveMapping(projectId, {
        drive_folder_id: folderId,
        drive_sync_enabled: true,
      });
      setFolderIdDraft('');
      showToast(t('toasts.mapped'));
      await refreshStatus();
    } catch (err) {
      const message = err instanceof Error ? err.message : t('toasts.mapFailed');
      setMapError(sanitizeError(message, t('toasts.mapFailed')));
    } finally {
      setMapping(false);
    }
  }, [canSync, folderIdDraft, mapping, projectId, refreshStatus, showToast, t]);

  const running =
    syncing || String(status?.last_sync_status || '').toUpperCase() === 'RUNNING';
  const failed = String(status?.last_sync_status || '').toUpperCase() === 'FAILED';
  const statusLabel = statusLabelFor(status?.last_sync_status, t);

  return (
    <article
      className="proj-detail-ds__panel proj-detail-ds__drive"
      data-testid="project-drive-sync-panel"
      aria-label={t('title')}
    >
      <div className="proj-detail-ds__drive-head">
        <div>
          <h3 className="proj-detail-ds__panel-title">{t('title')}</h3>
          <p className="proj-detail-ds__panel-sub">{t('subtitle')}</p>
        </div>
        {status ? (
          <span data-testid="project-drive-status-chip">
            <StatusChip tone={syncTone(status.last_sync_status)}>{statusLabel}</StatusChip>
          </span>
        ) : null}
      </div>

      {loading ? (
        <p className="proj-detail-ds__drive-empty" data-testid="project-drive-loading">
          {t('loading')}
        </p>
      ) : loadError ? (
        <div className="proj-detail-ds__drive-error" data-testid="project-drive-load-error">
          <p>{loadError}</p>
          <Button variant="secondary" size="sm" onClick={() => void refreshStatus()}>
            {t('actions.retry')}
          </Button>
        </div>
      ) : !status?.mapped ? (
        <div className="proj-detail-ds__drive-unmapped" data-testid="project-drive-unmapped">
          <p className="proj-detail-ds__drive-empty">{t('unmapped')}</p>
          {canSync ? (
            <div className="proj-detail-ds__drive-map" data-testid="project-drive-map-form">
              <Input
                id="project-drive-folder-id"
                label={t('fields.folderId')}
                hint={t('fields.folderIdHint')}
                value={folderIdDraft}
                disabled={mapping}
                autoComplete="off"
                spellCheck={false}
                placeholder={t('fields.folderIdPlaceholder')}
                onChange={(e) => {
                  setFolderIdDraft(e.target.value);
                  if (mapError) setMapError(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    void onSaveMapping();
                  }
                }}
                error={mapError ?? undefined}
                data-testid="project-drive-folder-id"
              />
              <div className="proj-detail-ds__drive-actions">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={mapping || !folderIdDraft.trim()}
                  aria-busy={mapping}
                  onClick={() => void onSaveMapping()}
                  data-testid="project-drive-map-save"
                >
                  {mapping ? t('actions.mapping') : t('actions.mapFolder')}
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <>
          <dl className="proj-detail-ds__drive-meta" data-testid="project-drive-meta">
            <div>
              <dt>{t('fields.mapping')}</dt>
              <dd>{t('mapped')}</dd>
            </div>
            <div>
              <dt>{t('fields.folderId')}</dt>
              <dd className="proj-detail-ds__drive-mono">{status.drive_folder_id || '—'}</dd>
            </div>
            <div>
              <dt>{t('fields.syncEnabled')}</dt>
              <dd>{status.drive_sync_enabled ? t('yes') : t('no')}</dd>
            </div>
            <div>
              <dt>{t('fields.lastSync')}</dt>
              <dd>{formatWhen(status.last_drive_sync_at, t('never'))}</dd>
            </div>
            <div>
              <dt>{t('fields.lastSuccessful')}</dt>
              <dd>{formatWhen(status.last_successful_sync_at, t('never'))}</dd>
            </div>
            <div>
              <dt>{t('fields.currentStatus')}</dt>
              <dd>
                <StatusChip tone={syncTone(status.last_sync_status)}>{statusLabel}</StatusChip>
              </dd>
            </div>
            <div>
              <dt>{t('fields.syncType')}</dt>
              <dd>{syncTypeLabel(status, t)}</dd>
            </div>
          </dl>

          {failed ? (
            <div className="proj-detail-ds__drive-error" data-testid="project-drive-sync-error">
              <p>
                <strong>{t('error.title')}</strong>{' '}
                {sanitizeError(status.last_sync_error, t('error.fallback'))}
              </p>
              <p className="proj-detail-ds__panel-sub">
                {t('error.at', { time: formatWhen(status.last_drive_sync_at, t('never')) })}
              </p>
            </div>
          ) : null}

          <div className="proj-detail-ds__drive-actions">
            {canSync && status.drive_folder_id ? (
              <label className="proj-detail-ds__drive-toggle">
                <input
                  type="checkbox"
                  checked={Boolean(status.drive_sync_enabled)}
                  disabled={toggling || running}
                  onChange={() => void onToggleAutoSync()}
                  data-testid="project-drive-auto-sync"
                  aria-label={t('fields.automaticSync')}
                />
                <span>{t('fields.automaticSync')}</span>
              </label>
            ) : null}

            {canSync ? (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={running}
                  aria-busy={running}
                  onClick={() => void runSync(false)}
                  data-testid="project-drive-sync-now"
                >
                  {running ? t('actions.syncing') : t('actions.syncNow')}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={running}
                  onClick={() => setForceConfirmOpen(true)}
                  data-testid="project-drive-force-full"
                >
                  {t('actions.forceFull')}
                </Button>
              </>
            ) : null}
          </div>
        </>
      )}

      {toast ? (
        <div className="proj-detail-ds__drive-toast" role="status" data-testid="project-drive-toast">
          {toast}
        </div>
      ) : null}

      <Dialog
        open={forceConfirmOpen}
        onClose={() => setForceConfirmOpen(false)}
        title={t('forceConfirm.title')}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setForceConfirmOpen(false)}>
              {t('forceConfirm.cancel')}
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={running}
              data-testid="project-drive-force-confirm"
              onClick={() => {
                setForceConfirmOpen(false);
                void runSync(true);
              }}
            >
              {t('forceConfirm.confirm')}
            </Button>
          </>
        }
      >
        <p>{t('forceConfirm.body')}</p>
      </Dialog>
    </article>
  );
}
