/**
 * CRM quality package 2: unsaved drawers, save errors, leads next task, table sort/paging.
 * Run: node --test src/lib/crm/__tests__/crm-quality-package-2.test.mjs
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
const tasks = read('src/app/workspaces/crm/tasks/_components/crm-tasks-workspace.tsx')
const notes = read('src/app/workspaces/crm/notes/_components/crm-notes-workspace.tsx')
const contact = read('src/workspaces/crm/contact-card/unified-contact-card.tsx')
const people = read('src/app/workspaces/crm/contacts/_components/people-workspace.tsx')
const companies = read('src/app/workspaces/crm/companies/_components/companies-workspace.tsx')
const companyForm = read('src/app/workspaces/crm/_components/crm-company-form.tsx')
const leadsApi = read('src/workspaces/crm/api/crm-leads.ts')
const helper = read('src/lib/crm/unsaved-form.ts')

test('dirty lead drawer confirms, a clean close does not, and a failed save stays in the form', () => {
  assert.match(leads, /leadFormDirty/)
  assert.match(leads, /confirmDiscardUnsaved\(locale === 'tr'\)/)
  assert.match(leads, /onClick=\{requestCloseDrawer\}/)
  assert.match(leads, /setFormError\(saveFailedMessage\(locale === 'tr'\)\)/)
  assert.match(leads, /data-testid="crm-leads-form-error"/)
  assert.match(leads, /disabled=\{saving\}/)
  assert.match(helper, /window\.confirm/)
  assert.doesNotMatch(leads, /beforeunload/)
})

test('task and note drawers confirm when dirty and keep a failed save open', () => {
  assert.match(tasks, /taskFormDirty/)
  assert.match(tasks, /confirmDiscardUnsaved\(locale\.startsWith\('tr'\)\)/)
  assert.match(tasks, /onClose=\{requestClose\}/)
  assert.match(tasks, /setFormError\(saveFailedMessage\(locale\.startsWith\('tr'\)\)\)/)
  assert.match(tasks, /data-testid="crm-tasks-form-error"/)
  assert.match(tasks, /disabled=\{saving \|\| !form\.title\.trim\(\)\}/)
  assert.match(notes, /noteFormDirty/)
  assert.match(notes, /confirmDiscardUnsaved\(locale\.startsWith\('tr'\)\)/)
  assert.match(notes, /onClose=\{requestClose\}/)
  assert.match(notes, /data-testid="crm-notes-form-error"/)
  assert.match(notes, /saveFailedMessage\(locale\.startsWith\('tr'\)\)/)
  assert.match(notes, /disabled=\{saving \|\| !form\.body\.trim\(\) \|\| !form\.contactId\}/)
  assert.doesNotMatch(tasks, /beforeunload/)
  assert.doesNotMatch(notes, /beforeunload/)
})

test('contact edit confirms before discard and failed saves stay on the edit panel', () => {
  assert.match(contact, /const editDirty =/)
  assert.match(contact, /confirmDiscardUnsaved\(!locale\.startsWith\('en'\)\)/)
  assert.match(contact, /requestCloseEdit\(null\)/)
  assert.match(contact, /return t\.saveError/)
  assert.match(contact, /data-testid="contact-edit-error"/)
  assert.match(contact, /disabled=\{actionMutation\.isPending\}/)
  assert.match(contact, /setPanel\(null\)/)
  assert.doesNotMatch(contact, /return message;/)
})

test('leads next task column is removed because the list payload has no task field', () => {
  assert.doesNotMatch(leads, /<th>\{t\.nextTask\}<\/th>/)
  assert.doesNotMatch(leads, /<td>\{t\.none\}<\/td>\s*<td>\{formatWhen\(item\.created_at/)
  const listType = leadsApi.slice(leadsApi.indexOf('export type CrmLeadListResponse'), leadsApi.indexOf('export type CrmLeadWrite'))
  assert.doesNotMatch(listType, /next_task|next_action/)
})

test('people and companies sort through the server query, and leads does not invent a sort', () => {
  assert.match(people, /sort_by: sortBy/)
  assert.match(people, /sort_dir: sortDir/)
  assert.match(people, /toggleSort\('display_name', 'asc'\)/)
  assert.match(people, /toggleSort\('last_contact_at', 'desc'\)/)
  assert.doesNotMatch(people, /rows\.sort\(/)
  assert.match(companies, /sortBy,/)
  assert.match(companies, /sortOrder,/)
  assert.match(companies, /toggleSort\('display_name', 'asc'\)/)
  assert.match(companies, /toggleSort\('company_type', 'asc'\)/)
  assert.match(companies, /toggleSort\('status', 'asc'\)/)
  assert.doesNotMatch(companies, /rows\.sort\(/)
  assert.doesNotMatch(leads, /sort_by/)
  assert.doesNotMatch(leads, /items\.sort\(/)
})

test('pagination stays on the existing page query for people and companies', () => {
  assert.match(people, /page_size: pageSize/)
  assert.match(people, /PAGE_SIZES = \[10, 25, 50\]/)
  assert.match(companies, /pageSize/)
  assert.match(companies, /PAGE_SIZES/)
  assert.doesNotMatch(leads, /page_size/)
})

test('company create keeps the form open and shows a save error', () => {
  assert.match(companyForm, /setSaveError\(saveFailedMessage/)
  assert.match(companyForm, /data-testid="crm-company-form-error"/)
  assert.match(companyForm, /disabled=\{createMutation\.isPending\}/)
  assert.match(companyForm, /confirmDiscardUnsaved/)
  assert.doesNotMatch(companyForm, /if \(createMutation\.isPending\)/)
})
