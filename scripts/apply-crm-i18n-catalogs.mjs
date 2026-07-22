/**
 * Merge CRM EN/TR base + supplements into apps/web/messages/{en,tr}.json
 */
import fs from 'node:fs';
import path from 'node:path';
import { EN_SUPPLEMENT, TR_SUPPLEMENT, mergeSupplement } from './crm-i18n-missing-supplement.mjs';

const root = path.resolve(import.meta.dirname, '..');
const enPath = path.join(root, 'apps/web/messages/en.json');
const trPath = path.join(root, 'apps/web/messages/tr.json');
const enCrmBase = JSON.parse(fs.readFileSync(path.join(root, '.tmp-crm-en.json'), 'utf8'));
const trCrmBase = JSON.parse(fs.readFileSync(path.join(root, '.tmp-crm-tr.json'), 'utf8'));

const en = JSON.parse(fs.readFileSync(enPath, 'utf8'));
const tr = JSON.parse(fs.readFileSync(trPath, 'utf8'));

en.crm = mergeSupplement(enCrmBase, EN_SUPPLEMENT);
tr.crm = mergeSupplement(trCrmBase, TR_SUPPLEMENT);

function leafCount(o) {
  let n = 0;
  for (const v of Object.values(o || {})) {
    if (v && typeof v === 'object' && !Array.isArray(v)) n += leafCount(v);
    else n += 1;
  }
  return n;
}

function leafKeys(o, p = '', a = []) {
  for (const [k, v] of Object.entries(o || {})) {
    const n = p ? `${p}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) leafKeys(v, n, a);
    else a.push(n);
  }
  return a;
}

const enKeys = leafKeys(en.crm);
const trKeys = leafKeys(tr.crm);
const missingTr = enKeys.filter((k) => !trKeys.includes(k));
const missingEn = trKeys.filter((k) => !enKeys.includes(k));

if (missingTr.length || missingEn.length) {
  console.error('PARITY FAIL', { missingTr: missingTr.slice(0, 20), missingEn: missingEn.slice(0, 20) });
  process.exit(1);
}

fs.writeFileSync(enPath, `${JSON.stringify(en, null, 2)}\n`, 'utf8');
fs.writeFileSync(trPath, `${JSON.stringify(tr, null, 2)}\n`, 'utf8');

console.log(
  JSON.stringify(
    {
      enLeaves: leafCount(en.crm),
      trLeaves: leafCount(tr.crm),
      parity: true,
      wrote: [enPath, trPath],
    },
    null,
    2,
  ),
);
