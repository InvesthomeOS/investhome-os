import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const enPath = path.join(root, 'apps/web/messages/en.json');
const trPath = path.join(root, 'apps/web/messages/tr.json');
const en = JSON.parse(fs.readFileSync(enPath, 'utf8'));
const tr = JSON.parse(fs.readFileSync(trPath, 'utf8'));

en.marketing.analytics.tableColumns = {
  name: 'Name',
  category: 'Category',
  connectionStatus: 'Connection status',
  status: 'Status',
};
tr.marketing.analytics.tableColumns = {
  name: 'Ad',
  category: 'Kategori',
  connectionStatus: 'Bağlantı durumu',
  status: 'Durum',
};

en.marketing.channels.social.fields = {
  title: 'Title',
  body: 'Body',
  saveDraft: 'Save draft',
};
tr.marketing.channels.social.fields = {
  title: 'Başlık',
  body: 'Gövde',
  saveDraft: 'Taslağı kaydet',
};

en.marketing.email = en.marketing.email || {};
tr.marketing.email = tr.marketing.email || {};
en.marketing.email.detail = {
  deliverability: 'Deliverability',
  subject: 'Subject',
  unsubscribeRequired: 'Unsubscribe required',
  unsubscribeLinkPresent: 'Unsubscribe link present',
  readinessChecklist: 'Readiness checklist',
};
tr.marketing.email.detail = {
  deliverability: 'Teslim edilebilirlik',
  subject: 'Konu',
  unsubscribeRequired: 'Abonelikten çıkış gerekli',
  unsubscribeLinkPresent: 'Abonelikten çıkış bağlantısı mevcut',
  readinessChecklist: 'Hazırlık kontrol listesi',
};

// Fix dashboard.audiences / leads that were left English
tr.marketing.dashboard.audiences = 'Kitleler';
tr.marketing.dashboard.leads = 'Lead Bağlamları';
tr.marketing.dashboard.campaigns = tr.marketing.dashboard.campaigns || 'Kampanyalar';

fs.writeFileSync(enPath, `${JSON.stringify(en, null, 2)}\n`);
fs.writeFileSync(trPath, `${JSON.stringify(tr, null, 2)}\n`);
console.log('patched keys');
