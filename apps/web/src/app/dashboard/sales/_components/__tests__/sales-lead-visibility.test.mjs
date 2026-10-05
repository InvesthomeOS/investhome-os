/**
 * Sales lead visibility, KPI exclusivity, empty states, website source, and activity i18n.
 * Run: node --test src/app/dashboard/sales/_components/__tests__/sales-lead-visibility.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '../../../../../../');
const workspace = readFileSync(join(here, '../sales-workspace.tsx'), 'utf8');
const leadTable = readFileSync(join(here, '../sales-lead-table.tsx'), 'utf8');
const tr = JSON.parse(readFileSync(join(webRoot, 'messages/tr.json'), 'utf8'));
const en = JSON.parse(readFileSync(join(webRoot, 'messages/en.json'), 'utf8'));
const salesApi = readFileSync(join(webRoot, 'src/lib/api/sales.ts'), 'utf8');
const activityLabels = readFileSync(join(webRoot, 'src/lib/i18n/activity-labels.ts'), 'utf8');
const leadSource = readFileSync(join(webRoot, 'src/lib/i18n/lead-source.ts'), 'utf8');
const visibility = readFileSync(join(webRoot, 'src/lib/sales/lead-visibility.ts'), 'utf8');

const NEW_LEAD_STATUS = 'New';
const QUALIFIED_LEAD_STATUS = 'Qualified';

function isNewLeadStatus(status) {
  return status === NEW_LEAD_STATUS;
}

function isQualifiedLeadStatus(status) {
  return status === QUALIFIED_LEAD_STATUS;
}

function countSalesLeadKpis(leads) {
  let new_leads = 0;
  let qualified_leads = 0;
  for (const lead of leads) {
    if (isNewLeadStatus(lead.status)) {
      new_leads += 1;
      continue;
    }
    if (isQualifiedLeadStatus(lead.status)) {
      qualified_leads += 1;
    }
  }
  return { new_leads, qualified_leads };
}

function leadMatchesSalesLeadList(lead, statusFilter) {
  if (!statusFilter) return true;
  return lead.status === statusFilter;
}

function newLeadHasOpportunity(leadId, opportunities) {
  return opportunities.some((item) => item.lead_id === leadId || item.party_id === leadId);
}

function salesPipelinePresentation(loading, opportunityCount) {
  if (loading && opportunityCount === 0) return 'skeleton';
  if (opportunityCount === 0) return 'empty';
  return 'content';
}

function leadSourceCatalogKey(source) {
  if (!source?.trim()) return null;
  const normalized = source.trim().toLowerCase().replace(/[\s-]+/g, '_');
  const aliases = { website: 'website', web_site_form: 'website', website_form: 'website' };
  const aliased = aliases[normalized] ?? normalized;
  const known = new Set(['website', 'referral', 'exhibition', 'linkedin', 'partner', 'cold_outreach']);
  return known.has(aliased) ? aliased : null;
}

function activityDescriptionPath(descriptionKey) {
  const normalized = descriptionKey.startsWith('activity.')
    ? descriptionKey.slice('activity.'.length)
    : descriptionKey;
  return `descriptions.${normalized}`;
}

const websiteLead = {
  id: 'lead-new-1',
  full_name: 'Ayşe Yılmaz',
  email: 'ayse@example.com',
  phone: '05551234567',
  source: 'website',
  status: 'New',
  interested_project: '1812 H Place',
};

describe('sales lead visibility', () => {
  it('shows a NEW lead in the lead list and not as an opportunity before conversion', () => {
    const leads = [websiteLead, { id: 'lead-q', status: 'Qualified' }];
    assert.equal(leadMatchesSalesLeadList(websiteLead, ''), true);
    assert.equal(leadMatchesSalesLeadList(websiteLead, 'New'), true);
    assert.equal(leadMatchesSalesLeadList(websiteLead, 'Qualified'), false);
    assert.equal(newLeadHasOpportunity(websiteLead.id, []), false);
    assert.equal(
      newLeadHasOpportunity(websiteLead.id, [{ id: 'opp-1', lead_id: websiteLead.id, party_id: websiteLead.id }]),
      true,
    );
    assert.match(workspace, /view === 'leads'/);
    assert.match(workspace, /t\('views\.leads'\)/);
    assert.match(leadTable, /getSourceLabel\(lead\.source\)/);
    assert.match(leadTable, /tLeads\('table\.created'\)/);
    assert.equal(tr.leads.table.created, 'Oluşturma Tarihi');
    assert.equal(en.leads.table.created, 'Created Date');
    assert.doesNotMatch(workspace, /window\.location\.href = '\/dashboard\/leads'/);
  });

  it('does not count a NEW lead as qualified', () => {
    const counts = countSalesLeadKpis([
      websiteLead,
      { status: 'New' },
      { status: 'Qualified' },
      { status: 'Contacted' },
    ]);
    assert.equal(counts.new_leads, 2);
    assert.equal(counts.qualified_leads, 1);
    assert.equal(countSalesLeadKpis([{ status: 'New' }]).qualified_leads, 0);
    assert.match(visibility, /if \(isNewLeadStatus\(lead\.status\)\) \{\s*new_leads \+= 1;\s*continue;/s);
    assert.match(salesApi, /countSalesLeadKpis\(allLeads\.items\)/);
  });

  it('renders the zero-opportunity empty state instead of a skeleton', () => {
    assert.equal(salesPipelinePresentation(true, 0), 'skeleton');
    assert.equal(salesPipelinePresentation(false, 0), 'empty');
    assert.equal(salesPipelinePresentation(true, 2), 'content');
    assert.equal(salesPipelinePresentation(false, 2), 'content');
    assert.match(workspace, /t\('emptyOpportunities'\)/);
    assert.equal(tr.sales.emptyOpportunities, 'Henüz aktif satış fırsatı yok.');
    assert.match(workspace, /salesPipelinePresentation\(loading, opportunities\.length\)/);
  });

  it('renders website source as Web Sitesi from the i18n catalog', () => {
    assert.equal(leadSourceCatalogKey('website'), 'website');
    assert.equal(leadSourceCatalogKey('Website'), 'website');
    assert.equal(tr.leads.sources.website, 'Web Sitesi');
    assert.equal(en.leads.sources.website, 'Website');
    assert.match(leadSource, /SOURCE_ALIASES/);
    assert.match(readFileSync(join(webRoot, 'src/lib/i18n/lead-labels.ts'), 'utf8'), /leadSourceCatalogKey/);
  });

  it('resolves the website form activity key to Turkish and English copy', () => {
    const path = activityDescriptionPath('crm.leads.website_form.received');
    assert.equal(path, 'descriptions.crm.leads.website_form.received');
    assert.equal(tr.activity.descriptions.crm.leads.website_form.received, 'Web sitesi formu alındı');
    assert.equal(en.activity.descriptions.crm.leads.website_form.received, 'Website form received');
    assert.match(activityLabels, /descriptions\.\$\{normalized\}/);
  });
});
