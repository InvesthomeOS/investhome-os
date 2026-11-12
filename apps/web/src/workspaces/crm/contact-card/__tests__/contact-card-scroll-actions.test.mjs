import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { phaseFieldVisible, unitIdentifier, unitsForPhase } from '../../project-phase-unit.mjs';
import { reminderInstant, reminderPayload } from '../../task-reminder-default.mjs';

const webRoot = new URL('../../../../../', import.meta.url);

function read(path) {
  return readFileSync(new URL(path, webRoot), 'utf8');
}

test('lead and contact drawers use one vertical scroll container', () => {
  const leadsCss = read('src/app/workspaces/crm/leads/leads-ops.css');
  const drawer = leadsCss.slice(leadsCss.indexOf('.crm-ops-drawer {'), leadsCss.indexOf('.crm-ops-drawer__head'));
  assert.match(drawer, /overflow:\s*hidden/);
  assert.match(drawer, /height:\s*100dvh/);
  const body = leadsCss.slice(leadsCss.indexOf('.crm-ops-drawer__body {'), leadsCss.indexOf('.crm-ops-drawer__body h4'));
  assert.match(body, /min-height:\s*0/);
  assert.match(body, /overflow:\s*auto/);
  const cardCss = read('src/workspaces/crm/contact-card/contact-card.css');
  assert.match(cardCss, /\.ih-drawer:has\(\.crm-contact-card\) \.ih-drawer__body/);
  assert.match(cardCss, /min-height:\s*0/);
});

test('lead actions keep three equal quick actions and a separated menu', () => {
  const source = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx');
  const menu = source.slice(source.indexOf('<OsOverflowMenu'), source.indexOf('data-testid="crm-lead-actions"'));
  const actions = source.slice(source.indexOf('data-testid="crm-lead-actions"'), source.indexOf('</aside>'));
  assert.match(menu, /t\.openPerson/);
  assert.match(menu, /t\.edit/);
  assert.match(menu, /t\.matches/);
  assert.match(menu, /t\.agreements/);
  assert.match(menu, /destructive: true/);
  assert.match(menu, /Pipeline’dan Kaldır/);
  assert.match(actions, /t\.emailAction/);
  assert.match(actions, /t\.whatsappAction/);
  assert.match(actions, /t\.addTask/);
  assert.ok(actions.indexOf('t.emailAction') < actions.indexOf('t.whatsappAction'));
  assert.ok(actions.indexOf('t.whatsappAction') < actions.indexOf('t.addTask'));
  assert.doesNotMatch(actions, /t\.openPerson/);
  assert.doesNotMatch(actions, /t\.edit/);
  assert.doesNotMatch(actions, /data-testid="crm-leads-convert"/);
  assert.doesNotMatch(actions, /Satışa Döndü/);
  const css = read('src/app/workspaces/crm/leads/leads-ops.css');
  assert.match(css, /\.crm-ops-drawer__quick button[\s\S]*height:\s*36px/);
  assert.match(css, /grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\)/);
});

test('email composer attachment snapshot is unchanged', () => {
  const source = read('src/workspaces/crm/contact-card/email-send-composer.tsx');
  assert.match(source, /attachmentsRef/);
  assert.match(source, /FileList/);
});

test('phase field is hidden when a project has no phases', () => {
  assert.equal(phaseFieldVisible([]), false);
  assert.equal(phaseFieldVisible(null), false);
  const units = [{ id: '1', phase_id: '', unit_number: 'A-201' }];
  assert.deepEqual(unitsForPhase(units, '', []), units);
});

test('phase field filters units and keeps the identifier text', () => {
  const phases = [{ id: 'historic', name: 'Historic' }];
  assert.equal(phaseFieldVisible(phases), true);
  const units = [
    { id: 'a', phase_id: 'historic', unit_number: '204' },
    { id: 'b', phase_id: 'addition', unit_number: '204' },
  ];
  assert.deepEqual(unitsForPhase(units, '', phases), []);
  assert.deepEqual(unitsForPhase(units, 'historic', phases).map((item) => item.unit_number), ['204']);
  assert.equal(unitIdentifier(' A-201 '), 'A-201');
  assert.equal(unitIdentifier('Historic 204').includes('Historic'), true);
});

test('default reminder is 10 minutes before the Istanbul due instant', () => {
  const due = '2026-11-09T11:35:00+03:00';
  const remind = reminderInstant(due, 10);
  assert.equal(remind, '2026-11-09T08:25:00.000Z');
  const rows = reminderPayload(due, 10, 'in_app');
  assert.equal(rows.length, 1);
  assert.equal(rows[0].channel, 'in_app');
  assert.equal(rows[0].offset_minutes, 10);
  assert.deepEqual(reminderPayload(due, 'none', 'in_app'), []);
  assert.deepEqual(reminderPayload('', 10, 'in_app'), []);
});
