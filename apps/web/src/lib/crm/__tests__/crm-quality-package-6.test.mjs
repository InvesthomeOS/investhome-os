/**
 * CRM quality package 6: tasks and agreements sort and page on the server.
 * Run: node --test src/lib/crm/__tests__/crm-quality-package-6.test.mjs
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

const tasks = read('src/app/workspaces/crm/tasks/_components/crm-tasks-workspace.tsx')
const taskApi = read('src/workspaces/crm/api/activities.ts')
const agreements = read('src/app/workspaces/crm/agreements/_components/agreements-workspace.tsx')
const agreementList = read('src/app/workspaces/crm/agreements/_components/agreements-list.tsx')
const agreementApi = read('src/workspaces/crm/api/agreements.ts')
const people = read('src/app/workspaces/crm/contacts/_components/people-workspace.tsx')
const companies = read('src/app/workspaces/crm/companies/_components/companies-workspace.tsx')
const activities = read('src/app/workspaces/crm/activities/_components/crm-activities-workspace.tsx')
const notes = read('src/app/workspaces/crm/notes/_components/crm-notes-workspace.tsx')
const relationships = read('src/app/workspaces/crm/relationships/_components/relationships-workspace.tsx')
const leads = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx')

test('tasks send sort to the API and do not reorder the loaded page', () => {
  assert.match(tasks, /params\.sort_by = TASK_SORT_API\[sortKey\]/)
  assert.match(tasks, /params\.sort_dir = sortDir/)
  assert.match(tasks, /patch\(\{ sort: key, dir: nextDir, page: null \}\)/)
  assert.match(taskApi, /sort_by: params\.sort_by/)
  assert.doesNotMatch(tasks, /rows\.sort\(/)
  assert.match(tasks, /\['person', 'is-person', false\]/)
  assert.match(tasks, /\['project', 'is-project', false\]/)
  assert.match(tasks, /\['owner', 'is-owner', false\]/)
})

test('agreements list uses the paged API result', () => {
  assert.match(agreements, /sort_by: listSort/)
  assert.match(agreements, /page_size: listPageSize/)
  assert.match(agreements, /items=\{listQuery\.data\?\.items/)
  assert.match(agreementApi, /search\.set\('sort_by', params\.sort_by\)/)
  assert.match(agreementApi, /search\.set\('q', params\.q\)/)
  assert.doesNotMatch(agreementList, /items\.sort\(/)
  assert.doesNotMatch(agreementList, /sorted\.slice/)
  assert.doesNotMatch(agreementList, /page_size:\s*200/)
  assert.match(agreementList, /data-testid="agreements-column-picker"/)
  assert.match(agreementList, /onOpen\(row\)/)
  assert.match(agreementList, /openPurchase/)
})

test('other live tables do not sort a partial page in the browser', () => {
  assert.match(people, /sort_by: sortBy/)
  assert.match(companies, /toggleSort\('display_name'/)
  assert.match(activities, /sort_by: 'created_at'/)
  assert.doesNotMatch(activities, /\.sort\(/)
  assert.doesNotMatch(notes, /\.sort\(/)
  assert.doesNotMatch(leads, /toggleSort/)
  assert.match(relationships, /sort_by: 'updated_at'/)
  assert.doesNotMatch(relationships, /\.sort\(/)
})
