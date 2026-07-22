/**
 * Audit CRM translation key usage vs en.json crm catalog.
 * Detects:
 * - missing leaves
 * - duplicate namespace prefixes (crm.crm.*)
 * - titleKey/descriptionKey composition mistakes under useTranslations('crm')
 * - object/string collisions (leaf used as object and string)
 *
 * Usage: node scripts/audit-crm-i18n-keys.mjs
 */
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const enPath = path.join(root, 'apps/web/messages/en.json');
const trPath = path.join(root, 'apps/web/messages/tr.json');
const en = JSON.parse(fs.readFileSync(enPath, 'utf8'));
const tr = JSON.parse(fs.readFileSync(trPath, 'utf8'));

function walkFiles(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walkFiles(full, out);
    else if (/\.(tsx|ts)$/.test(entry.name)) out.push(full);
  }
  return out;
}

const dirs = [
  path.join(root, 'apps/web/src/app/workspaces/crm'),
  path.join(root, 'apps/web/src/workspaces/crm'),
  path.join(root, 'apps/web/src/lib/crm'),
];
const files = dirs.flatMap((d) => walkFiles(d));

function getAt(obj, dotted) {
  return dotted.split('.').reduce((acc, k) => (acc == null ? undefined : acc[k]), obj);
}

function leafKeys(o, p = '', a = []) {
  for (const [k, v] of Object.entries(o || {})) {
    const n = p ? `${p}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) leafKeys(v, n, a);
    else a.push(n);
  }
  return a;
}

const used = new Set();
const doublePrefix = [];
const namespaceMisuse = [];
const collisions = [];

for (const file of files) {
  const content = fs.readFileSync(file, 'utf8');
  const rel = path.relative(root, file);
  const nsMatches = [...content.matchAll(/useTranslations\(\s*['"]([^'"]+)['"]\s*\)/g)].map((m) => m[1]);
  const crmNs = nsMatches.filter((n) => n === 'crm' || n.startsWith('crm.'));
  if (!crmNs.length && !/titleKey=|descriptionKey=/.test(content)) continue;

  const lines = content.split(/\r?\n/);
  /** @type {Record<string, string>} */
  const varToNs = {};
  for (const line of lines) {
    const assign = line.match(/const\s+(\w+)\s*=\s*useTranslations\(\s*['"]([^'"]+)['"]\s*\)/);
    if (assign && (assign[2] === 'crm' || assign[2].startsWith('crm.'))) {
      varToNs[assign[1]] = assign[2];
    }
  }

  for (const [varName, ns] of Object.entries(varToNs)) {
    const re = new RegExp(`\\b${varName}\\(\\s*['"\`]([a-zA-Z0-9_.]+)['"\`]`, 'g');
    for (const m of content.matchAll(re)) {
      const leaf = m[1];
      if (ns === 'crm' && leaf.startsWith('crm.')) {
        doublePrefix.push({ file: rel, ns, leaf, resolved: `crm.${leaf}` });
      }
      if (ns.startsWith('crm.') && leaf.startsWith('crm.')) {
        doublePrefix.push({ file: rel, ns, leaf, resolved: `${ns}.${leaf}` });
      }
      // communication + nav.* should live under crm.nav, not crm.communication.nav
      if (ns === 'crm.communication' && leaf.startsWith('nav.')) {
        namespaceMisuse.push({
          file: rel,
          ns,
          leaf,
          hint: 'Use useTranslations("crm.nav") for tools nav labels',
        });
      }
      const full = ns === 'crm' ? `crm.${leaf}` : `${ns}.${leaf}`;
      used.add(full.replace(/^crm\.crm\./, 'crm.crm.'));
      used.add(full);
    }
  }

  // CrmModuleShell titleKey/descriptionKey are relative to crm
  for (const m of content.matchAll(/(?:titleKey|descriptionKey)=\{?["']([^"']+)["']\}?/g)) {
    const key = m[1];
    if (key.startsWith('crm.')) {
      doublePrefix.push({
        file: rel,
        ns: 'crm (CrmModuleShell)',
        leaf: key,
        resolved: `crm.${key}`,
      });
    }
    used.add(`crm.${key.startsWith('crm.') ? key.slice(4) : key}`);
  }

  for (const m of content.matchAll(/labelKey:\s*['"]([a-zA-Z0-9_.]+)['"]/g)) {
    const key = m[1];
    // Only associate dotted keys (e.g. nav.dashboard) with the root crm namespace.
    // Bare keys (e.g. templates) are resolved by a dedicated translator in the same file.
    if (key.includes('.')) {
      used.add(`crm.${key}`);
    }
  }
}

const missing = [];
const present = [];
for (const key of [...used].sort()) {
  if (key.startsWith('crm.crm.')) {
    doublePrefix.push({ file: '(resolved)', ns: 'crm', leaf: key.slice(4), resolved: key });
    continue;
  }
  const pathInCrm = key.replace(/^crm\./, '');
  const val = getAt(en.crm, pathInCrm);
  if (val === undefined) missing.push(key);
  else if (typeof val === 'object' && val !== null) {
    collisions.push({ key, issue: 'path resolves to object, not a string leaf' });
  } else present.push(key);
}

// Catalog parity
const enLeaves = leafKeys(en.crm);
const trLeaves = leafKeys(tr.crm);
const missingTr = enLeaves.filter((k) => !trLeaves.includes(k));
const missingEn = trLeaves.filter((k) => !enLeaves.includes(k));

// Detect create string/object collision style keys at catalog level
const stringObjectCollisions = [];
function walkCollisions(obj, prefix = '') {
  for (const [k, v] of Object.entries(obj || {})) {
    const p = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      // if sibling leaf somehow — not applicable in JSON
      walkCollisions(v, p);
    }
  }
}
walkCollisions(en.crm);

const report = {
  filesScanned: files.length,
  usedKeys: used.size,
  presentLeaves: present.length,
  missingLeaves: missing.length,
  missingSample: missing.slice(0, 80),
  missingAll: missing,
  doublePrefixCount: doublePrefix.length,
  doublePrefixSample: doublePrefix.slice(0, 40),
  namespaceMisuseCount: namespaceMisuse.length,
  namespaceMisuse,
  objectPathCollisions: collisions,
  catalogParity: {
    enLeaves: enLeaves.length,
    trLeaves: trLeaves.length,
    missingTr: missingTr.length,
    missingEn: missingEn.length,
  },
  stringObjectCollisions,
  ok:
    missing.length === 0 &&
    doublePrefix.length === 0 &&
    namespaceMisuse.length === 0 &&
    collisions.length === 0 &&
    missingTr.length === 0 &&
    missingEn.length === 0,
};

console.log(JSON.stringify(report, null, 2));
fs.writeFileSync(path.join(root, '.tmp-crm-missing-keys.json'), `${JSON.stringify(report, null, 2)}\n`);
if (!report.ok) process.exit(1);
