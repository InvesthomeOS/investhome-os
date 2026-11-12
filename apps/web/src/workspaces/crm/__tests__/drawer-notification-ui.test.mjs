import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { formatOsDate, formatOsDateTime, formatOsRelative } from '../../../lib/datetime/os-datetime.mjs';
import { isRawMessageKey, notificationFallback } from '../../../lib/i18n/notification-text.mjs';

const webRoot = new URL('../../../../', import.meta.url);

function read(path) {
  return readFileSync(new URL(path, webRoot), 'utf8');
}

test('the shared overflow trigger is a borderless ellipsis', () => {
  const css = read('src/app/globals.css');
  const trigger = css.slice(css.indexOf('.os-overflow__trigger {'), css.indexOf('.os-overflow__trigger:hover'));
  assert.match(trigger, /border:\s*0/);
  assert.match(trigger, /background:\s*transparent/);
  assert.match(trigger, /width:\s*32px/);
  assert.match(trigger, /height:\s*32px/);
  assert.doesNotMatch(trigger, /border:\s*1px/);
  const menu = read('src/components/shell/os-overflow-menu.tsx');
  assert.match(menu, /os-overflow-ellipsis/);
  assert.match(menu, /⋯/);
  assert.doesNotMatch(menu, /⋮/);
});

