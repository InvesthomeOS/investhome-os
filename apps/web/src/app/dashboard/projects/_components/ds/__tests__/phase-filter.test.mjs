import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const workspace = readFileSync(
  new URL('../projects-detail-ds-workspace.tsx', import.meta.url),
  'utf8',
);

test('phase selection stays in the query while tabs change', () => {
  assert.match(workspace, /searchParams\.get\('phase'\)/);
  assert.match(workspace, /Entire Project/);
  assert.match(workspace, /Tüm Proje/);
  assert.match(workspace, /phaseScope=\{phaseId\}/);
  assert.match(workspace, /fetchProjectFinancials\(projectId, financeAudience, phaseId \|\| undefined\)/);
  assert.match(workspace, /fetchProjectInvestors\(projectId, phaseId \|\| undefined\)/);
  assert.match(workspace, /data-testid="project-phase-kpis"/);
  assert.match(workspace, /verified_collections/);
  assert.match(workspace, /remaining_receivable/);
  assert.match(workspace, /project-units-phase-empty/);
  assert.match(workspace, /units\.phaseEmpty/);
  assert.match(workspace, /scopedPhase/);
});
