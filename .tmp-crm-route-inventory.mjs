import fs from 'node:fs';
import path from 'node:path';

const root = 'apps/web/src/app/workspaces/crm';

function walk(dir, acc = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, acc);
    else if (entry.name === 'page.tsx') acc.push(full);
  }
  return acc;
}

const pages = walk(root).sort();
const rows = pages.map((file) => {
  const posix = file.split(path.sep).join('/');
  const url = posix
    .replace('apps/web/src/app', '')
    .replace(/\/page\.tsx$/, '')
    .replace(/\[([^\]]+)\]/g, ':$1');
  const src = fs.readFileSync(file, 'utf8');
  const namespaces = [...src.matchAll(/useTranslations\(['`]([^'`]+)['`]\)/g)].map((m) => m[1]);
  const importsComponent = [...src.matchAll(/from ['"](\.[^'"]+)['"]/g)].map((m) => m[1]);
  return { url, file: posix, namespaces, importsComponent };
});

fs.writeFileSync('.tmp-crm-route-inventory.json', JSON.stringify(rows, null, 2));
console.log(JSON.stringify({ count: rows.length, urls: rows.map((r) => r.url) }, null, 2));
