import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const webRoot = new URL('../../../../', import.meta.url);

function source(path) {
  return readFileSync(new URL(path, webRoot), 'utf8');
}

test('in-app alerts stay until closed and background tabs use the desktop notification', () => {
  const provider = source('src/lib/notifications/notification-context.tsx');
  const api = source('src/lib/api/notifications.ts');
  assert.doesNotMatch(provider, /setTimeout\(\(\) => setToasts/);
  assert.match(provider, /observeNotificationIds/);
  assert.match(provider, /visibilityState === 'visible'/);
  assert.match(provider, /new Notification/);
  assert.match(provider, /requireInteraction: true/);
  assert.match(provider, /closeToast/);
  assert.doesNotMatch(provider, /closeToast[\s\S]{0,180}dismissNotification/);
  assert.match(provider, /firstLoad/);
  assert.match(provider, /if \(firstLoad\) setLoading\(true\)/);
  assert.match(api, /NOTIFICATION_REFRESH_MS = 60_000/);
  assert.match(provider, /setInterval\(\(\) => void refresh\(\), NOTIFICATION_REFRESH_MS\)/);
  assert.match(source('public/notification-sw.js'), /showNotification/);
  assert.match(source('src/app/dashboard/profile/notification-preferences.tsx'), /Masaüstü bildirimleri/);
  assert.match(source('src/app/dashboard/profile/notification-preferences.tsx'), /requestPermission/);
});

test('drawer actions share one height and clear archives without deleting', () => {
  const drawer = source('src/app/dashboard/_components/notification-drawer.tsx');
  const css = source('src/app/globals.css');
  const rule = css.slice(css.indexOf('.notification-item__actions button'), css.indexOf('.executive__notification-summary'));
  assert.match(rule, /height:\s*32px/);
  assert.match(rule, /min-height:\s*32px/);
  assert.match(rule, /border-radius:\s*8px/);
  assert.match(rule, /font-size:\s*0\.75rem/);
  assert.match(drawer, /actions.clearAll/);
  assert.match(drawer, /actions.markAllRead/);
  assert.match(drawer, /window.confirm/);
  assert.match(drawer, /loading && items.length === 0/);
});

test('task completion, reschedule, and create cancel stay compact', () => {
  const tasks = source('src/app/workspaces/crm/tasks/_components/crm-tasks-workspace.tsx');
  const api = source('src/workspaces/crm/api/activities.ts');
  assert.match(tasks, /Sonuç \/ Görüşme Notu/);
  assert.match(tasks, /data-testid="task-complete-open"/);
  assert.match(tasks, /data-testid="task-postpone-open"/);
  assert.match(tasks, /status !== 'completed'/);
  assert.match(tasks, /data-testid="task-drawer-close"/);
  assert.match(tasks, /data-testid="task-form-cancel"/);
  assert.match(tasks, /setPromptComplete\(true\)/);
  assert.match(api, /outcome/);
  assert.match(api, /due_date/);
  assert.doesNotMatch(tasks, /crm-ops-drawer__actions[\s\S]{0,80}width:\s*100%/);
});

test('communication is a manual activity and the person menu is reduced', () => {
  const card = source('src/workspaces/crm/contact-card/unified-contact-card.tsx');
  const copy = source('src/workspaces/crm/contact-card/person-card-copy.ts');
  const history = source('src/workspaces/crm/contact-card/history-stream.tsx');
  const menu = card.slice(card.indexOf('data-testid="contact-more-menu"'), card.indexOf('contact-junk-banner'));
  assert.match(copy, /İletişim Ekle/);
  assert.match(copy, /İletişim \/ Görüşme Notu/);
  assert.match(card, /activity_type: noteType/);
  assert.match(card, /source: 'communication_follow_up'/);
  assert.match(history, /data-testid="communication-add"/);
  assert.match(menu, /contact-assign-owner/);
  assert.match(menu, /contact-edit-open/);
  assert.match(menu, /Kişiyi Sil/);
  assert.doesNotMatch(menu, /Görev Oluştur/);
  assert.doesNotMatch(menu, /contact-junk|moveToJunk|junkReason/);
});

test('agreement form follows uses_phases, summarizes the unit, and prefixes USD', () => {
  const dialog = source('src/workspaces/crm/crm-record-dialog.tsx');
  const form = source('src/app/dashboard/projects/_components/project-form-modal.tsx');
  const purchase = source('src/workspaces/crm/contact-card/purchase-detail-view.tsx');
  assert.match(form, /Fazlı proje/);
  assert.match(form, /uses_phases/);
  assert.match(dialog, /data-testid="phased-project-empty"/);
  assert.match(dialog, /Bu proje fazlı olarak tanımlı/);
  assert.match(dialog, /data-testid="agreement-unit-summary"/);
  assert.match(dialog, /data-testid="sale-price-prefix"/);
  assert.match(dialog, /currencyPrefix\(/);
  assert.match(dialog, /replace\(\/\[\^0-9\.\]\/g, ''\)/);
  assert.match(purchase, /data-testid="cancel-agreement"/);
  assert.match(purchase, /data-testid="return-pipeline-form"/);
  assert.match(purchase, /Pipeline'a geri döndür|Pipeline&apos;a geri döndür/);
  assert.match(purchase, /crm-pd-task-actions/);
  assert.doesNotMatch(dialog, /Historic/);
  assert.doesNotMatch(dialog, /Addition/);
});
