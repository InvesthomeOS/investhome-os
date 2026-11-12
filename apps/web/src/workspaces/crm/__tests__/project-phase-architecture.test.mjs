import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { interestLabel, phaseFieldVisible, unitIdentifier, unitsForPhase } from '../project-phase-unit.mjs';

const webRoot = new URL('../../../../', import.meta.url);

function source(path) {
  return readFileSync(new URL(path, webRoot), 'utf8');
}

test('phase field stays hidden for a project with no phases', () => {
  assert.equal(phaseFieldVisible([]), false);
  assert.equal(phaseFieldVisible(null), false);
  const units = [{ id: '1', phase_id: '', unit_number: 'A-201' }];
  assert.deepEqual(unitsForPhase(units, '', []).map((item) => item.unit_number), ['A-201']);
});

test('one or many phases filter units without merging the name into the identifier', () => {
  const phases = [{ id: 'historic', name: 'Historic' }, { id: 'addition', name: 'Addition' }];
  assert.equal(phaseFieldVisible(phases.slice(0, 1)), true);
  assert.equal(phaseFieldVisible(phases), true);
  const units = [
    { id: 'a', phase_id: 'historic', unit_number: '204' },
    { id: 'b', phase_id: 'addition', unit_number: '204' },
  ];
  assert.deepEqual(unitsForPhase(units, 'historic', phases).map((item) => item.unit_number), ['204']);
  assert.equal(unitIdentifier('Historic 204'), 'Historic 204');
  assert.equal(unitIdentifier('204'), '204');
  assert.equal(interestLabel('The Temple', 'Historic', '204'), 'The Temple · Historic · 204');
  assert.equal(interestLabel('Plain', '', 'A-201'), 'Plain · A-201');
  assert.equal(interestLabel('Plain', null, null), 'Plain');
});

test('project create and detail use the same phase editor', () => {
  const form = source('src/app/dashboard/projects/_components/project-form-modal.tsx');
  const detail = source('src/app/dashboard/projects/_components/ds/projects-detail-ds-workspace.tsx');
  const editor = source('src/app/dashboard/projects/_components/project-phase-editor.tsx');
  assert.match(form, /ProjectPhaseEditor/);
  assert.match(detail, /resolvedTab === 'phases'/);
  assert.match(editor, /data-testid="project-phases"/);
  assert.match(editor, /project-phases-empty/);
  assert.doesNotMatch(editor, /Historic/);
  assert.doesNotMatch(editor, /Addition/);
});

test('inventory and lead forms hide phase until the project has phases', () => {
  const inventory = source('src/app/dashboard/inventory/_components/inventory-create-modal.tsx');
  const leads = source('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx');
  const purchase = source('src/workspaces/crm/contact-card/purchase-detail-view.tsx');
  const dialog = source('src/workspaces/crm/crm-record-dialog.tsx');
  const editor = source('src/app/dashboard/projects/_components/project-phase-editor.tsx');
  assert.match(inventory, /phases\.length/);
  assert.match(inventory, /display_id/);
  assert.match(leads, /leadUsesPhases/);
  assert.match(leads, /phased-project-empty/);
  assert.match(leads, /!leadUsesPhases \|\| \(leadPhaseReady && form\.phase_id\)/);
  assert.match(leads, /inventory_asset_id/);
  assert.match(leads, /selectedPhaseName/);
  assert.match(purchase, /data-testid="purchase-card-phase"/);
  assert.match(purchase, /unitSelectionLabel/);
  assert.match(purchase, /phaseRequired && !unitPhaseId/);
  assert.match(purchase, /!phaseRequired \|\| unitPhaseId/);
  assert.match(dialog, /uses_phases && \(unitsQuery\.data\?\.phases \?\? \[\]\)\.length/);
  assert.match(dialog, /data-testid="phased-project-empty"/);
  assert.match(dialog, /!unitsQuery\.data\?\.uses_phases \|\| phaseId/);
  assert.match(dialog, /unitSelectionLabel/);
  assert.match(editor, /data-testid="project-phase-units"/);
  assert.doesNotMatch(editor, /Historic/);
  assert.doesNotMatch(editor, /Addition/);
});
