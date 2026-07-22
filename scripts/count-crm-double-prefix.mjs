import fs from 'node:fs';
import path from 'node:path';

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (/\.(tsx|ts)$/.test(entry.name)) out.push(full);
  }
  return out;
}

const files = walk('apps/web/src/app/workspaces/crm');
let hits = [];
for (const file of files) {
  const s = fs.readFileSync(file, 'utf8');
  for (const m of s.matchAll(/(?:titleKey|descriptionKey)=["'](crm\.[^"']+)["']/g)) {
    hits.push({ file, key: m[1] });
  }
  for (const m of s.matchAll(/\bt\(\s*['`]crm\./g)) {
    hits.push({ file, key: m[0] });
  }
}
console.log(JSON.stringify({ count: hits.length, hits }, null, 2));