test('open CRM and notification drawers lock the page scroll', () => {
  const leads = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx');
  const notes = read('src/app/dashboard/_components/notification-drawer.tsx');
  const css = read('src/app/globals.css');
  const lock = read('src/lib/ui/scroll-lock.mjs');
  assert.match(leads, /if \(!drawer\) return undefined;\s*return lockPageScroll\(\)/);
  assert.match(notes, /const unlock = lockPageScroll\(\)/);
  assert.match(lock, /html\.style\.overflow = 'hidden'/);
  assert.match(lock, /body\.style\.overflow = 'hidden'/);
  assert.match(css, /html\.ih-scroll-lock,\s*html\.ih-scroll-lock body \{\s*overflow: hidden;/);
  assert.doesNotMatch(notes, /document\.body\.style\.overflow = 'hidden'/);
});

test('each drawer keeps a single scroll region', () => {
  const leadsCss = read('src/app/workspaces/crm/leads/leads-ops.css');
  const drawer = leadsCss.slice(leadsCss.indexOf('.crm-ops-drawer {'), leadsCss.indexOf('.crm-ops-drawer__head'));
  assert.match(drawer, /overflow:\s*hidden/);
  assert.match(drawer, /height:\s*100dvh/);
  assert.doesNotMatch(drawer, /height:\s*\d+px/);
  const body = leadsCss.slice(leadsCss.indexOf('.crm-ops-drawer__body {'), leadsCss.indexOf('.crm-ops-drawer__body h4'));
  assert.match(body, /overflow:\s*auto/);
  assert.match(body, /min-height:\s*0/);
  const globals = read('src/app/globals.css');
  const panel = globals.slice(globals.indexOf('.notification-drawer__panel {'), globals.indexOf('.notification-drawer__scroll'));
  assert.match(panel, /overflow:\s*hidden/);
  assert.doesNotMatch(panel, /overflow-y:\s*auto/);
  const scroll = globals.slice(globals.indexOf('.notification-drawer__scroll {'), globals.indexOf('.notification-drawer__header'));
  assert.match(scroll, /overflow:\s*auto/);
  assert.match(scroll, /min-height:\s*0/);
  assert.match(scroll, /flex:\s*1 1 auto/);
});

test('sale conversion stays on the final pipeline stage', () => {
  const source = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx');
  const actions = source.slice(source.indexOf('data-testid="crm-lead-actions"'), source.indexOf('</aside>'));
  assert.doesNotMatch(actions, /data-testid="crm-leads-convert"/);
  assert.doesNotMatch(actions, /Satışa Döndü/);
  assert.match(source, /data-testid="crm-lead-stage-control"/);
  assert.match(source, /\{STAGES\.map\(\(stage\)/);
  const branch = source.slice(source.indexOf("if (next === 'converted')"), source.indexOf("if (next === 'unqualified')"));
  assert.match(branch, /convertMutation\.mutate/);
  assert.doesNotMatch(branch, /moveCrmLeadStage|stageMutation/);
  assert.match(source, /role="tablist"/);
  assert.match(source, /t\.generalTab/);
  assert.match(source, /t\.tasksTab/);
  assert.match(source, /t\.notesTab/);
  assert.match(source, /t\.historyTab/);
});

test('notification actions share one aligned row and keys never render raw', () => {
  const notes = read('src/app/dashboard/_components/notification-drawer.tsx');
  const actions = notes.slice(notes.indexOf('notification-item__actions'), notes.indexOf('export function NotificationDrawer'));
  const open = actions.indexOf("t('actions.openRecord')");
  const dismiss = actions.indexOf("t('actions.dismiss')");
  assert.ok(open > 0 && open < dismiss);
  const css = read('src/app/globals.css');
  const row = css.slice(css.indexOf('.notification-item__actions {'), css.indexOf('.notification-item__actions button'));
  assert.match(row, /display:\s*flex/);
  assert.match(row, /align-items:\s*center/);
  const overdue = notificationFallback('notifications.crm.tasks_overdue.message', { title: 'Ara' }, 'tr');
  assert.equal(overdue, 'Görev süresi geçti: Ara');
  assert.equal(isRawMessageKey(overdue), false);
  assert.equal(isRawMessageKey('notifications.crm.tasks_overdue.message'), true);
  for (const key of [
    'notifications.crm.task_due.message',
    'notifications.crm.meeting_soon.title',
    'notifications.crm.new_lead.message',
    'notifications.crm.instagram_message.title',
    'notifications.crm.meta_comment.title',
    'notifications.crm.agreement_created.message',
    'notifications.crm.sale.title',
    'notifications.crm.social_published.message',
  ]) {
    const text = notificationFallback(key, { title: 'Villa', name: 'Ada', minutes: '15' }, 'en');
    assert.equal(isRawMessageKey(text), false, key);
    assert.equal(text.includes('notifications.'), false, key);
  }
  const unknown = notificationFallback('notifications.crm.custom_event.message', { name: 'Ada' }, 'en');
  assert.equal(unknown, 'custom event: Ada');
  assert.equal(isRawMessageKey(unknown), false);
});

test('dashboard and CRM share the Istanbul clock and do not use the demo date', () => {
  const dashboard = read('src/app/dashboard/_components/screenshot-dashboard.tsx');
  const leads = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx');
  const pipeline = read('src/app/workspaces/crm/pipeline/_components/crm-pipeline-live-workspace.tsx');
  assert.doesNotMatch(dashboard, /new Date\(2025,\s*4,\s*26\)/);
  assert.match(dashboard, /formatOsDate\(dateValue, locale\)/);
  assert.match(dashboard, /const dateValue = new Date\(\)/);
  assert.match(leads, /formatOsDateTime/);
  assert.match(pipeline, /formatOsDateTime/);
  const stamp = '2026-11-09T08:35:00.000Z';
  assert.equal(formatOsDate(stamp, 'tr'), '9 Kas 2026');
  assert.equal(formatOsDateTime(stamp, 'tr'), '9 Kas 2026 · 11:35');
  assert.equal(formatOsRelative(stamp, '2026-11-09T08:40:00.000Z', 'tr'), '5 dk önce');
});

test('a toast closes without dismissing the notification record', () => {
  const source = read('src/lib/notifications/notification-context.tsx');
  const close = source.slice(source.indexOf('const closeToast'), source.indexOf('const openToast'));
  assert.match(source, /data-testid="notification-toast-close"/);
  assert.match(source, /seenIds/);
  assert.match(close, /setToasts/);
  assert.doesNotMatch(close, /dismissNotification|dismiss\(/);
  assert.doesNotMatch(source, /setTimeout\(\(\) => setToasts/);
  assert.match(source, /requireInteraction: true/);
  assert.match(read('src/app/dashboard/_components/notification-drawer.tsx'), /Bildirimleri temizle|actions.clearAll/);
  assert.match(source, /createPortal/);
});

test('creation notes stay in the Notlar tab and later notes are appended', () => {
  const leads = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx');
  const card = read('src/workspaces/crm/contact-card/unified-contact-card.tsx');
  const service = read('../api/src/investhome_api/services/crm/crm_lead_service.py');
  assert.match(leads, /t\.notesTab/);
  assert.match(leads, /data-testid="crm-lead-notes"/);
  assert.match(leads, /data-testid="crm-lead-note-form"/);
  assert.match(leads, /createNote\(/);
  assert.doesNotMatch(leads.slice(leads.indexOf('const noteMutation'), leads.indexOf('const sourceOptions')), /updateCrmLead/);
  assert.match(card, /data-testid="contact-saved-note"/);
  assert.match(service, /def _record_creation_note/);
  assert.match(service, /note_entries=_lead_note_entries/);
});

test('existing units are assigned to a phase only by explicit selection', () => {
  const editor = read('src/app/dashboard/projects/_components/project-phase-editor.tsx');
  assert.match(editor, /data-testid="phase-unit-assign"/);
  assert.match(editor, /updateInventoryAsset\(id, \{ phase_id: phaseId \}\)/);
  assert.doesNotMatch(editor, /Historic/);
  assert.doesNotMatch(editor, /Addition/);
});
