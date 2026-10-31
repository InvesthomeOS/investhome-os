/**
 * CRM quality package 7: agreement board totals come from the server.
 * Run: node --test src/lib/crm/__tests__/crm-quality-package-7.test.mjs
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

const agreements = read('src/app/workspaces/crm/agreements/_components/agreements-workspace.tsx')
const kanban = read('src/app/workspaces/crm/agreements/_components/agreements-kanban.tsx')
const agreementApi = read('src/workspaces/crm/api/agreements.ts')
const agreementList = read('src/app/workspaces/crm/agreements/_components/agreements-list.tsx')

test('board totals are not aggregated from a fixed client page', () => {
  assert.match(agreements, /fetchAgreementBoard\(/)
  assert.match(agreementApi, /\/crm\/agreements\/board/)
  assert.match(agreementApi, /\/crm\/agreements\/board\/cards/)
  assert.doesNotMatch(agreements, /page_size:\s*200/)
  assert.doesNotMatch(agreements, /baseItems/)
  assert.doesNotMatch(agreements, /kanbanColumns\(/)
  assert.doesNotMatch(agreements, /visibleItems/)
  assert.match(kanban, /column\.total/)
  assert.match(kanban, /onLoadMore\(column\.stage\)/)
  assert.match(kanban, /onClick=\{\(\) => onOpen\(row\)\}/)
  assert.doesNotMatch(kanban, /kanbanColumns\(/)
  assert.doesNotMatch(kanban, /cards\.length/)
})

test('the paged list from package 6 stays on the server', () => {
  assert.match(agreements, /sort_by: listSort/)
  assert.match(agreements, /page_size: listPageSize/)
  assert.match(agreements, /items=\{listQuery\.data\?\.items/)
  assert.match(agreements, /openPurchase/)
  assert.match(agreementList, /data-testid="agreements-column-picker"/)
  assert.match(agreementList, /onOpen\(row\)/)
  assert.doesNotMatch(agreementList, /page_size:\s*200/)
})
