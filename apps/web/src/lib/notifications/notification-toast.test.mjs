import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { observeNotificationIds } from './notification-toast-detector.mjs';

const source = readFileSync(new URL('./notification-context.tsx', import.meta.url), 'utf8');

test('new unread notifications toast without alert and keep the center record', () => {
  assert.match(source, /notification-toast/);
  assert.match(source, /seenIds/);
  assert.doesNotMatch(source, /window\.alert\(/);
  assert.doesNotMatch(source, /setTimeout\(\(\) => setToasts/);
  assert.match(source, /observeNotificationIds/);
  assert.match(source, /createPortal/);
  assert.match(source, /notification-toast-stack/);
  assert.match(source, /unreadCount/);
  assert.match(source, /fetchNotifications\(\)/);
  assert.match(source, /fetchNotificationUnreadCount\(\)/);
  assert.doesNotMatch(source, /sync=/);
  assert.doesNotMatch(source, /refresh\(true\)/);
  assert.match(source, /createNotificationRefreshGate/);
  assert.match(source, /refreshGate/);
  assert.match(source, /void refresh\(\)/);
  assert.match(source, /setInterval\(\(\) => void refresh\(\), NOTIFICATION_REFRESH_MS\)/);
  assert.match(source, /\[canView, refresh\]/);
  assert.doesNotMatch(source, /\[canView, refresh, (items|loading|unreadCount)\]/);
});

const labels = readFileSync(new URL('../i18n/notification-labels.ts', import.meta.url), 'utf8');

test('notification label functions keep a stable identity across ordinary rerenders', () => {
  assert.match(labels, /const tRef = useRef\(t\)/);
  assert.match(labels, /tRef\.current = t/);
  assert.match(labels, /const getTitle = useCallback\(/);
  assert.match(labels, /const getMessage = useCallback\(/);
  assert.match(labels, /const getPriorityLabel = useCallback\(/);
  assert.match(labels, /const getTypeLabel = useCallback\(/);
  assert.match(labels, /const getGroupLabel = useCallback\(/);
  assert.match(labels, /return useMemo\(/);
  assert.doesNotMatch(labels, /getTitle:\s*\(/);
  assert.equal(labels.match(/\[\]/g)?.length, 5);
});

test('the first fetch is a baseline and later unread ids toast once', () => {
  const initial = observeNotificationIds(null, [
    { id: 'old', status: 'unread' },
    { id: 'read', status: 'read' },
  ]);
  assert.deepEqual(initial.fresh, []);
  const arrived = observeNotificationIds(initial.seen, [
    { id: 'old', status: 'unread' },
    { id: 'new', status: 'UNREAD' },
  ]);
  assert.deepEqual(arrived.fresh.map((item) => item.id), ['new']);
  const again = observeNotificationIds(arrived.seen, [
    { id: 'old', status: 'unread' },
    { id: 'new', status: 'unread' },
  ]);
  assert.deepEqual(again.fresh, []);
});

test('toast stack is portaled above the shell and polls on one timer', () => {
  assert.match(source, /createPortal/);
  assert.match(source, /document\.body/);
  assert.match(source, /data-testid="notification-toast-stack"/);
  assert.match(source, /NOTIFICATION_REFRESH_MS = 15_000|NOTIFICATION_REFRESH_MS/);
  const api = readFileSync(new URL('../api/notifications.ts', import.meta.url), 'utf8');
  assert.match(api, /NOTIFICATION_REFRESH_MS = 60_000/);
  const css = readFileSync(new URL('../../app/globals.css', import.meta.url), 'utf8');
  const stack = css.slice(css.indexOf('.notification-toast-stack {'), css.indexOf('.notification-toast {'));
  assert.match(stack, /top:\s*4\.5rem/);
  assert.match(stack, /z-index:\s*1400/);
  assert.doesNotMatch(stack, /bottom:\s*1rem/);
  const shell = readFileSync(new URL('../../components/shell/os-shell.tsx', import.meta.url), 'utf8');
  assert.match(shell, /NotificationProvider/);
});

test('polling effect does not depend on loading or list state', () => {
  const refreshStart = source.indexOf('const refresh = useCallback');
  const effectStart = source.indexOf('useEffect(() => {', refreshStart);
  const refreshBody = source.slice(refreshStart, effectStart);
  assert.match(refreshBody, /\[canView, getTitle, getMessage, router\]/);
  assert.doesNotMatch(refreshBody, /\[canView, getTitle,[^\]]*items/);
  assert.doesNotMatch(refreshBody, /\[canView, getTitle,[^\]]*loading/);
  assert.match(source, /setInterval\(\(\) => void refresh\(\), NOTIFICATION_REFRESH_MS\)/);
});
