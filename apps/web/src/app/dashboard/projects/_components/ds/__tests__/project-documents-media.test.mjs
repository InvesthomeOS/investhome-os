/**
 * Phase B — Project Documents tab loads real project-scoped media assets.
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

  it('keeps Drive sync panel and shows filename / category / type / size / Drive badge', () => {
    assert.match(detailWorkspace, /<ProjectDriveSyncPanel projectId=\{projectId\} \/>/);
    assert.match(detailWorkspace, /doc\.filename/);
    assert.match(detailWorkspace, /folder_category/);
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
    assert.equal(en.projects.detail.documents.folderCats['09_DOCUMENTS'], 'Documents');
    assert.equal(tr.projects.detail.documents.folderCats['09_DOCUMENTS'], 'Belgeler');
  });
});
