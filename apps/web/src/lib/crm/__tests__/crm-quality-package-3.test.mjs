/**
 * CRM quality package 3: filter URLs, dead search routes, communication tools, rail cleanup.
 * Run: node --test src/lib/crm/__tests__/crm-quality-package-3.test.mjs
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

const people = read('src/app/workspaces/crm/contacts/_components/people-workspace.tsx')
const companies = read('src/app/workspaces/crm/companies/_components/companies-workspace.tsx')
const notes = read('src/app/workspaces/crm/notes/_components/crm-notes-workspace.tsx')
const tasks = read('src/app/workspaces/crm/tasks/_components/crm-tasks-workspace.tsx')
const relationships = read('src/app/workspaces/crm/relationships/_components/relationships-workspace.tsx')
const leads = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx')
const pipeline = read('src/app/workspaces/crm/pipeline/_components/crm-pipeline-live-workspace.tsx')
const listQuery = read('src/lib/crm/list-query.ts')
const searchPage = read('src/app/workspaces/crm/search/page.tsx')
const advancedPage = read('src/app/workspaces/crm/search/advanced/page.tsx')
const savedPage = read('src/app/workspaces/crm/search/saved/page.tsx')
const searchWorkspace = read('src/app/workspaces/crm/search/_components/search-workspace.tsx')
const palette = read('src/app/workspaces/crm/search/_components/crm-search-palette.tsx')
const globalSearch = read('src/lib/search/global-search-context.tsx')
const header = read('src/app/workspaces/crm/_components/crm-header.tsx')
const nav = read('src/workspaces/crm/types.ts')
const sidebar = read('src/app/workspaces/crm/_components/crm-sidebar.tsx')
const communication = read('src/app/workspaces/crm/communication/_components/crm-communication-live-workspace.tsx')
const commSidebar = read('src/app/workspaces/crm/communication/_components/communication-sidebar.tsx')
const sequences = read('src/app/workspaces/crm/communication/_components/sequences-view.tsx')
const preferences = read('src/app/workspaces/crm/communication/_components/preferences-view.tsx')
const calls = read('src/app/workspaces/crm/communication/_components/calls-view.tsx')
const meetings = read('src/app/workspaces/crm/communication/_components/meetings-view.tsx')
const templates = read('src/app/workspaces/crm/communication/_components/templates-view.tsx')
const analytics = read('src/app/workspaces/crm/communication/_components/analytics-view.tsx')

test('people filters are read from and written to the URL', () => {
  assert.match(people, /useDebouncedQueryParam\('q'/)
  assert.match(people, /searchParams\.get\('category'\)/)
  assert.match(people, /searchParams\.get\('owner'\)/)
  assert.match(people, /patch\(\{ category: event\.target\.value, page: null \}\)/)
  assert.match(listQuery, /router\.replace/)
  assert.doesNotMatch(people, /selectedId: searchParams/)
})

test('companies filters are read from and written to the URL', () => {
  assert.match(companies, /useDebouncedQueryParam\('q'/)
  assert.match(companies, /searchParams\.get\('status'\)/)
  assert.match(companies, /searchParams\.get\('country'\)/)
  assert.match(companies, /patch\(\{ status: event\.target\.value, page: null \}\)/)
  assert.match(companies, /Şirketler yüklenemedi\. Yeniden deneyin\./)
  assert.match(companies, /listQuery\.refetch\(\)/)
  assert.match(companies, /rows\.length === 0/)
  assert.doesNotMatch(companies, /listQuery\.error\.message/)
})

test('notes filters are read from and written to the URL', () => {
  assert.match(notes, /useDebouncedQueryParam\('q'/)
  assert.match(notes, /searchParams\.get\('owner'\)/)
  assert.match(notes, /searchParams\.get\('project'\)/)
  assert.match(notes, /LIST_SEARCH_DEBOUNCE_MS/)
  assert.match(notes, /setSelectedId/)
  assert.doesNotMatch(notes, /searchParams\.get\('mode'\)/)
})

test('tasks filters survive in the URL and Clear returns the default active status', () => {
  assert.match(tasks, /useDebouncedQueryParam\('q'/)
  assert.match(tasks, /taskStatusFromQuery\(searchParams\.get\('status'\)\)/)
  assert.match(tasks, /if \(value == null\) return 'active'/)
  assert.match(tasks, /const TASK_QUERY_DEFAULTS = \{ status: 'active'/)
  assert.match(tasks, /status: null/)
  assert.doesNotMatch(tasks, /setFilters\(EMPTY_FILTERS\)/)
})

test('relationships filters survive in the URL and Clear restores the default list', () => {
  assert.match(relationships, /useDebouncedQueryParam\('q'/)
  assert.match(relationships, /searchParams\.get\('type'\)/)
  assert.match(relationships, /RELATIONSHIP_QUERY_DEFAULTS = \{ tab: 'all'/)
  assert.match(relationships, /data-testid="crm-relationships-clear"/)
  assert.match(relationships, /tab: null, type: null, category: null, project: null, status: null, owner: null, page: null/)
})

test('leads and pipeline search debounce instead of waiting for blur or Enter', () => {
  assert.match(leads, /useDebouncedQueryParam\('q'\)/)
  assert.match(pipeline, /useDebouncedQueryParam\('q'\)/)
  assert.match(listQuery, /LIST_SEARCH_DEBOUNCE_MS = 300/)
  assert.match(listQuery, /window\.setTimeout/)
  assert.doesNotMatch(leads, /onBlur=\{\(\) => setSearch/)
  assert.doesNotMatch(pipeline, /onBlur=\{\(\) => setSearch/)
  assert.match(leads, /searchParams\.get\('stage'\)/)
  assert.match(pipeline, /searchParams\.get\('stage'\)/)
})

test('dead search routes do not redirect to the dashboard', () => {
  for (const source of [searchPage, advancedPage, savedPage]) {
    assert.match(source, /SearchUnavailable/)
    assert.doesNotMatch(source, /redirect\('\/workspaces\/crm\/dashboard'\)/)
  }
  assert.match(read('src/app/workspaces/crm/search/_components/search-unavailable.tsx'), /data-testid="crm-search-unavailable"/)
  assert.match(read('src/app/workspaces/crm/search/_components/search-unavailable.tsx'), /Ctrl\+K/)
})

test('search navigation does not expose unfinished advanced or saved search', () => {
  assert.doesNotMatch(nav, /\/workspaces\/crm\/search\/advanced/)
  assert.doesNotMatch(nav, /\/workspaces\/crm\/search\/saved/)
  assert.doesNotMatch(searchWorkspace, /\/workspaces\/crm\/search\/advanced/)
  assert.doesNotMatch(searchWorkspace, /\/workspaces\/crm\/search\/saved/)
  assert.doesNotMatch(sidebar, /\/workspaces\/crm\/search/)
})

test('command palette shortcut behavior is unchanged', () => {
  assert.match(header, /<CrmSearchPalette \/>/)
  assert.match(header, /useCrmSearchShortcuts\(\)/)
  assert.match(palette, /const modifier = isMac \? event\.metaKey : event\.ctrlKey/)
  assert.match(globalSearch, /modifier && event\.key\.toLowerCase\(\) === 'k'/)
})

test('unmatched and working communication tools are reachable from Communication', () => {
  assert.match(communication, /data-testid="crm-comm-tools"/)
  assert.match(communication, /data-testid="crm-comm-link-unmatched"/)
  assert.match(communication, /data-testid="crm-comm-link-templates"/)
  assert.match(communication, /data-testid="crm-comm-link-signatures"/)
  assert.match(communication, /data-testid="crm-comm-link-calls"/)
  assert.match(communication, /data-testid="crm-comm-link-meetings"/)
  assert.match(communication, /data-testid="crm-comm-unmatched-tab"/)
})

test('sequences are labeled unavailable and preferences hide the UUID workflow', () => {
  assert.match(communication, /data-testid="crm-comm-link-sequences"/)
  assert.match(communication, /tSequences\('architectureNote'\)/)
  assert.match(sequences, /data-testid="crm-sequences-unavailable"/)
  assert.match(sequences, /t\('architectureNote'\)/)
  assert.doesNotMatch(sequences, /createSequence/)
  assert.doesNotMatch(sequences, /createMutation/)
  assert.match(preferences, /data-testid="crm-preferences-unavailable"/)
  assert.doesNotMatch(preferences, /placeholder="UUID"/)
  assert.doesNotMatch(communication, /communication\/preferences/)
  assert.doesNotMatch(commSidebar, /communication\/preferences/)
})

test('CRM rail no longer checks ui-preview paths', () => {
  assert.doesNotMatch(sidebar, /\/ui-preview\/crm\//)
  assert.doesNotMatch(sidebar, /\/ui-preview\/admin/)
  assert.match(sidebar, /pathname === item\.href/)
})

test('existing permissions still gate the affected communication pages', () => {
  assert.match(communication, /if \(!canViewCommunications\)/)
  assert.match(communication, /has\('view_analytics'\)/)
  assert.match(calls, /if \(!canViewCommunications\)/)
  assert.match(meetings, /if \(!canViewCommunications\)/)
  assert.match(templates, /if \(!canViewCommunications\)/)
  assert.match(sequences, /if \(!canViewCommunications\)/)
  assert.match(preferences, /if \(!canViewCommunications\)/)
  assert.match(analytics, /if \(!canViewAnalytics\)/)
  assert.doesNotMatch(communication, /feedQuery\.error\.message/)
})
