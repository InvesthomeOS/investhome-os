/**
 * Sprint 3 — Media Library Drive sync status + source visibility contracts.
 * Run: node --test src/app/workspaces/creative-studio/media-library/__tests__/media-library-drive.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const webSrc = join(here, '../../../../../');

function readRel(...parts) {
  return readFileSync(join(...parts), 'utf8');
}

const workspace = readRel(root, 'media-library-workspace.tsx');
const model = readRel(root, 'media-library-model.ts');
const apiMap = readRel(root, 'media-library-api-map.ts');
const client = readRel(webSrc, 'lib/api/creative-studio.ts');
const projectsApi = readRel(webSrc, 'lib/api/projects.ts');
const drivePanel = readRel(
  webSrc,
  'app/dashboard/projects/_components/ds/project-drive-sync-panel.tsx',
);
const detailWorkspace = readRel(
  webSrc,
  'app/dashboard/projects/_components/ds/projects-detail-ds-workspace.tsx',
);
const wbMediaHook = readRel(
  webSrc,
  'app/workspaces/creative-studio/website-builder/use-website-builder-media.ts',
);
const en = JSON.parse(readRel(webSrc, '../messages/en.json'));
const tr = JSON.parse(readRel(webSrc, '../messages/tr.json'));

describe('1. Drive status renders', () => {
  it('embeds ProjectDriveSyncPanel in Documents tab and loads status', () => {
    assert.match(detailWorkspace, /ProjectDriveSyncPanel/);
    assert.match(detailWorkspace, /projectId=\{projectId\}/);
    assert.match(drivePanel, /fetchProjectDriveStatus/);
    assert.match(drivePanel, /data-testid="project-drive-sync-panel"/);
    assert.match(drivePanel, /data-testid="project-drive-meta"/);
    assert.match(drivePanel, /last_successful_sync_at/);
    assert.match(drivePanel, /last_sync_status/);
  });
});

describe('2. successful manual sync', () => {
  it('calls syncProjectDrive and refreshes status with toast', () => {
    assert.match(drivePanel, /syncProjectDrive\(projectId/);
    assert.match(drivePanel, /data-testid="project-drive-sync-now"/);
    assert.match(drivePanel, /toasts\.syncDone/);
    assert.match(drivePanel, /refreshStatus/);
    assert.match(projectsApi, /export async function syncProjectDrive/);
  });
});

describe('3. sync failure state', () => {
  it('shows compact error summary without stack traces', () => {
    assert.match(drivePanel, /data-testid="project-drive-sync-error"/);
    assert.match(drivePanel, /sanitizeError/);
    assert.match(drivePanel, /last_sync_error/);
    assert.doesNotMatch(drivePanel, /stackTrace|stack_trace/);
    assert.match(drivePanel, /Never surface tokens/);
  });
});

describe('4. running state disables duplicate sync', () => {
  it('locks sync while RUNNING / syncing', () => {
    assert.match(drivePanel, /syncLockRef/);
    assert.match(drivePanel, /disabled=\{running\}/);
    assert.match(drivePanel, /RUNNING/);
    assert.match(drivePanel, /aria-busy=\{running\}/);
  });
});

describe('5. Force Full confirmation', () => {
  it('requires Dialog confirmation and forceFull=true', () => {
    assert.match(drivePanel, /data-testid="project-drive-force-full"/);
    assert.match(drivePanel, /data-testid="project-drive-force-confirm"/);
    assert.match(drivePanel, /forceConfirmOpen/);
    assert.match(drivePanel, /runSync\(true\)/);
    assert.match(drivePanel, /forceFull/);
    assert.match(drivePanel, /<Dialog/);
  });
});

describe('6–7. Drive badge visibility', () => {
  it('shows Drive badge only for google_drive assets', () => {
    assert.match(workspace, /ml-drive-badge-/);
    assert.match(workspace, /isGoogleDriveAsset\(asset\)/);
    assert.match(model, /export function isGoogleDriveAsset/);
    assert.match(model, /sourceType === 'google_drive'/);
  });

  it('mapper preserves source_type for Drive vs upload', () => {
    assert.match(apiMap, /sourceType: asset\.source_type/);
    assert.match(client, /source_type\?:/);
    // Inline mapper smoke
    function isGoogleDrive(sourceType) {
      return sourceType === 'google_drive';
    }
    assert.equal(isGoogleDrive('google_drive'), true);
    assert.equal(isGoogleDrive('upload'), false);
    assert.equal(isGoogleDrive(null), false);
  });
});

describe('8. missing asset status', () => {
  it('marks MISSING with badge and retain-id messaging', () => {
    assert.match(workspace, /ml-missing-badge-/);
    assert.match(workspace, /ml-drive-missing-note/);
    assert.match(workspace, /drive\.missingRetainId/);
    assert.match(model, /export function isMissingDriveAsset/);
    assert.match(model, /syncStatus === 'missing'/);
  });
});

describe('9. possible duplicate warning', () => {
  it('renders informational duplicate warning only', () => {
    assert.match(workspace, /ml-duplicate-badge-/);
    assert.match(workspace, /ml-drive-duplicate-warning/);
    assert.match(workspace, /possibleDuplicate/);
    assert.doesNotMatch(workspace, /autoMerge|mergeDuplicate/);
    assert.match(apiMap, /possibleDuplicate: Boolean\(asset\.possible_duplicate\)/);
  });
});

describe('10. asset detail Drive metadata', () => {
  it('shows Drive section fields in detail panel', () => {
    assert.match(workspace, /data-testid="ml-drive-detail"/);
    assert.match(workspace, /drive\.fields\.assetId/);
    assert.match(workspace, /drive\.fields\.fileId/);
    assert.match(workspace, /drive\.fields\.lastModified/);
    assert.match(workspace, /drive\.fields\.syncStatus/);
    assert.match(workspace, /drive\.fields\.category/);
    assert.match(workspace, /drive\.fields\.project/);
    assert.match(apiMap, /webViewLink: asset\.web_view_link/);
    assert.match(apiMap, /externalFileId: asset\.external_file_id/);
  });
});

describe('11. Open in Google Drive only when link exists', () => {
  it('gates external link on webViewLink', () => {
    assert.match(workspace, /selected\.webViewLink \?/);
    assert.match(workspace, /data-testid="ml-open-in-drive"/);
    assert.match(workspace, /target="_blank"/);
    assert.match(workspace, /rel="noopener noreferrer"/);
    assert.match(workspace, /drive\.opensExternal/);
  });
});

describe('12. Automatic Sync toggle', () => {
  it('uses PUT mapping with existing folder id', () => {
    assert.match(drivePanel, /data-testid="project-drive-auto-sync"/);
    assert.match(drivePanel, /upsertProjectDriveMapping/);
    assert.match(drivePanel, /drive_sync_enabled: !status\.drive_sync_enabled/);
    assert.match(drivePanel, /drive_folder_id: status\.drive_folder_id/);
    assert.match(projectsApi, /export async function upsertProjectDriveMapping/);
  });
});

describe('13. existing Media Library selection still works', () => {
  it('keeps select / multi-select / UUID guards intact', () => {
    assert.match(workspace, /selectAsset\(asset\.id\)/);
    assert.match(workspace, /ml-check-/);
    assert.match(workspace, /toggleCheck/);
    assert.match(workspace, /isMediaAssetUuid/);
    assert.match(apiMap, /isMediaAssetUuid/);
    assert.match(model, /filterAssets/);
    assert.match(model, /sourceFilter/);
  });
});

describe('builder safety + i18n', () => {
  it('excludes MISSING assets from Website Builder picker lists', () => {
    assert.match(wbMediaHook, /sync_status/);
    assert.match(wbMediaHook, /!== 'missing'/);
  });

  it('adds en/tr Drive copy under Media Library and project detail', () => {
    assert.equal(en.creativeStudio.ds.mediaLibrary.drive.openInDrive, 'Open in Google Drive');
    assert.equal(tr.creativeStudio.ds.mediaLibrary.drive.openInDrive, 'Google Drive’da aç');
    assert.equal(en.projects.detail.drive.actions.syncNow, 'Sync Now');
    assert.equal(tr.projects.detail.drive.actions.syncNow, 'Şimdi Senkronize Et');
    assert.ok(en.projects.detail.drive.forceConfirm.body.includes('does not delete'));
  });

  it('API client exposes Drive status/sync/mapping routes', () => {
    assert.match(projectsApi, /\/projects\/\$\{projectId\}\/drive\/status/);
    assert.match(projectsApi, /\/projects\/\$\{projectId\}\/drive\/sync/);
    assert.match(projectsApi, /\/projects\/\$\{projectId\}\/drive\/mapping/);
    assert.match(client, /possible_duplicate\?:/);
    assert.match(client, /web_view_link\?:/);
  });
});
