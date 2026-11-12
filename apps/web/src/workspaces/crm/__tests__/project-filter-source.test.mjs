import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const webRoot = new URL('../../../../', import.meta.url);

function read(path) {
  return readFileSync(new URL(path, webRoot), 'utf8');
}

test('pipeline and lead filters list canonical projects, not the current lead result', () => {
  const pipeline = read('src/app/workspaces/crm/pipeline/_components/crm-pipeline-live-workspace.tsx');
  const leads = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx');
  const people = read('src/app/workspaces/crm/contacts/_components/people-workspace.tsx');
  for (const source of [pipeline, leads]) {
    assert.match(source, /fetchMembershipProjects/);
    assert.match(source, /pipeline-project-filter|crm-leads-project-filter/);
    assert.doesNotMatch(source, /data\?\.projects/);
  }
  assert.match(pipeline, /pipeline-phase-filter/);
  assert.match(leads, /Bu faza henüz ünite atanmadı/);
  assert.match(people, /project_id: agreementProject.includes\('-'\)/);
  assert.doesNotMatch(people, /the_temple/);
});

test('purchase and agreement selectors keep phase in front of the unit list', () => {
  const purchase = read('src/workspaces/crm/contact-card/purchase-detail-view.tsx');
  const dialog = read('src/workspaces/crm/crm-record-dialog.tsx');
  assert.match(purchase, /data-testid="purchase-card-phase"/);
  assert.match(purchase, /Bu faza henüz ünite atanmadı/);
  assert.match(dialog, /fetchMembershipProjects/);
  assert.match(dialog, /Bu faza henüz ünite atanmadı/);
  assert.doesNotMatch(dialog, /CRM_PROJECT_OPTIONS/);
});
