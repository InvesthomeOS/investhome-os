import { stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dir = path.join(__dirname, '..', 'artifacts', 'finance-g5');
const req = [
  '01-executive-dashboard.png',
  '02-cash-position.png',
  '03-bank-accounts.png',
  '04-incoming-wires.png',
  '05-outgoing-wires.png',
  '06-investor-payments.png',
  '07-vendor-payments.png',
  '08-ar.png',
  '09-ap.png',
  '10-treasury.png',
  '11-forecast.png',
  '12-budget.png',
  '13-approvals.png',
  '14-documents.png',
  '15-audit.png',
  '16-tablet.png',
  '17-turkish.png',
  '18-english.png',
];

const sizes = {};
let ok = 0;
console.log('dir=', dir);
for (const n of req) {
  const s = (await stat(path.join(dir, n))).size;
  sizes[n] = s;
  const pass = s > 10_000;
  if (pass) ok += 1;
  console.log(`${pass ? 'OK' : 'FAIL'}\t${n}\t${s}`);
}
await writeFile(path.join(dir, 'sizes-verified.json'), JSON.stringify(sizes, null, 2));
console.log(`RESULT ${ok}/18`);
if (ok !== 18) process.exitCode = 1;
