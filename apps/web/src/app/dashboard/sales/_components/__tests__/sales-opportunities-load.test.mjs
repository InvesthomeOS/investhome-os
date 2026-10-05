/**
 * Sales opportunities fetch must not loop on party-name resolution or translator identity.
 * Run: node --test src/app/dashboard/sales/_components/__tests__/sales-opportunities-load.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const workspace = readFileSync(join(here, '../sales-workspace.tsx'), 'utf8');
const helpers = readFileSync(join(here, '../sales-opportunities-load.ts'), 'utf8');

function salesOpportunitiesRequestKey(filters) {
  return [
    filters.view,
    filters.search.trim(),
    filters.stage,
    filters.assigned_sales_user_id,
    filters.party_id,
    filters.lead_id,
    filters.priority,
    filters.include_archived ? '1' : '0',
    filters.sort_by,
    filters.sort_dir,
    String(filters.page),
    String(filters.page_size),
  ].join('|');
}

function shouldShowSalesSkeleton(loading, itemCount) {
  return loading && itemCount === 0;
}

function mergePartyNames(current, incoming) {
  let changed = false;
  const next = { ...current };
  for (const [id, name] of Object.entries(incoming)) {
    if (!id || !name || next[id] === name) continue;
    next[id] = name;
    changed = true;
  }
  return { next, changed };
}

const FILTER = {
  search: '',
  stage: '',
  assigned_sales_user_id: '',
  party_id: '',
  lead_id: '',
  priority: '',
  include_archived: false,
  sort_by: 'updated_at',
  sort_dir: 'desc',
  page: 1,
  page_size: 20,
  view: 'pipeline',
};

describe('sales opportunities loading loop', () => {
  it('keeps the same request key when filter objects are recreated with the same values', () => {
    assert.equal(salesOpportunitiesRequestKey(FILTER), salesOpportunitiesRequestKey({ ...FILTER }));
  });

  it('changes the request key only when a real filter changes', () => {
    assert.notEqual(
      salesOpportunitiesRequestKey({ ...FILTER, view: 'list' }),
      salesOpportunitiesRequestKey(FILTER),
    );
  });

  it('shows skeleton only while the first load has no rows', () => {
    assert.equal(shouldShowSalesSkeleton(true, 0), true);
    assert.equal(shouldShowSalesSkeleton(true, 3), false);
    assert.equal(shouldShowSalesSkeleton(false, 0), false);
  });

  it('does not treat cached party names as a state change', () => {
    assert.equal(mergePartyNames({ p1: 'Ayşe' }, { p1: 'Ayşe' }).changed, false);
  });

  it('workspace fetch effect is stable and skips redundant party-name writes', () => {
    assert.match(helpers, /export function salesOpportunitiesRequestKey/);
    assert.match(helpers, /export function shouldShowSalesSkeleton/);
    assert.match(workspace, /if \(missing\.length === 0\) return;/);
    assert.match(workspace, /if \(!merged\.changed\) return;/);
    assert.match(workspace, /if \(seq === loadSeqRef\.current\) \{\s*setLoading\(false\);/s);
    const resolveBlock = workspace.slice(
      workspace.indexOf('const resolvePartyNames'),
      workspace.indexOf('const loadOpportunities'),
    );
    assert.match(resolveBlock, /\}, \[\]\);/);
    assert.doesNotMatch(resolveBlock, /\[partyNames\]/);
    const loadBlock = workspace.slice(
      workspace.indexOf('const loadOpportunities'),
      workspace.indexOf('void loadKpis()'),
    );
    assert.doesNotMatch(loadBlock, /\[resolvePartyNames, t\]/);
    assert.match(loadBlock, /\[resolvePartyNames\],/);
    assert.match(workspace, /\[appliedFilters, canView, loadOpportunities\]/);
    assert.doesNotMatch(
      workspace,
      /setPartyNames\(\(current\) => \(\{ \.\.\.current, \.\.\.next \}\)\)/,
    );
  });
});
