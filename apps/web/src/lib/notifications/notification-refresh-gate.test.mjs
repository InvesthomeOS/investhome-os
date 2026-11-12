import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { createNotificationRefreshGate } from './notification-refresh-gate.mjs';

const provider = readFileSync(new URL('./notification-context.tsx', import.meta.url), 'utf8');

test('one initial refresh, then one refresh per interval tick', async () => {
  const calls = [];
  const gate = createNotificationRefreshGate();
  const refresh = () => gate(async () => {
    calls.push('fetch');
  });

  let effectRuns = 0;
  const canView = true;
  const deps = [canView, refresh];
  let previous = null;
  const mount = () => {
    if (previous && previous[0] === deps[0] && previous[1] === deps[1]) return;
    previous = deps;
    effectRuns += 1;
    void refresh();
  };

  mount();
  mount();
  mount();
  await Promise.resolve();
  assert.equal(effectRuns, 1);
  assert.equal(calls.length, 1);

  await refresh();
  await refresh();
  assert.equal(calls.length, 3);
});

test('concurrent refresh attempts collapse to the in-flight request plus one follow-up', async () => {
  let active = 0;
  let maxActive = 0;
  const resolvers = [];
  const gate = createNotificationRefreshGate();
  const task = () => {
    active += 1;
    maxActive = Math.max(maxActive, active);
    return new Promise((resolve) => {
      resolvers.push(() => {
        active -= 1;
        resolve();
      });
    });
  };

  const first = gate(task);
  await Promise.resolve();
  const second = gate(task);
  const third = gate(task);
  assert.equal(resolvers.length, 1);
  assert.equal(maxActive, 1);
  resolvers.shift()();
  await Promise.resolve();
  assert.equal(resolvers.length, 1);
  resolvers.shift()();
  await Promise.all([first, second, third]);
  assert.equal(maxActive, 1);
  assert.equal(active, 0);
});

test('provider keeps list and unread polling without sync or a render loop', () => {
  assert.match(provider, /fetchNotifications\(\)/);
  assert.match(provider, /fetchNotificationUnreadCount\(\)/);
  assert.match(provider, /refreshGate/);
  assert.match(provider, /\[canView, getTitle, getMessage, router\]/);
  assert.match(provider, /\[canView, refresh\]/);
  assert.doesNotMatch(provider, /sync=/);
  assert.match(provider, /notification-toast/);
  assert.match(provider, /seenIds/);
  assert.doesNotMatch(provider, /setTimeout\(\(\) => setToasts/);
});
