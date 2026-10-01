/**
 * Portal session cookie gate used by middleware.
 * Run: node --test src/lib/auth/__tests__/portal-session-cookie.test.mjs
 */

import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  PORTAL_SESSION_COOKIE,
  PORTAL_SESSION_TTL_SECONDS,
  isValidPortalSession,
  portalAccessDecision,
} from '../portal-session-cookie.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../../..');

function read(rel) {
  return readFileSync(join(webSrc, rel), 'utf8');
}

const SECRET = 'test-portal-session-secret-32bytes!!';

function encodePortalSession(payload, secret = SECRET) {
  const payloadJson = JSON.stringify(payload);
  const body = Buffer.from(payloadJson, 'utf8').toString('base64url');
  const sig = createHmac('sha256', secret).update(payloadJson).digest('base64url');
  return `${body}.${sig}`;
}

function validPayload(overrides = {}) {
  return {
    investorId: 'portal-inv-a',
    email: 'investor.a@investhome.demo',
    issuedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe('valid portal session accepted', () => {
  it('accepts a signed payload with investorId, email, and fresh issuedAt', async () => {
    const token = encodePortalSession(validPayload());
    assert.equal(await isValidPortalSession(token, SECRET), true);
  });
});

describe('forged cookie rejected', () => {
  it('rejects a cookie signed with a different secret', async () => {
    const token = encodePortalSession(validPayload(), 'attacker-secret-not-the-server');
    assert.equal(await isValidPortalSession(token, SECRET), false);
  });

  it('rejects an unsigned body pretending to be a session', async () => {
    const body = Buffer.from(JSON.stringify(validPayload()), 'utf8').toString('base64url');
    assert.equal(await isValidPortalSession(body, SECRET), false);
  });
});

describe('modified cookie rejected', () => {
  it('rejects a payload swapped onto another signature', async () => {
    const original = encodePortalSession(validPayload());
    const sig = original.slice(original.indexOf('.') + 1);
    const modifiedBody = Buffer.from(
      JSON.stringify(validPayload({ investorId: 'portal-inv-forged' })),
      'utf8',
    ).toString('base64url');
    assert.equal(await isValidPortalSession(`${modifiedBody}.${sig}`, SECRET), false);
  });
});

describe('expired cookie rejected', () => {
  it('rejects a correctly signed cookie whose issuedAt is beyond the TTL', async () => {
    const issuedAt = new Date(Date.now() - (PORTAL_SESSION_TTL_SECONDS + 120) * 1000).toISOString();
    const token = encodePortalSession(validPayload({ issuedAt }));
    assert.equal(await isValidPortalSession(token, SECRET), false);
  });
});

describe('empty/malformed cookie rejected', () => {
  it('rejects missing, empty, truncated, and non-json cookies', async () => {
    assert.equal(await isValidPortalSession(undefined, SECRET), false);
    assert.equal(await isValidPortalSession('', SECRET), false);
    assert.equal(await isValidPortalSession('not-a-session', SECRET), false);
    assert.equal(await isValidPortalSession('abc.', SECRET), false);
    assert.equal(await isValidPortalSession('.sig', SECRET), false);
    const incomplete = encodePortalSession({ investorId: 'x', issuedAt: new Date().toISOString() });
    assert.equal(await isValidPortalSession(incomplete, SECRET), false);
  });
});

describe('protected portal routes remain inaccessible without valid session', () => {
  it('sends unauthenticated portal paths to login and keeps login public', () => {
    assert.equal(portalAccessDecision('/portal', false), 'redirect-login');
    assert.equal(portalAccessDecision('/portal/documents', false), 'redirect-login');
    assert.equal(portalAccessDecision('/portal/projects/alpha', false), 'redirect-login');
    assert.equal(portalAccessDecision('/portal/login', false), 'next');
    assert.equal(portalAccessDecision('/portal/login', true), 'redirect-home');
    assert.equal(portalAccessDecision('/portal', true), 'next');
    assert.equal(portalAccessDecision('/portal/documents', true), 'next');
  });

  it('middleware validates the portal cookie instead of treating presence as auth', () => {
    const middleware = read('middleware.ts');
    assert.match(middleware, /isValidPortalSession/);
    assert.match(middleware, /portalAccessDecision/);
    assert.match(middleware, /PORTAL_SESSION_COOKIE/);
    assert.doesNotMatch(middleware, /if \(!portalSession && !isLogin\)/);
    assert.doesNotMatch(middleware, /if \(portalSession && isLogin\)/);
    assert.match(middleware, /\/portal\/login/);
    assert.doesNotMatch(middleware, /validation failed|invalid signature|expired cookie/i);
    const decoder = read('app/portal/_lib/session.ts');
    assert.match(decoder, /isPortalSessionExpired/);
    assert.match(decoder, /timingSafeEqual/);
    assert.doesNotMatch(decoder, /dev-only-portal-session-secret/);
    const edge = read('lib/auth/portal-session-cookie.mjs');
    assert.doesNotMatch(edge, /dev-only-portal-session-secret/);
    assert.doesNotMatch(edge, /investhome-portal-demo-session-secret/);
    assert.equal(PORTAL_SESSION_COOKIE, 'ih_portal_session');
  });
});
