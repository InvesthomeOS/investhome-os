/**
 * Overview copy: missing data stays quiet and localized.
 * Run: node --test src/app/dashboard/projects/_components/ds/__tests__/project-overview-copy.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../../../../../../');
const workspace = readFileSync(
  join(webSrc, 'app/dashboard/projects/_components/ds/projects-detail-ds-workspace.tsx'),
  'utf8',
);
const en = JSON.parse(readFileSync(join(webSrc, '../messages/en.json'), 'utf8'));
const tr = JSON.parse(readFileSync(join(webSrc, '../messages/tr.json'), 'utf8'));
const detailEn = en.projects.detail;
const detailTr = tr.projects.detail;

describe('project overview copy', () => {
  it('does not present a completeness heuristic as a risk level', () => {
    assert.match(workspace, /data-testid="project-risk-level"/);
    assert.match(workspace, /tD\('notices\.riskUncalculated'\)/);
    assert.doesNotMatch(workspace, /tDs\(`risk\.\$\{projectRisk\}`\)/);
    assert.equal(detailTr.notices.riskUncalculated, 'Henüz hesaplanmadı');
    assert.equal(detailEn.notices.riskUncalculated, 'Not calculated yet');
  });

  it('localizes the project-created activity key', () => {
    assert.match(workspace, /'activity\.project\.created': 'activityEvents\.created'/);
    assert.match(workspace, /title\.startsWith\('activity\.'\)/);
    assert.equal(detailTr.activityEvents.created, 'Proje oluşturuldu');
    assert.equal(detailEn.activityEvents.created, 'Project created');
  });

  it('renders missing-data notices outside the warning styles', () => {
    assert.match(workspace, /data-testid="project-missing-details"/);
    assert.match(workspace, /'No project manager assigned': 'notices\.missingManager'/);
    assert.match(workspace, /'No project team members': 'notices\.missingTeam'/);
    assert.match(workspace, /'Budget data missing': 'notices\.missingBudget'/);
    assert.match(workspace, /'Completion percentage missing': 'notices\.missingCompletion'/);
    assert.match(workspace, /missingDataNoticeKey\(item\.title\) == null/);
    assert.equal(detailTr.notices.missingManager, 'Proje yöneticisi henüz atanmadı');
    assert.equal(detailTr.notices.missingTeam, 'Proje ekibi henüz oluşturulmadı');
    assert.equal(detailTr.notices.missingBudget, 'Bütçe verisi henüz eklenmedi');
    assert.equal(detailTr.notices.missingCompletion, 'Tamamlanma oranı henüz girilmedi');
    assert.equal(detailEn.notices.missingManager, 'No project manager assigned');
    assert.equal(detailEn.notices.missingTeam, 'No project team members');
    assert.ok(detailEn.notices.missingBudget.length > 5);
    assert.ok(detailEn.notices.missingCompletion.length > 5);
  });
});
