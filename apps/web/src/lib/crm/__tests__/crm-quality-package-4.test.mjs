/**
 * CRM quality package 4: action permissions, company form, relationship create, historical correction.
 * Run: node --test src/lib/crm/__tests__/crm-quality-package-4.test.mjs
 */

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

const here = dirname(fileURLToPath(import.meta.url))
const webRoot = join(here, '../../../..')
const repoRoot = join(webRoot, '../..')

function read(rel) {
  return readFileSync(join(webRoot, rel), 'utf8')
}

function readRepo(rel) {
  return readFileSync(join(repoRoot, rel), 'utf8')
}

const leads = read('src/app/workspaces/crm/leads/_components/crm-leads-live-workspace.tsx')
const tags = read('src/app/workspaces/crm/tags/_components/crm-tags-live-workspace.tsx')
const card = read('src/workspaces/crm/contact-card/unified-contact-card.tsx')
const companyForm = read('src/app/workspaces/crm/_components/crm-company-form.tsx')
const companyDetail = read('src/app/workspaces/crm/_components/crm-company-detail.tsx')
const wizard = read('src/app/workspaces/crm/relationships/_components/relationship-create-wizard.tsx')
const relationships = read('src/app/workspaces/crm/relationships/_components/relationships-workspace.tsx')
const correction = read('src/app/workspaces/crm/relationships/_components/historical-correction-panel.tsx')
const relationshipApi = read('src/workspaces/crm/api/relationships.ts')
const leadRoutes = readRepo('apps/api/src/investhome_api/api/routes/crm_leads.py')
const activityRoutes = readRepo('apps/api/src/investhome_api/api/routes/crm_activities.py')
const companyRoutes = readRepo('apps/api/src/investhome_api/api/routes/crm_companies.py')
const companyService = readRepo('apps/api/src/investhome_api/services/crm_company_service.py')
const relationshipService = readRepo('apps/api/src/investhome_api/services/crm/relationship_service.py')
const permissions = readRepo('apps/api/src/investhome_api/config/permissions_config.py')

