/**
 * Email / history HTML XSS hardening.
 * Run: node --test src/workspaces/crm/contact-card/__tests__/email-html-xss.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '../../../../../');

function read(rel) {
  return readFileSync(join(webRoot, rel), 'utf8');
}

const historyHtml = await import(pathToFileURL(join(here, '../history-html.ts')).href);

describe('email HTML XSS hardening', () => {
  it('renders normal email HTML and keeps safe formatting', () => {
    const html = historyHtml.sanitizeHtml(
      '<p>Hello <strong>Ada</strong> and <em>Grace</em></p><ul><li>One</li></ul>',
    );
    assert.match(html, /<p>/i);
    assert.match(html, /<strong>Ada<\/strong>/i);
    assert.match(html, /<em>Grace<\/em>/i);
    assert.match(html, /<li>One<\/li>/i);
    assert.match(html, /Hello/);
  });

  it('removes script tags and nested script payloads', () => {
    const html = historyHtml.sanitizeHtml(
      '<div><p>Safe</p><script>alert(1)</script><p>Still</p></div>',
    );
    assert.match(html, /Safe/);
    assert.match(html, /Still/);
    assert.doesNotMatch(html, /<script/i);
    assert.doesNotMatch(html, /alert\(1\)/);
  });

  it('removes onerror and onclick handlers', () => {
    const html = historyHtml.sanitizeHtml(
      '<p onclick="alert(1)">Click</p><img src="https://cdn.example.com/ok.png" onerror="alert(2)" alt="ok">',
    );
    assert.doesNotMatch(html, /onclick/i);
    assert.doesNotMatch(html, /onerror/i);
    assert.doesNotMatch(html, /alert\(/);
    assert.match(html, /Click/);
  });

  it('rejects javascript: and data: URLs on links and images', () => {
    const html = historyHtml.sanitizeHtml(
      '<a href="javascript:alert(1)">js</a>' +
        '<a href="JAVASCRIPT:alert(2)">js2</a>' +
        '<a href="data:text/html,<script>alert(3)</script>">data</a>' +
        '<img src="javascript:alert(4)">' +
        '<img src="data:image/svg+xml,<svg onload=alert(5)>" alt="x">',
    );
    assert.doesNotMatch(html, /javascript:/i);
    assert.doesNotMatch(html, /data:/i);
    assert.doesNotMatch(html, /alert\(/);
  });

  it('removes iframe, object, embed, and forms', () => {
    const html = historyHtml.sanitizeHtml(
      '<p>Body</p><iframe src="https://evil.example"></iframe>' +
        '<object data="https://evil.example"></object>' +
        '<embed src="https://evil.example">' +
        '<form action="https://evil.example"><input name="x"></form>',
    );
    assert.match(html, /Body/);
    assert.doesNotMatch(html, /<iframe/i);
    assert.doesNotMatch(html, /<object/i);
    assert.doesNotMatch(html, /<embed/i);
    assert.doesNotMatch(html, /<form/i);
    assert.doesNotMatch(html, /<input/i);
  });

  it('rejects malicious nested HTML while keeping surrounding text', () => {
    const html = historyHtml.sanitizeHtml(
      '<div><svg/onload=alert(1)><p>Hi</p><img src=x onerror=alert(2)><iframe src="javascript:alert(3)"></iframe></div>',
    );
    assert.match(html, /Hi/);
    assert.doesNotMatch(html, /<svg/i);
    assert.doesNotMatch(html, /onload/i);
    assert.doesNotMatch(html, /onerror/i);
    assert.doesNotMatch(html, /<iframe/i);
    assert.doesNotMatch(html, /javascript:/i);
    assert.doesNotMatch(html, /alert\(/);
  });

  it('keeps safe http/https/mailto links with rel attributes and drops javascript links', () => {
    const parsed = historyHtml.parseEmailContent(
      'Hello',
      '<p><a href="https://investhome.example/offer">Offer</a> ' +
        '<a href="mailto:hello@investhome.example">Mail</a> ' +
        '<a href="javascript:alert(1)">Bad</a></p>',
    );
    assert.match(parsed.html, /href="https:\/\/investhome\.example\/offer\/?"/);
    assert.match(parsed.html, /rel="noopener noreferrer nofollow"/);
    assert.match(parsed.html, /target="_blank"/);
    assert.match(parsed.html, /mailto:hello@investhome\.example/);
    assert.doesNotMatch(parsed.html, /javascript:/i);
    assert.equal(
      parsed.links.some((item) => String(item.href).includes('https://investhome.example/offer')),
      true,
    );
    assert.equal(
      parsed.links.some((item) => item.href.startsWith('mailto:hello@investhome.example')),
      true,
    );
    assert.equal(parsed.links.some((item) => /javascript:/i.test(item.href)), false);
  });

  it('strips tracking pixels and data/javascript image payloads', () => {
    const html = historyHtml.sanitizeHtml(
      '<p>News</p>' +
        '<img src="https://cdn.example.com/pixel.gif" width="1" height="1" alt="">' +
        '<img src="https://doubleclick.net/track.gif" alt="t">' +
        '<img src="https://cdn.example.com/hero.jpg" alt="hero">',
    );
    assert.match(html, /News/);
    assert.match(html, /hero\.jpg/);
    assert.doesNotMatch(html, /pixel\.gif/);
    assert.doesNotMatch(html, /doubleclick/);
  });

  it('uses DOMPurify before dangerouslySetInnerHTML and leaves CSP intact', () => {
    const history = read('src/workspaces/crm/contact-card/history-html.ts');
    const emailView = read('src/workspaces/crm/contact-card/crm-email-view.tsx');
    const activity = read('src/app/workspaces/crm/_components/activity-detail-panel.tsx');
    const csp = read('src/lib/security/security-headers.ts');
    const pkg = read('package.json');

    assert.match(history, /isomorphic-dompurify/);
    assert.match(history, /DOMPurify\.sanitize/);
    assert.match(history, /sanitizeEmailHtmlFragment/);
    assert.match(emailView, /sanitizeHtml\(/);
    assert.match(emailView, /dangerouslySetInnerHTML=\{\{ __html: html \}\}/);
    assert.match(activity, /sanitizeHtml\(/);
    assert.match(activity, /dangerouslySetInnerHTML=\{\{ __html: html \}\}/);
    assert.match(pkg, /isomorphic-dompurify/);
    assert.match(csp, /script-src \$\{scriptSrc\}/);
    assert.match(csp, /img-src 'self' blob: data:/);
    assert.match(csp, /object-src 'none'/);
    assert.match(csp, /style-src 'self' 'unsafe-inline'/);
    assert.doesNotMatch(csp, /script-src 'unsafe-inline'/);
  });
});
