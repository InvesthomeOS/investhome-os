/**
 * CSRF header is attached in memory only — never localStorage/sessionStorage.
 * Run: node --test src/lib/auth/__tests__/csrf-frontend.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../../..');

function read(rel) {
  return readFileSync(join(webSrc, rel), 'utf8');
}

describe('staff CSRF client', () => {
  it('sends X-CSRF-Token on state-changing requests and keeps the token in memory', () => {
    const client = read('lib/api/client.ts');
    assert.match(client, /export const CSRF_HEADER = 'X-CSRF-Token'/);
    assert.match(client, /csrfTokenMemory/);
    assert.match(client, /ensureCsrfToken/);
    assert.match(client, /\/auth\/csrf/);
    assert.doesNotMatch(client, /localStorage\.setItem/);
    assert.doesNotMatch(client, /sessionStorage\.setItem/);
    assert.match(client, /csrf_rejected/);
  });

  it('clears the in-memory token on logout', () => {
    const auth = read('lib/api/auth.ts');
    assert.match(auth, /clearCsrfToken/);
  });
});
