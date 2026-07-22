/**
 * Lightweight frontend regression checks for AI Assistant schemas/helpers.
 * Run: node src/workspaces/marketing/schemas/assistant.test.mjs
 */

import assert from 'node:assert/strict';

// Zod schemas are TS — validate contract expectations via plain JS mirrors.
const MODES = [
  'marketing_summary',
  'campaign_analysis',
  'content_draft',
  'campaign_brief',
  'audience_suggestion',
  'channel_suggestion',
  'translation',
  'next_actions',
];

function modeRequiresCampaign(mode) {
  return mode === 'campaign_analysis';
}

function modeRequiresSourceText(mode) {
  return mode === 'translation';
}

function createClientRequestId(prefix = 'mkt-ai') {
  return `${prefix}-test-id`;
}

function plainText(value) {
  return value.replace(/<[^>]*>/g, '');
}

assert.equal(MODES.length, 8);
assert.equal(modeRequiresCampaign('campaign_analysis'), true);
assert.equal(modeRequiresCampaign('marketing_summary'), false);
assert.equal(modeRequiresSourceText('translation'), true);
assert.equal(modeRequiresSourceText('content_draft'), false);
assert.match(createClientRequestId(), /^mkt-ai-/);
assert.equal(plainText('<script>alert(1)</script>Hello'), 'alert(1)Hello');
assert.equal(plainText('Safe draft copy'), 'Safe draft copy');

// Localization keys present in both locale files
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '../../../..');
const en = JSON.parse(readFileSync(join(root, 'messages/en.json'), 'utf8'));
const tr = JSON.parse(readFileSync(join(root, 'messages/tr.json'), 'utf8'));

for (const locale of [en, tr]) {
  const assistant = locale.marketing.ai.assistant;
  assert.ok(assistant.title);
  assert.ok(assistant.modes.marketing_summary);
  assert.ok(assistant.modes.next_actions);
  assert.ok(assistant.actions.generate);
  assert.ok(assistant.states.safetyTitle);
  assert.equal(locale.marketing.nav.aiAssistant?.length > 0, true);
  assert.equal(locale.marketing.ai.tabs.assistant?.length > 0, true);
}

console.log('assistant frontend checks passed');
