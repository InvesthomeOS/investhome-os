/**
 * CRM quality package 5: tables, dashboard, mobile drawers, pipeline filter empty, dead demos, rail icons.
 * Run: node --test src/lib/crm/__tests__/crm-quality-package-5.test.mjs
 */

import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

const here = dirname(fileURLToPath(import.meta.url))
const webRoot = join(here, '../../../..')

function read(rel) {
  return readFileSync(join(webRoot, rel), 'utf8')
}

const leads = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx')
const people = read('src/app/workspaces/crm/contacts/_components/people-workspace.tsx')
const companies = read('src/app/workspaces/crm/companies/_components/companies-workspace.tsx')
const activities = read('src/app/workspaces/crm/activities/_components/crm-activities-workspace.tsx')
const notes = read('src/app/workspaces/crm/notes/_components/crm-notes-workspace.tsx')
const relationships = read('src/app/workspaces/crm/relationships/_components/relationships-workspace.tsx')
const tasks = read('src/app/workspaces/crm/tasks/_components/crm-tasks-workspace.tsx')
const agreements = read('src/app/workspaces/crm/agreements/_components/agreements-list.tsx')
const leadsCss = read('src/app/workspaces/crm/leads/leads-ops.css')
const peopleCss = read('src/app/workspaces/crm/contacts/_components/people-workspace.css')
const companiesCss = read('src/app/workspaces/crm/companies/companies-ops.css')
const tasksCss = read('src/app/workspaces/crm/tasks/tasks-ops.css')
const agreementsCss = read('src/app/workspaces/crm/agreements/_components/agreements-workspace.css')
const activitiesCss = read('src/app/workspaces/crm/activities/activities.css')
const notesCss = read('src/app/workspaces/crm/notes/notes.css')
const relationshipsCss = read('src/app/workspaces/crm/relationships/_components/relationships-workspace.css')
const dashboard = read('src/app/workspaces/crm/dashboard/_components/crm-pano-live-workspace.tsx')
const pipeline = read('src/app/workspaces/crm/pipeline/_components/crm-pipeline-live-workspace.tsx')
const theme = read('src/app/workspaces/crm/crm-theme.css')
const contactCss = read('src/workspaces/crm/contact-card/contact-card.css')
const calendar = read('src/app/workspaces/crm/calendar/_components/crm-calendar-workspace.tsx')
const sidebar = read('src/app/workspaces/crm/_components/crm-sidebar.tsx')
const nav = read('src/workspaces/crm/types.ts')
const notesApi = read('src/workspaces/crm/api/activities.ts')

const removed = [
  'src/app/workspaces/crm/leads/_components/ds/leads-ds-workspace.tsx',
  'src/app/workspaces/crm/contacts/_components/ds/contacts-ds-workspace.tsx',
  'src/app/workspaces/crm/relationships/_components/ds/relationships-ds-workspace.tsx',
  'src/app/workspaces/crm/_components/g2/crm-pipeline-workspace.tsx',
  'src/app/workspaces/crm/_components/g2/crm-leads-workspace.tsx',
  'src/app/workspaces/crm/dashboard/_components/ds/crm-dashboard-ds-workspace.tsx',
  'src/app/workspaces/crm/communication/_components/communication-workspace.tsx',
  'src/app/workspaces/crm/search/_components/saved-searches-workspace.tsx',
  'src/app/workspaces/crm/files/_components/crm-files-workspace.tsx',
  'src/app/workspaces/crm/notes/_components/ds/notes-ds-workspace.tsx',
  'src/app/workspaces/crm/files/files-demo-data.ts',
]

