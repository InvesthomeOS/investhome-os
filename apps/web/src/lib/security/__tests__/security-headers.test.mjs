/**
 * Security header contracts for CSP / HSTS / nosniff / frame protection.
 * Run: node --test src/lib/security/__tests__/security-headers.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';
import { pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '../../../..');

function read(rel) {
  return readFileSync(join(webRoot, rel), 'utf8');
}

const headersMod = await import(
  pathToFileURL(join(here, '../security-headers.ts')).href
);

describe('security headers', () => {
  it('emits CSP with required directives and no wildcard policy', () => {
    const csp = headersMod.buildContentSecurityPolicy('test-nonce', {
      apiUrl: 'http://localhost:8000',
    });
    for (const directive of [
      'default-src',
      'script-src',
      'style-src',
      'img-src',
      'font-src',
      'connect-src',
      'frame-ancestors',
      'object-src',
      'base-uri',
      'form-action',
    ]) {
      assert.match(csp, new RegExp(directive));
    }
    assert.match(csp, /script-src[^;]*'self'/);
    assert.match(csp, /script-src[^;]*'nonce-test-nonce'/);
    assert.doesNotMatch(csp, /script-src[^;]*https:/);
    assert.match(csp, /object-src 'none'/);
    assert.match(csp, /frame-ancestors 'none'/);
    assert.doesNotMatch(csp, /default-src \*/);
    assert.doesNotMatch(csp, /script-src[^;]*\*/);
    assert.doesNotMatch(csp, /frame-ancestors \*/);
  });

  it('allows inline styles and the API origin, including X-CSRF-compatible connect-src', () => {
    const csp = headersMod.buildContentSecurityPolicy('n', {
      apiUrl: 'http://localhost:8000',
    });
    assert.match(csp, /style-src 'self' 'unsafe-inline'/);
    assert.match(csp, /connect-src[^;]*http:\/\/localhost:8000/);
    assert.match(csp, /connect-src[^;]*http:\/\/127\.0\.0\.1:8000/);
    assert.doesNotMatch(csp, /unsafe-eval/);
  });

  it('sends HSTS on HTTPS production requests only', () => {
    assert.equal(
      headersMod.shouldSendHsts({ protocol: 'https:', cookieSecure: true }),
      true,
    );
    assert.equal(
      headersMod.shouldSendHsts({
        protocol: 'http:',
        forwardedProto: 'https',
        cookieSecure: true,
      }),
      true,
    );
    assert.equal(
      headersMod.shouldSendHsts({ protocol: 'http:', cookieSecure: false }),
      false,
    );
    assert.equal(
      headersMod.shouldSendHsts({
        protocol: 'http:',
        forwardedProto: 'https',
        cookieSecure: false,
      }),
      false,
    );
    assert.doesNotMatch(headersMod.HSTS_VALUE, /preload/);
    assert.doesNotMatch(headersMod.HSTS_VALUE, /includeSubDomains/);
  });

  it('does not attach HSTS on local HTTP even when applying headers', () => {
    const store = new Map();
    headersMod.applySecurityHeaders(
      { set: (name, value) => store.set(name.toLowerCase(), value) },
      {
        nonce: 'abc',
        protocol: 'http:',
        cookieSecure: false,
        isDev: false,
        apiUrl: 'http://localhost:8000',
      },
    );
    assert.equal(store.get('content-security-policy')?.includes("default-src 'self'"), true);
    assert.equal(store.get('x-content-type-options'), 'nosniff');
    assert.equal(store.get('referrer-policy'), 'strict-origin-when-cross-origin');
    assert.equal(store.get('x-frame-options'), 'DENY');
    assert.equal(store.has('strict-transport-security'), false);
    assert.match(store.get('permissions-policy'), /camera=\(\)/);
  });

  it('attaches HSTS for HTTPS', () => {
    const store = new Map();
    headersMod.applySecurityHeaders(
      { set: (name, value) => store.set(name.toLowerCase(), value) },
      { nonce: 'abc', protocol: 'https:', cookieSecure: true },
    );
    assert.equal(store.get('strict-transport-security'), 'max-age=31536000');
  });

  it('wires middleware nonce CSP and layout nonce without changing auth gates', () => {
    const middleware = read('src/middleware.ts');
    assert.match(middleware, /isValidSessionJwt/);
    assert.match(middleware, /pathname === '\/login'/);
    assert.match(middleware, /Content-Security-Policy|applySecurityHeaders/);
    assert.match(middleware, /x-nonce/);
    assert.doesNotMatch(middleware, /pathname === '\/login' && session/);

    const layout = read('src/app/layout.tsx');
    assert.match(layout, /nonce=\{nonce\}/);
    assert.match(layout, /getCspNonce/);

    const nextConfig = read('next.config.ts');
    assert.match(nextConfig, /X-Content-Type-Options/);
    assert.match(nextConfig, /nosniff/);
    assert.match(nextConfig, /X-Frame-Options/);
    assert.match(nextConfig, /DENY/);
    assert.doesNotMatch(nextConfig, /Strict-Transport-Security/);
  });
});
