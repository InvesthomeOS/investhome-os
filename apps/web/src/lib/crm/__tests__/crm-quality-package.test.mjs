/**
 * CRM quality package: journey fixture, pipeline/leads errors, permissions, settings labels.
 * Run: node --test src/lib/crm/__tests__/crm-quality-package.test.mjs
 */

import assert from 'node:assert/strict'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

const here = dirname(fileURLToPath(import.meta.url))
const webRoot = join(here, '../../../..')

function read(rel) {
  return readFileSync(join(webRoot, rel), 'utf8')
}

function pages(dir, found = []) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) pages(path, found)
    else if (name === 'page.tsx') found.push(path)
  }
  return found
}

const journeyPage = read('src/app/workspaces/crm/contacts/[contactId]/journey/page.tsx')
const pipeline = read('src/app/workspaces/crm/pipeline/_components/crm-pipeline-live-workspace.tsx')
const leads = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx')
const people = read('src/app/workspaces/crm/contacts/_components/people-workspace.tsx')
const createContact = read('src/app/workspaces/crm/contacts/new/page.tsx')
const card = read('src/workspaces/crm/contact-card/unified-contact-card.tsx')
const settings = read('src/app/workspaces/crm/settings/_components/crm-settings-live-workspace.tsx')

test('no live CRM page renders fixture journey data', () => {
  const livePages = pages(join(webRoot, 'src/app/workspaces/crm'))
  for (const page of livePages) {
    const source = readFileSync(page, 'utf8')
    assert.equal(source.includes('JOURNEY_TIMELINE_EVENTS'), false, page)
    assert.equal(source.includes('North Towers'), false, page)
    assert.equal(source.includes('contact-journey-workspace'), false, page)
  }
  assert.match(journeyPage, /Yolculuk geçmişi burada yok/)
  assert.match(journeyPage, /kişi kartındadır/)
})

test('pipeline and leads failures are errors, and an empty pipeline stays empty', () => {
  assert.match(pipeline, /title=\{t\.loadErrorTitle\}/)
  assert.match(pipeline, /message=\{t\.loadError\}/)
  assert.match(pipeline, /listQuery\.refetch/)
  assert.match(pipeline, /loadError: 'Kayıtlar alınamadı\. Yeniden deneyin\.'/)
  assert.doesNotMatch(pipeline, /isError[\s\S]{0,180}message=\{t\.emptyBody\}/)
  assert.match(pipeline, /const activeEmpty = !stage && items\.length === 0/)
  assert.match(pipeline, /data-testid="crm-pipeline-empty"/)
  assert.match(leads, /title=\{t\.loadErrorTitle\}/)
  assert.match(leads, /message=\{t\.loadError\}/)
  assert.match(leads, /listQuery\.refetch/)
  assert.match(leads, /loadErrorTitle: 'Leadler yüklenemedi'/)
  assert.doesNotMatch(leads, /isError[\s\S]{0,180}message=\{t\.emptyBody\}/)
})

test('pipeline reuses the leads stage system and explains a Sales Closing drop', () => {
  assert.match(pipeline, /crm-ops-kanban__col is-\$\{column\}/)
  assert.match(pipeline, /crm-ops-kanban__dot/)
  assert.match(pipeline, /dragOverStage === column \? ' is-drop'/)
  assert.match(pipeline, /t\.emptyColumn/)
  assert.match(pipeline, /event\.preventDefault\(\)/)
  assert.match(pipeline, /showToast\(t\.convertBlocked\)/)
  assert.match(pipeline, /setStageError\(t\.stageFailed\)/)
  assert.match(pipeline, /data-testid="crm-pipeline-stage-error"/)
  assert.match(read('src/app/workspaces/crm/pipeline/page.tsx'), /leads-ops\.css/)
})

test('create and assign-owner follow the API permissions', () => {
  assert.match(people, /\{canCreate \? \([\s\S]*data-testid="crm-people-new"/)
  assert.match(createContact, /!canCreate/)
  assert.match(createContact, /crm\.create/)
  assert.match(createContact, /canCreate \? \(/)
  assert.match(card, /const canTransferOwnership = has\('transfer_ownership'\)/)
  assert.match(card, /data-testid="contact-assign-owner"/)
  assert.match(card, /panel === 'assign' && canTransferOwnership/)
  assert.doesNotMatch(card, /<button type="button" onClick=\{\(\) => togglePanel\('assign'\)\}>/)
})

test('settings rows no longer use a dash for navigation-only configuration', () => {
  assert.match(settings, /pipelineValue: 'Pipeline ekranından yönetilir'/)
  assert.match(settings, /opportunityValue: 'Anlaşmalar ekranında görüntülenir'/)
  assert.match(settings, /activityValue: 'İletişim ekranından yönetilir'/)
  assert.match(settings, /taskValue: 'Görevler ekranından yönetilir'/)
  assert.match(settings, /value: copy\.pipelineValue/)
  assert.doesNotMatch(settings, /title: copy\.pipeline, value: copy\.none/)
  assert.doesNotMatch(settings, /title: copy\.taskTypes, value: copy\.none/)
})
