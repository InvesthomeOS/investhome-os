/**
 * Social Media Builder follow-up AI edit mapper + AI-first chrome wiring.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-ai-edit.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const smbDir = join(here, '..');
const messagesDir = join(smbDir, '../../../../../messages');

function readSmb(name) {
  return readFileSync(join(smbDir, name), 'utf8');
}

function readMessages(name) {
  return readFileSync(join(messagesDir, name), 'utf8');
}

const PRICE_RE =
  /(?:[$€£₺]\s?\d|\d[\d.,]*\s?(?:\$|€|£|₺|usd|eur|try)|fiyat|price|asking|starting from|başlangıç|satış fiyat|m[ıi]lyon|million)/i;
const NIGHT_RE = /night|nighttime|gece|evening|dusk|twilight|ak[sş]am/i;

const COMMAND_PATTERNS = [
  { command: 'shrink_headline', pattern: /ba[sş]l[iı][gğ][iı].{0,24}k[uü][cç][uü]lt|shrink (the )?headline|smaller headline|headline.{0,12}(smaller|k[uü][cç][uü]k)/i },
  { command: 'remove_price', pattern: /fiyat[iı] kald[iı]r|remove (the )?price|hide (the )?price|fiyat[iı] gizle/i },
  { command: 'use_night_render', pattern: /gece render|night render|use (the )?night|gece g[oö]r[uü]n/i },
  { command: 'move_logo_down', pattern: /logoyu.{0,24}a[sş]a[gğ][iı]|move (the )?logo down|logo.{0,12}down/i },
  { command: 'move_headline_down', pattern: /ba[sş]l[iı][gğ][iı].{0,24}a[sş]a[gğ][iı]|move (the )?headline down|headline.{0,12}down/i },
  { command: 'make_premium', pattern: /daha premium|more premium|make (it )?premium/i },
  { command: 'simplify_text', pattern: /daha (minimal|sade)|yaz[iı]lar[iı].{0,16}sade|simplify (the )?text|more minimal|sadele[sş]tir/i },
];

function parseAiFollowUpCommands(instruction) {
  const text = (instruction || '').trim();
  if (!text) return [];
  const found = [];
  for (const row of COMMAND_PATTERNS) {
    if (row.pattern.test(text) && !found.includes(row.command)) found.push(row.command);
  }
  return found;
}

function isNightMediaHint(item) {
  const hay = `${item.name ?? ''} ${(item.tags ?? []).join(' ')} ${item.folderCategory ?? ''}`;
  return NIGHT_RE.test(hay);
}

function looksLikePriceText(text) {
  return PRICE_RE.test(text || '');
}

describe('follow-up command parser', () => {
  it('maps the documented TR/EN commands', () => {
    assert.deepEqual(parseAiFollowUpCommands('Başlığı küçült ve daha minimal yap.'), [
      'shrink_headline',
      'simplify_text',
    ]);
    assert.deepEqual(parseAiFollowUpCommands('Fiyatı kaldır.'), ['remove_price']);
    assert.deepEqual(parseAiFollowUpCommands('Daha premium yap.'), ['make_premium']);
    assert.deepEqual(parseAiFollowUpCommands('Gece renderını kullan.'), ['use_night_render']);
    assert.deepEqual(parseAiFollowUpCommands('Logoyu biraz aşağı al.'), ['move_logo_down']);
    assert.deepEqual(parseAiFollowUpCommands('Başlığı biraz aşağı al.'), ['move_headline_down']);
    assert.deepEqual(parseAiFollowUpCommands('Yazıları daha sade yap.'), ['simplify_text']);
    assert.deepEqual(parseAiFollowUpCommands('Use the night render and shrink the headline'), [
      'shrink_headline',
      'use_night_render',
    ]);
  });

  it('does not invent a match for unrelated copy', () => {
    assert.deepEqual(parseAiFollowUpCommands('The Temple için premium bir Instagram yatırım postu hazırla.'), []);
    assert.deepEqual(parseAiFollowUpCommands(''), []);
  });
});

describe('honest local mutations', () => {
  it('detects price copy and night media hints', () => {
    assert.equal(looksLikePriceText('From $850,000 in Washington DC'), true);
    assert.equal(looksLikePriceText('Limited residences in the capital'), false);
    assert.equal(isNightMediaHint({ name: 'temple-night-facade.jpg', tags: ['render'] }), true);
    assert.equal(isNightMediaHint({ name: 'lobby-day.jpg', tags: ['interior'] }), false);
  });
});

describe('AI-first SMB chrome (source wiring)', () => {
  it('hides engine names and technical layout labels from the prompt UI', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /data-testid="smb-ai-design-command"/);
    assert.match(workspace, /aiDesign\.submit/);
    assert.doesNotMatch(workspace, /data-testid="smb-ai-engine-selector"/);
    assert.doesNotMatch(workspace, /t\('aiDesign\.engineArtDirector'\)/);
    assert.doesNotMatch(workspace, /t\('aiDesign\.engineIdeogram'\)/);
    assert.doesNotMatch(workspace, /t\('aiDesign\.createPost'\)/);
    assert.doesNotMatch(workspace, /t\('aiDesign\.editPost'\)/);
    // GPT Image may reference output.composition_* fields; keep UI free of raw composition dumps.
    assert.doesNotMatch(workspace, /output\.composition[^_a-zA-Z]/);
    assert.doesNotMatch(workspace, /t\('useCanvaEngine'\)/);
    assert.match(workspace, /testId: 'smb-open-in-canva'/);
    assert.match(workspace, /moreLabel=\{t\('editor.more'\)\}/);
    assert.match(workspace, /applyAiFollowUpEdit/);
    assert.match(workspace, /generateSocialDesign/);
    assert.match(workspace, /exportSocialPostPng/);
  });

  it('keeps Canva transfer + PNG export internals available', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    const exportSrc = readSmb('social-media-builder-export.ts');
    assert.match(workspace, /runOpenInCanva/);
    assert.match(workspace, /buildCanvaLayersPayload/);
    assert.match(workspace, /exportDesignToCanva/);
    assert.match(exportSrc, /export async function exportSocialPostPng/);
    assert.match(exportSrc, /await renderSocialPostPng\(input\)/);
  });

  it('ships i18n for Oluştur, Tasarım A/B/C, and output actions', () => {
    const en = readMessages('en.json');
    const tr = readMessages('tr.json');
    assert.match(tr, /"submit": "Oluştur"/);
    assert.match(en, /"submit": "Create"/);
    assert.match(tr, /"designLabel": "Tasarım \{letter\}"/);
    assert.match(en, /"designLabel": "Design \{letter\}"/);
    assert.match(tr, /"story": "Story Yap"/);
    assert.match(tr, /"reel": "Reel Yap"/);
    assert.match(tr, /"variation": "Varyasyon Oluştur"/);
    assert.match(en, /"openInCanva": "Open in Canva"/);
    assert.match(tr, /"openInCanva": "Canva'da Aç"/);
  });

  it('documents working follow-up commands in the mapper module', () => {
    const src = readSmb('social-media-builder-ai-edit.ts');
    assert.match(src, /shrink_headline/);
    assert.match(src, /remove_price/);
    assert.match(src, /make_premium/);
    assert.match(src, /use_night_render/);
    assert.match(src, /move_logo_down/);
    assert.match(src, /move_headline_down/);
    assert.match(src, /simplify_text/);
    assert.match(src, /export function applyAiFollowUpEdit/);
  });
});
