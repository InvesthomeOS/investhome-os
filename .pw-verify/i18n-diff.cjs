const fs = require('fs');
const en = JSON.parse(fs.readFileSync('apps/web/messages/en.json', 'utf8')).marketing;
const tr = JSON.parse(fs.readFileSync('apps/web/messages/tr.json', 'utf8')).marketing;

function flatten(obj, prefix = '') {
  const keys = [];
  for (const [k, v] of Object.entries(obj || {})) {
    const p = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) keys.push(...flatten(v, p));
    else keys.push(p);
  }
  return keys;
}

const enKeys = new Set(flatten(en));
const trKeys = new Set(flatten(tr));
const missing = [...enKeys].filter((k) => !trKeys.has(k)).sort();
const extra = [...trKeys].filter((k) => !enKeys.has(k)).sort();

console.log('EN keys:', enKeys.size);
console.log('TR keys:', trKeys.size);
console.log('Missing in TR:', missing.length);
console.log('Extra in TR:', extra.length);

const groups = {};
for (const k of missing) {
  const top = k.split('.')[0];
  (groups[top] ||= []).push(k);
}
console.log('\n=== Missing top-level trees ===');
for (const [top, arr] of Object.entries(groups).sort()) {
  console.log(`${top}: ${arr.length} keys`);
}
console.log('\n=== Full missing key list ===');
for (const k of missing) console.log(k);