test('desktop tables keep identity and action columns reachable while scrolling', () => {
  assert.match(leads, /data-testid="crm-leads-table"/)
  assert.match(leadsCss, /overflow: auto/)
  assert.match(leadsCss, /th:first-child/)
  assert.match(leadsCss, /th:last-child/)
  assert.match(peopleCss, /th:first-child/)
  assert.match(peopleCss, /th:last-child/)
  assert.match(peopleCss, /white-space: nowrap/)
  assert.match(companiesCss, /overflow-x: auto/)
  assert.match(companies, /toggleSort\('display_name'/)
  assert.match(people, /sort_by: sortBy/)
  assert.match(tasksCss, /td\.is-actions/)
  assert.match(tasksCss, /white-space: nowrap/)
  assert.match(tasks, /page_size: pageSize/)
  assert.match(agreementsCss, /td\.is-actions/)
  assert.match(agreementsCss, /overflow: auto/)
  assert.match(agreements, /className="is-actions"/)
  assert.match(activitiesCss, /overflow: auto/)
  assert.match(activitiesCss, /th:first-child/)
  assert.match(activities, /sort_by: 'created_at'/)
  assert.match(notesCss, /overflow-x: auto/)
  assert.match(notesCss, /th:first-child/)
  assert.match(relationshipsCss, /position: static/)
  assert.match(relationships, /crm-rel-table/)
  assert.match(relationships, /page_size: PAGE_SIZE/)
})

test('drawers stay inside the viewport and contact close remains available', () => {
  assert.match(theme, /\.crm-shell \.crm-ops-drawer/)
  assert.match(theme, /max-width: 100vw/)
  assert.match(theme, /\.crm-tasks__drawer/)
  assert.match(theme, /\.crm-comm-drawer/)
  assert.match(theme, /flex: 0 0 auto/)
  assert.match(contactCss, /max-width: 100vw/)
  assert.match(contactCss, /\.ih-drawer__close/)
  assert.match(theme, /\.crm-shell \.app-header/)
  assert.match(theme, /flex-wrap: wrap/)
})

test('pipeline empty columns distinguish a real empty stage from an active filter', () => {
  assert.match(pipeline, /filteredColumn: 'No leads match this filter\.'/)
  assert.match(pipeline, /filteredColumn: 'Bu filtreye uyan lead yok\.'/)
  assert.match(pipeline, /emptyColumn: 'No leads in this stage\.'/)
  assert.match(pipeline, /crm-pipeline-column-filtered-empty/)
  assert.match(pipeline, /crm-pipeline-column-empty/)
  assert.match(pipeline, /const filtersActive = Boolean/)
  assert.match(pipeline, /const columnCount = \(column: CrmLeadStage\) => grouped\[column\]\.length/)
  assert.match(pipeline, /const activeEmpty = !stage && items\.length === 0/)
})

test('dashboard draws project counts once and keeps KPI links', () => {
  assert.equal((dashboard.match(/data=\{projectChart\}/g) || []).length, 1)
  assert.doesNotMatch(dashboard, /CompactHorizontalBars/)
  assert.match(dashboard, /crm-pano-kpi-\$\{item\.key\}/)
  assert.match(dashboard, /href: '\/workspaces\/crm\/agreements'/)
  assert.match(dashboard, /href: '\/workspaces\/crm\/leads'/)
})

test('removed demo workspaces are not referenced by live routes', () => {
  for (const rel of removed) {
    assert.equal(existsSync(join(webRoot, rel)), false, rel)
  }
  assert.equal(existsSync(join(webRoot, 'src/app/workspaces/crm/search/_components/search-workspace.tsx')), true)
  assert.equal(existsSync(join(webRoot, 'src/app/workspaces/crm/contacts/_components/ds/contacts-ds.css')), true)
  const livePages = [
    'src/app/workspaces/crm/leads/page.tsx',
    'src/app/workspaces/crm/pipeline/page.tsx',
    'src/app/workspaces/crm/dashboard/page.tsx',
    'src/app/workspaces/crm/contacts/page.tsx',
    'src/app/workspaces/crm/relationships/page.tsx',
    'src/app/workspaces/crm/notes/page.tsx',
    'src/app/workspaces/crm/communication/page.tsx',
    'src/app/workspaces/crm/files/page.tsx',
    'src/app/workspaces/crm/search/page.tsx',
  ]
  for (const rel of livePages) {
    const source = read(rel)
    assert.doesNotMatch(source, /LeadsDsWorkspace|ContactsDsWorkspace|RelationshipsDsWorkspace|CrmPipelineWorkspace|CrmLeadsWorkspace|CrmDashboardDsWorkspace|CommunicationWorkspace|SavedSearchesWorkspace|CrmFilesWorkspace|NotesDsWorkspace/)
  }
  assert.match(read('src/app/workspaces/crm/leads/page.tsx'), /CrmLeadsLiveWorkspace/)
  assert.match(read('src/app/workspaces/crm/files/page.tsx'), /redirect\('\/workspaces\/crm\/documents'\)/)
})

test('CRM rail icons stay on the same routes', () => {
  assert.match(nav, /href: '\/workspaces\/crm\/notes', labelKey: 'nav\.notes'/)
  assert.match(nav, /href: '\/workspaces\/crm\/pipeline', labelKey: 'nav\.pipeline'/)
  assert.match(nav, /href: '\/workspaces\/crm\/reports', labelKey: 'nav\.reports'/)
  assert.match(nav, /href: '\/workspaces\/crm\/agreements', labelKey: 'nav\.agreements'/)
  assert.match(nav, /href: '\/workspaces\/crm\/documents', labelKey: 'nav\.documents'/)
  assert.match(sidebar, /'nav\.notes': 'empty'/)
  assert.match(sidebar, /'nav\.documents': 'documents'/)
  assert.match(sidebar, /'nav\.agreements': 'finance'/)
  assert.match(sidebar, /'nav\.pipeline': 'barChart'/)
  assert.match(sidebar, /'nav\.reports': 'sales'/)
  assert.match(sidebar, /href=\{item\.href as Route\}/)
})

test('notes stay create-only and say so', () => {
  assert.match(notes, /data-testid="crm-notes-immutable"/)
  assert.match(notes, /t\('immutable'\)/)
  assert.match(notes, /createNote\(/)
  assert.doesNotMatch(notes, /updateNote|editNote/)
  assert.match(notesApi, /\/crm\/notes'/)
  assert.doesNotMatch(notesApi, /\/crm\/notes\/\$\{/)
})

test('narrow calendar month uses the existing list and permissions stay put', () => {
  assert.match(calendar, /const monthAsList = view === 'month' && narrow/)
  assert.match(calendar, /data-testid=\{monthAsList \? 'crm-calendar-narrow-list' : 'crm-calendar-list'\}/)
  assert.match(calendar, /rangeForView\(view, cursor\)/)
  assert.match(leads, /canCreate/)
  assert.match(leads, /canUpdate/)
  assert.doesNotMatch(dashboard, /transfer_ownership/)
})
