import assert from 'node:assert/strict';
import test from 'node:test';

import {
  formatGreeting,
  greetingName,
  greetingPeriod,
  resolveGreetingTimezone,
} from '../greeting.ts';

const TR = {
  morning: 'Günaydın',
  afternoon: 'İyi günler',
  evening: 'İyi akşamlar',
  night: 'İyi geceler',
};

test('Hasan never receives a greeting that uses Emin', () => {
  const hasan = greetingName({ full_name: 'Hasan Yılmaz', email: 'hasan@investhome.com' });
  const emin = greetingName({ full_name: 'Emin Kaya', email: 'emin@investhome.com' });
  const hasanLine = formatGreeting('morning', hasan, TR);
  assert.equal(hasan, 'Hasan');
  assert.equal(hasanLine, 'Günaydın Hasan');
  assert.equal(hasanLine.includes('Emin'), false);
  assert.equal(formatGreeting('morning', emin, TR), 'Günaydın Emin');
  assert.equal(greetingName({ full_name: 'Hasan Yılmaz', email: 'hasan@investhome.com' }), 'Hasan');
});

test('greeting uses the authenticated first name, then the display name, then the email', () => {
  assert.equal(greetingName({ full_name: 'Hasan Yılmaz', email: 'hasan@investhome.com' }), 'Hasan');
  assert.equal(greetingName({ full_name: 'Hasan', email: 'other@investhome.com' }), 'Hasan');
  assert.equal(greetingName({ full_name: '', email: 'hasan@investhome.com' }), 'Hasan');
  assert.equal(greetingName({ full_name: '   ', email: 'emin.user@investhome.com' }), 'Emin');
});

test('an updated name is what the greeting uses', () => {
  const before = greetingName({ full_name: 'Sales User', email: 'sales@example.com' });
  const after = greetingName({ full_name: 'Hasan Yılmaz', email: 'sales@example.com' });
  assert.equal(before, 'Sales');
  assert.equal(formatGreeting('evening', after, TR), 'İyi akşamlar Hasan');
});

test('Europe/Istanbul at 22:49 is an evening greeting', () => {
  const at = new Date('2026-10-30T19:49:00Z');
  assert.equal(greetingPeriod(at, 'Europe/Istanbul'), 'evening');
  const name = greetingName({ full_name: 'Hasan Yılmaz', email: 'hasan@investhome.com' });
  assert.equal(formatGreeting(greetingPeriod(at, 'Europe/Istanbul'), name, TR), 'İyi akşamlar Hasan');
});

test('morning, afternoon, and late night use the profile timezone', () => {
  assert.equal(greetingPeriod(new Date('2026-10-30T05:00:00Z'), 'Europe/Istanbul'), 'morning');
  assert.equal(greetingPeriod(new Date('2026-10-30T08:59:00Z'), 'Europe/Istanbul'), 'morning');
  assert.equal(greetingPeriod(new Date('2026-10-30T09:00:00Z'), 'Europe/Istanbul'), 'afternoon');
  assert.equal(greetingPeriod(new Date('2026-10-30T14:59:00Z'), 'Europe/Istanbul'), 'afternoon');
  assert.equal(greetingPeriod(new Date('2026-10-30T23:30:00Z'), 'Europe/Istanbul'), 'night');
  assert.equal(greetingPeriod(new Date('2026-10-30T01:59:00Z'), 'Europe/Istanbul'), 'night');
  assert.equal(
    formatGreeting('morning', 'Emin', TR),
    'Günaydın Emin',
  );
  assert.equal(formatGreeting('afternoon', 'Hasan', TR), 'İyi günler Hasan');
  assert.equal(formatGreeting('night', 'Hasan', TR), 'İyi geceler Hasan');
});

test('saved timezone wins, then the browser, then Europe/Istanbul', () => {
  assert.equal(resolveGreetingTimezone('Europe/Istanbul', 'UTC'), 'Europe/Istanbul');
  assert.equal(resolveGreetingTimezone('UTC', 'Europe/Istanbul'), 'UTC');
  assert.equal(resolveGreetingTimezone('', 'America/New_York'), 'America/New_York');
  assert.equal(resolveGreetingTimezone('Not/AZone', 'Europe/Berlin'), 'Europe/Berlin');
  assert.equal(resolveGreetingTimezone(null, 'Mars/Olympus'), 'Europe/Istanbul');
  assert.equal(resolveGreetingTimezone(undefined, null), 'Europe/Istanbul');
});