test('crm.create controls Create Lead and column add', () => {
  assert.match(leads, /data-testid="crm-leads-create"/)
  assert.match(leads, /data-testid="crm-leads-add-column"/)
  assert.match(leads, /\{canCreate \? \([\s\S]*?data-testid="crm-leads-create"/)
  assert.match(leads, /\{canCreate \? \([\s\S]*?data-testid="crm-leads-add-column"/)
  assert.match(leadRoutes, /def create_lead_workspace\([\s\S]{0,240}require_permission\("crm", "create"\)/)
  assert.doesNotMatch(leads, /canWrite/)
})

test('crm.update controls Lead edit', () => {
  assert.match(leads, /\{canUpdate && drawer !== 'convert'[\s\S]*?data-testid="crm-leads-edit"/)
  assert.match(leadRoutes, /def update_lead_workspace\([\s\S]{0,240}require_permission\("crm", "update"\)/)
})

test('crm.update controls stage drag', () => {
  assert.match(leads, /canDrag=\{canUpdate && item\.stage !== 'converted'\}/)
  assert.match(leads, /\{canUpdate && item\.stage !== 'converted' \?/)
  assert.match(leadRoutes, /def move_lead_stage\([\s\S]{0,240}require_permission\("crm", "update"\)/)
})

test('lead conversion uses the update permission required by its API', () => {
  assert.match(leadRoutes, /def convert_lead_workspace\([\s\S]{0,280}require_permission\("crm", "update"\)/)
  assert.match(leads, /\{canUpdate && selected\.stage !== 'converted' \?[\s\S]*?data-testid="crm-leads-convert"/)
  assert.doesNotMatch(leads, /\{canCreate && selected\.stage !== 'converted'/)
})

test('read-only user does not see tag write actions', () => {
  assert.match(tags, /const canUpdate = has\('update'\)/)
  assert.match(tags, /\{canCreate \? \([\s\S]*?data-testid="crm-tags-create"/)
  assert.match(tags, /\{canUpdate \?/)
  assert.doesNotMatch(tags, /canCreate \|\| has\('update'\)/)
  assert.doesNotMatch(tags, /canWrite/)
  assert.match(tags, /Etiketler yüklenemedi\. Yeniden deneyin\./)
  assert.doesNotMatch(tags, /tagsQuery\.error\.message/)
})

test('contact task permission matches its API', () => {
  assert.match(activityRoutes, /def post_task\([\s\S]{0,220}require_permission\("crm", "manage_tasks"\)/)
  assert.match(card, /const canManageTasks = has\('manage_tasks'\)/)
  assert.match(card, /\{canManageTasks \? \(\s*<button[\s\S]{0,220}data-testid="contact-task-action"/)
  assert.match(card, /data-testid="contact-task-side"/)
  assert.match(card, /data-testid="contact-task-tab"/)
  assert.doesNotMatch(card, /\{canUpdate \? \(\s*<button[\s\S]{0,220}data-testid="contact-task-action"/)
})

test('contact meeting permission matches its API', () => {
  assert.match(activityRoutes, /def post_meeting\([\s\S]{0,220}require_permission\("crm", "manage_meetings"\)/)
  assert.match(card, /const canManageMeetings = has\('manage_meetings'\)/)
  assert.match(card, /\{canManageMeetings \? \(\s*<button[\s\S]{0,280}data-testid="contact-meeting-action"/)
  assert.doesNotMatch(card, /canManageCrmMeetings/)
})

test('contact comment permission matches its API', () => {
  assert.match(activityRoutes, /def post_activity\([\s\S]{0,220}require_permission\("crm", "create"\)/)
  assert.match(card, /const canCreate = has\('create'\)/)
  assert.match(card, /\{canCreate \? \(\s*<button[\s\S]{0,280}data-testid="contact-comment-action"/)
  assert.match(activityRoutes, /def post_follow_up\([\s\S]{0,220}require_permission\("crm", "manage_followups"\)/)
  assert.match(card, /canManageFollowUps && noteNeedsFollowUp/)
})

test('company owner edit requires transfer ownership and uses the transfer endpoint', () => {
  assert.match(companyRoutes, /def update_company\([\s\S]{0,320}require_permission\("crm", "update"\)/)
  assert.match(companyRoutes, /def transfer_ownership\([\s\S]{0,280}require_permission\("crm", "transfer_ownership"\)/)
  assert.match(companyService, /if "owner_user_id" in data/)
  assert.match(companyService, /HTTP_403_FORBIDDEN/)
  assert.doesNotMatch(companyService, /"source",\s*"owner_user_id"/)
  assert.match(companyDetail, /const canTransferOwnership = has\('transfer_ownership'\)/)
  assert.match(companyDetail, /\{canTransferOwnership \? \([\s\S]*?data-testid="crm-company-owner"/)
  assert.match(companyDetail, /transferCrmCompanyOwnership/)
  assert.match(companyDetail, /crmCompaniesMutations\.update\(companyId\)/)
  assert.doesNotMatch(companyDetail, /\['owner_user_id', company\.owner_user_id\]/)
})

test('company duplicate warning requires an explicit user action', () => {
  assert.match(companyForm, /if \(!duplicateConfirmed\)/)
  assert.match(companyForm, /if \(outcome !== 'clear'\) return/)
  assert.match(companyForm, /data-testid="crm-company-duplicate-review"/)
  assert.match(companyForm, /data-testid="crm-company-duplicate-continue"/)
  assert.match(companyForm, /form\.duplicateReview/)
  assert.match(companyForm, /form\.duplicateContinue/)
})

test('company create uses the create API and does not pretend to edit', () => {
  assert.match(companyForm, /crmCompaniesMutations\.create\(\)/)
  assert.match(companyForm, /label=\{t\('form\.displayName'\)\}/)
  assert.match(companyForm, /fields\.companyType/)
  assert.match(companyForm, /label=\{tCrm\('fields\.email'\)\}/)
  assert.match(companyForm, /label=\{tCrm\('fields\.phone'\)\}/)
  assert.doesNotMatch(companyForm, /mode\?: 'create' \| 'edit'/)
  assert.doesNotMatch(companyForm, /crmCompaniesMutations\.update/)
})

test('company save-error and dirty protection from package 2 remain', () => {
  assert.match(companyForm, /setSaveError\(saveFailedMessage/)
  assert.match(companyForm, /data-testid="crm-company-form-error"/)
  assert.match(companyForm, /disabled=\{createMutation\.isPending\}/)
  assert.match(companyForm, /confirmDiscardUnsaved/)
  assert.doesNotMatch(companyForm, /if \(createMutation\.isPending\)/)
})

test('dirty relationship wizard warns before discard', () => {
  assert.match(wizard, /confirmDiscardUnsaved/)
  assert.match(wizard, /data-testid="crm-relationships-create-back"/)
  assert.match(wizard, /if \(!confirmLeave\(\)\) event\.preventDefault\(\)/)
})

test('relationship picker loading and error states render', () => {
  assert.match(wizard, /data-testid="crm-rel-picker-loading"/)
  assert.match(wizard, /data-testid="crm-rel-picker-error"/)
  assert.match(wizard, /data-testid="crm-rel-picker-empty"/)
  assert.match(wizard, /activeQuery\.refetch\(\)/)
  assert.doesNotMatch(wizard, /activeQuery\.error/)
})

test('duplicate relationship follows the backend forbid rule', () => {
  assert.match(relationshipService, /status_code=status\.HTTP_409_CONFLICT,\s*detail="Duplicate relationship exists"/)
  assert.match(wizard, /data-testid="crm-relationship-duplicate"/)
  assert.match(wizard, /\{copy\.openExisting\}/)
  assert.match(wizard, /if \(duplicates\.length > 0\)/)
  assert.match(wizard, /if \(!sourceId \|\| !targetId \|\| !selectedType \|\| duplicateWarning\) return/)
  assert.doesNotMatch(wizard, /duplicateContinue|Continue anyway|Yine de devam/)
  assert.doesNotMatch(wizard, /error\.message/)
})

test('relationship cancel works', () => {
  assert.match(wizard, /data-testid="crm-relationships-create-cancel"/)
  assert.match(wizard, /if \(confirmLeave\(\)\) router\.push\('\/workspaces\/crm\/relationships'\)/)
})

test('correct_relationships user sees the historical correction action', () => {
  assert.match(relationships, /has\('correct_relationships'\) \? <HistoricalCorrectionPanel \/> : null/)
  assert.match(correction, /data-testid="crm-historical-correction"/)
  assert.match(relationshipApi, /'\/crm\/corrections\/known\/preview'/)
  assert.match(relationshipApi, /'\/crm\/corrections\/known'/)
})

test('sales does not see the historical correction action', () => {
  const sales = permissions.slice(permissions.indexOf('"sales": ['), permissions.indexOf('"investor_relations": ['))
  assert.doesNotMatch(sales, /correct_relationships/)
  assert.doesNotMatch(relationships, /sales/)
  assert.match(relationships, /has\('correct_relationships'\)/)
})

test('preview is required before apply', () => {
  assert.match(correction, /enabled: false/)
  assert.match(correction, /previewKnownCorrections/)
  assert.match(correction, /disabled=\{!previewReady \|\| !preview\.data \|\| apply\.isPending\}/)
  assert.match(correction, /if \(!previewReady \|\| !preview\.data \|\| apply\.isPending\) return/)
})

test('apply requires explicit confirmation', () => {
  assert.match(correction, /if \(!window\.confirm\(copy\.confirm\)\) return;\s*apply\.mutate\(\)/)
  assert.match(correction, /applyKnownCorrections/)
  assert.doesNotMatch(correction, /apply\.mutate\(\)\s*$/m)
})
