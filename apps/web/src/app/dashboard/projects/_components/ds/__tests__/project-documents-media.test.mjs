/**
 * Phase B/C2 — Project Documents tab loads project-scoped media and Drive folders.
 * Run: node --test src/app/dashboard/projects/_components/ds/__tests__/project-documents-media.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../../../../../../');

function readRel(...parts) {
  return readFileSync(join(...parts), 'utf8');
}

const detailWorkspace = readRel(
  webSrc,
  'app/dashboard/projects/_components/ds/projects-detail-ds-workspace.tsx',
);
const detailModel = readRel(
  webSrc,
  'app/dashboard/projects/_components/ds/projects-detail-ds-model.ts',
);
const client = readRel(webSrc, 'lib/api/creative-studio.ts');
const en = JSON.parse(readRel(webSrc, '../messages/en.json'));
const tr = JSON.parse(readRel(webSrc, '../messages/tr.json'));

describe('Project Documents — real media assets', () => {
  it('removes hardcoded DOC_NAMES demo document seeding', () => {
    assert.doesNotMatch(detailModel, /DOC_NAMES/);
    assert.doesNotMatch(detailModel, /EPC Agreement/);
    assert.doesNotMatch(detailModel, /Sarah Chen/);
    assert.match(detailModel, /const documents: DetailDocument\[] = \[]/);
  });

  it('DocumentsTab loads assets with linked_project_id and excludes archived by default', () => {
    assert.match(detailWorkspace, /listCreativeStudioMediaAssets/);
    assert.match(detailWorkspace, /linked_project_id:\s*projectId/);
    assert.match(detailWorkspace, /include_archived:\s*false/);
    assert.match(detailWorkspace, /item\.linked_project_id === projectId/);
    assert.match(detailWorkspace, /item\.archived_at == null/);
  });

  it('keeps Drive sync panel and Project Assistant unchanged', () => {
    assert.match(detailWorkspace, /<ProjectDriveSyncPanel projectId=\{projectId\} \/>/);
    assert.match(detailWorkspace, /<ProjectAssistantPanel projectId=\{projectId\} \/>/);
    assert.match(detailWorkspace, /doc\.filename/);
    assert.match(detailWorkspace, /formatFileSize\(doc\.file_size\)/);
    assert.match(detailWorkspace, /source_type === 'google_drive'/);
    assert.match(detailWorkspace, /documents\.sourceGoogleDrive/);
    assert.match(detailWorkspace, /data-testid="project-documents-tab"/);
    assert.match(detailWorkspace, /data-testid="project-documents-empty"/);
    assert.match(detailWorkspace, /data-testid="project-documents-loading"/);
    assert.match(detailWorkspace, /data-testid="project-documents-error"/);
  });

  it('API client supports linked_project_id list filter', () => {
    assert.match(client, /linked_project_id\?:/);
    assert.match(client, /search\.set\('linked_project_id'/);
  });

  it('adds en/tr copy for empty/loading/error and Drive source badge', () => {
    assert.equal(en.projects.detail.documents.sourceGoogleDrive, 'Google Drive');
    assert.equal(tr.projects.detail.documents.sourceGoogleDrive, 'Google Drive');
    assert.ok(en.projects.detail.documents.empty.includes('synced'));
    assert.ok(tr.projects.detail.documents.empty.length > 10);
    assert.equal(en.projects.detail.documents.loading.includes('Loading'), true);
  });
});

describe('Project Documents — Drive folder hierarchy browse (C2)', () => {
  it('loads media_folders scoped by linked_project_id and filters assets by folder_id', () => {
    assert.match(detailWorkspace, /listCreativeStudioMediaFolders/);
    assert.match(detailWorkspace, /linked_project_id:\s*projectId/);
    assert.match(detailWorkspace, /folder_id:\s*selectedFolderId/);
    assert.match(detailWorkspace, /item\.linked_project_id === projectId/);
    assert.match(detailWorkspace, /item\.folder_id !== selectedFolderId/);
  });

  it('navigates root → child → nested with back to parent/all', () => {
    assert.match(detailWorkspace, /data-testid="project-documents-folder-nav"/);
    assert.match(detailWorkspace, /data-testid="project-documents-folder-all"/);
    assert.match(detailWorkspace, /data-testid="project-documents-folder-back"/);
    assert.match(detailWorkspace, /data-testid="project-documents-folder-chip-all"/);
    assert.match(detailWorkspace, /goToFolder\(null\)/);
    assert.match(detailWorkspace, /goToFolder\(parentFolderId\)/);
    assert.match(detailWorkspace, /goToFolder\(folder\.id\)/);
    assert.match(detailWorkspace, /projectRootIds/);
    assert.match(detailWorkspace, /childFolders/);
  });

  it('uses persisted Drive folder names — no hardcoded taxonomy in DocumentsTab', () => {
    assert.doesNotMatch(detailWorkspace, /folderCats\.00_PROJECT_INFO/);
    assert.doesNotMatch(detailWorkspace, /folder_category/);
    assert.match(detailWorkspace, /folderById\.get\(folderId\)\?\.name/);
    assert.match(detailWorkspace, /folder\.name/);
  });

  it('exposes folder list linked_project_id on API client', () => {
    assert.match(client, /listCreativeStudioMediaFolders/);
    assert.match(
      client,
      /export async function listCreativeStudioMediaFolders\(options\?: \{[\s\S]*linked_project_id\?:/,
    );
    assert.match(client, /linked_project_id\?: string \| null;/);
  });

  it('adds en/tr copy for folder navigation empty/loading/error', () => {
    assert.equal(en.projects.detail.documents.allFolders, 'All documents');
    assert.equal(tr.projects.detail.documents.allFolders, 'Tüm belgeler');
    assert.equal(en.projects.detail.documents.backToAll, 'Back to all');
    assert.equal(tr.projects.detail.documents.backToParent, 'Üst klasöre dön');
    assert.ok(en.projects.detail.documents.folderEmpty.length > 5);
    assert.ok(tr.projects.detail.documents.foldersLoadError.length > 5);
    assert.equal(en.projects.detail.documents.foldersLoading.includes('Loading'), true);
  });
});
