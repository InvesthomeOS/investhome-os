import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '../../../..');

function source(path) {
  return readFileSync(join(webRoot, path), 'utf8');
}

test('dashboard greeting comes from the signed-in user, not a hardcoded name', () => {
  const dashboard = source('src/app/dashboard/_components/screenshot-dashboard.tsx');
  const turkish = source('messages/tr.json');
  const english = source('messages/en.json');
  assert.equal(dashboard.includes('intro.greeting'), false);
  assert.equal(dashboard.includes('Emin'), false);
  assert.match(dashboard, /greetingName\(user\)/);
  assert.match(dashboard, /resolveGreetingTimezone\(user\?\.timezone/);
  assert.equal(turkish.includes('Günaydın, Emin'), false);
  assert.equal(english.includes('Good morning, Emin'), false);
  assert.match(turkish, /"morning": "Günaydın"/);
  assert.match(turkish, /"evening": "İyi akşamlar"/);
});

test('profile page edits personal fields and keeps role, email, password, and MFA locked', () => {
  const page = source('src/app/dashboard/profile/page.tsx');
  const auth = source('src/lib/api/auth.ts');
  assert.match(page, /name="first_name"/);
  assert.match(page, /name="last_name"/);
  assert.match(page, /name="preferred_language"/);
  assert.match(page, /name="timezone"/);
  assert.match(page, /updateMyProfile\(/);
  assert.match(page, /disabled=\{saving\}/);
  assert.match(page, /t\('saved'\)/);
  assert.match(page, /t\('saveFailed'\)/);
  assert.match(page, /changePassword\(/);
  assert.match(page, /<MfaEnrollCard/);
  assert.equal(page.includes('name="email"'), false);
  assert.equal(page.includes('name="role"'), false);
  assert.equal(page.includes('name="permissions"'), false);
  assert.equal(page.includes('updateUser('), false);
  assert.match(page, /\{user\.full_name\}/);
  assert.match(page, /\{user\.email\}/);
  assert.match(auth, /method: 'PATCH'/);
  assert.match(auth, /'\/auth\/me'/);
  assert.equal(auth.includes("first_name?: string"), true);
});
