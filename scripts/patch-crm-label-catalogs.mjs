import fs from 'node:fs';

const enPath = 'apps/web/messages/en.json';
const trPath = 'apps/web/messages/tr.json';
const en = JSON.parse(fs.readFileSync(enPath, 'utf8'));
const tr = JSON.parse(fs.readFileSync(trPath, 'utf8'));

const EN_EVENTS = {
  unknown: 'Activity update',
  'lead.created': 'Lead created',
  'lead.updated': 'Lead updated',
  'lead.archived': 'Lead archived',
  'investor.created': 'Investor created',
  'investor.updated': 'Investor updated',
  'contact.created': 'Contact created',
  'contact.updated': 'Contact updated',
  'contact.archived': 'Contact archived',
  'company.created': 'Company created',
  'company.updated': 'Company updated',
  'relationship.created': 'Relationship created',
  'relationship.updated': 'Relationship updated',
  'note.created': 'Note created',
  'task.created': 'Task created',
  'task.updated': 'Task updated',
  'task.completed': 'Task completed',
  'status.changed': 'Status changed',
  'communication.sent': 'Communication sent',
  'project.created': 'Project created',
  'project.updated': 'Project updated',
  'project.archived': 'Project archived',
};

const TR_EVENTS = {
  unknown: 'Aktivite güncellemesi',
  'lead.created': 'Potansiyel müşteri oluşturuldu',
  'lead.updated': 'Potansiyel müşteri güncellendi',
  'lead.archived': 'Potansiyel müşteri arşivlendi',
  'investor.created': 'Yatırımcı oluşturuldu',
  'investor.updated': 'Yatırımcı güncellendi',
  'contact.created': 'Kişi oluşturuldu',
  'contact.updated': 'Kişi güncellendi',
  'contact.archived': 'Kişi arşivlendi',
  'company.created': 'Şirket oluşturuldu',
  'company.updated': 'Şirket güncellendi',
  'relationship.created': 'İlişki oluşturuldu',
  'relationship.updated': 'İlişki güncellendi',
  'note.created': 'Not oluşturuldu',
  'task.created': 'Görev oluşturuldu',
  'task.updated': 'Görev güncellendi',
  'task.completed': 'Görev tamamlandı',
  'status.changed': 'Durum değişti',
  'communication.sent': 'İletişim gönderildi',
  'project.created': 'Proje oluşturuldu',
  'project.updated': 'Proje güncellendi',
  'project.archived': 'Proje arşivlendi',
};

const EN_REL_TYPES = {
  colleague: 'Colleague',
  partner: 'Partner',
  parent: 'Parent',
  subsidiary: 'Subsidiary',
  client: 'Client',
  vendor: 'Vendor',
  referred_by: 'Referred by',
  referred_to: 'Referred to',
  investor: 'Investor',
  advisor: 'Advisor',
  employs: 'Employs',
  employed_by: 'Employed by',
  other: 'Other',
  investee: 'Investee',
  advisee: 'Advisee',
};

const TR_REL_TYPES = {
  colleague: 'Meslektaş',
  partner: 'İş ortağı',
  parent: 'Ana',
  subsidiary: 'Bağlı şirket',
  client: 'Müşteri',
  vendor: 'Tedarikçi',
  referred_by: 'Yönlendiren',
  referred_to: 'Yönlendirilen',
  investor: 'Yatırımcı',
  advisor: 'Danışman',
  employs: 'İstihdam eder',
  employed_by: 'İstihdam edilir',
  other: 'Diğer',
  investee: 'Yatırım yapılan',
  advisee: 'Danışılan',
};

const EN_REL_CATS = {
  organizational: 'Organizational',
  commercial: 'Commercial',
  personal: 'Personal',
  referral: 'Referral',
  investment: 'Investment',
  operational: 'Operational',
  other: 'Other',
};

const TR_REL_CATS = {
  organizational: 'Kurumsal',
  commercial: 'Ticari',
  personal: 'Kişisel',
  referral: 'Yönlendirme',
  investment: 'Yatırım',
  operational: 'Operasyonel',
  other: 'Diğer',
};

const EN_STRENGTH = { weak: 'Weak', moderate: 'Moderate', strong: 'Strong', strategic: 'Strategic' };
const TR_STRENGTH = { weak: 'Zayıf', moderate: 'Orta', strong: 'Güçlü', strategic: 'Stratejik' };

en.crm.activityEvents = { ...(en.crm.activityEvents || {}), ...EN_EVENTS };
tr.crm.activityEvents = { ...(tr.crm.activityEvents || {}), ...TR_EVENTS };
en.crm.relationships.types = { ...(en.crm.relationships.types || {}), ...EN_REL_TYPES };
tr.crm.relationships.types = { ...(tr.crm.relationships.types || {}), ...TR_REL_TYPES };
en.crm.relationships.categories = { ...(en.crm.relationships.categories || {}), ...EN_REL_CATS };
tr.crm.relationships.categories = { ...(tr.crm.relationships.categories || {}), ...TR_REL_CATS };
en.crm.relationships.strengths = { ...(en.crm.relationships.strengths || {}), ...EN_STRENGTH };
tr.crm.relationships.strengths = { ...(tr.crm.relationships.strengths || {}), ...TR_STRENGTH };

function leaves(o) {
  let n = 0;
  for (const v of Object.values(o || {})) {
    if (v && typeof v === 'object' && !Array.isArray(v)) n += leaves(v);
    else n += 1;
  }
  return n;
}
function keys(o, p = '', a = []) {
  for (const [k, v] of Object.entries(o || {})) {
    const n = p ? `${p}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) keys(v, n, a);
    else a.push(n);
  }
  return a;
}
const ek = keys(en.crm);
const tk = keys(tr.crm);
const missingTr = ek.filter((k) => !tk.includes(k));
const missingEn = tk.filter((k) => !ek.includes(k));
if (missingTr.length || missingEn.length) {
  console.error({ missingTr: missingTr.slice(0, 20), missingEn: missingEn.slice(0, 20) });
  process.exit(1);
}
fs.writeFileSync(enPath, `${JSON.stringify(en, null, 2)}\n`);
fs.writeFileSync(trPath, `${JSON.stringify(tr, null, 2)}\n`);
console.log(JSON.stringify({ enLeaves: leaves(en.crm), trLeaves: leaves(tr.crm) }, null, 2));
