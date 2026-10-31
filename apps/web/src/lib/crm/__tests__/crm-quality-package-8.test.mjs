/**
 * CRM quality package 8: lead totals are server aggregates, not a 500-row page.
 * Run: node --test src/lib/crm/__tests__/crm-quality-package-8.test.mjs
 */

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

const here = dirname(fileURLToPath(import.meta.url))
const webRoot = join(here, '../../../..')

function read(rel) {
  return readFileSync(join(webRoot, rel), 'utf8')
}

const leads = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx')
const pipeline = read('src/app/workspaces/crm/pipeline/_components/crm-pipeline-live-workspace.tsx')
const leadApi = read('src/workspaces/crm/api/crm-leads.ts')
const relationships = read('src/app/workspaces/crm/relationships/_components/relationships-workspace.tsx')
const calendar = read('src/app/workspaces/crm/calendar/_components/crm-calendar-workspace.tsx')

test('lead list and pipeline totals come from the server board', () => {
  assert.match(leadApi, /\/crm\/leads\/board/)
  assert.match(leadApi, /\/crm\/leads\/board\/cards/)
  assert.match(leads, /fetchCrmLeadBoard\(/)
  assert.match(pipeline, /fetchCrmLeadBoard\(/)
  assert.doesNotMatch(leads, /limit\(500\)/)
  assert.doesNotMatch(leads, /page_size/)
  assert.doesNotMatch(leads, /sort_by/)
  assert.doesNotMatch(leads, /items\.sort\(/)
  assert.match(leads, /data-testid="crm-leads-pager"/)
  assert.match(pipeline, /\?\.total \?\? 0/)
  assert.match(pipeline, /showToast\(t\.convertBlocked\)/)
})

test('relationship sort stays on real columns and calendar week collapses on a narrow screen', () => {
  assert.match(relationships, /sort_by: 'updated_at'/)
  assert.match(relationships, /toggleSort\('relationship_type', 'asc'\)/)
  assert.match(relationships, /toggleSort\('last_interaction_at', 'desc'\)/)
  assert.doesNotMatch(relationships, /\.sort\(/)
  assert.match(calendar, /const weekAsList = view === 'week' && narrow/)
  assert.match(calendar, /view === 'week' && !weekAsList/)
  assert.match(calendar, /monthAsList \|\| weekAsList/)
})
