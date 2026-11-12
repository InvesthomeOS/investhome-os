import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const root = new URL('../../../', import.meta.url);

function read(path) {
  return readFileSync(new URL(path, root), 'utf8');
}

const interactions = read('src/app/dashboard/_components/screenshot-dashboard-interactions.tsx');
const header = read('src/app/dashboard/_components/screenshot-dashboard-header.tsx');
const actions = read('src/app/dashboard/_components/dashboard-header-actions.tsx');
const shell = read('src/components/shell/os-shell.tsx');
const crmLayout = read('src/app/workspaces/crm/layout.tsx');
const en = read('messages/en.json');
const tr = read('messages/tr.json');

test('dashboard and CRM share the real notification center', () => {
  assert.match(shell, /NotificationProvider/);
  assert.match(shell, /<NotificationDrawer \/>/);
  assert.equal(shell.match(/<NotificationDrawer/g)?.length, 1);
  assert.match(header, /useNotifications\(\)/);
  assert.match(header, /openDrawer/);
  assert.match(header, /unreadCount/);
  assert.match(header, /onOpenNotifications=\{openDrawer\}/);
  assert.match(actions, /NotificationBell/);
  assert.match(actions, /pathname === '\/dashboard'/);
  assert.match(crmLayout, /OsShell/);
  assert.doesNotMatch(crmLayout, /CrmHeader/);
});

test('mock notification drawer and fake entries are gone', () => {
  assert.doesNotMatch(interactions, /MockNotifications/);
  assert.doesNotMatch(interactions, /unreadCount = 2/);
  assert.doesNotMatch(interactions, /notificationsOpen/);
  assert.doesNotMatch(interactions, /openNotifications/);
  assert.doesNotMatch(interactions, /Marina Heights/);
  assert.doesNotMatch(interactions, /Greenview/);
  assert.doesNotMatch(header, /openNotifications,/);
  assert.doesNotMatch(header, /openNotifications \}/);
  for (const messages of [en, tr]) {
    const dashboard = JSON.parse(messages).screenshotDashboard;
    assert.equal(dashboard.notifications, undefined);
    assert.doesNotMatch(JSON.stringify(dashboard), /Marina Heights/);
    assert.doesNotMatch(JSON.stringify(dashboard), /Greenview/);
  }
});
