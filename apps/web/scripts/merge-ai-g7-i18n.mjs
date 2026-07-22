import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(__dirname, '..');
const g7Dir = path.join(webRoot, 'src/app/dashboard/ai/_components/g7');
const messagesDir = path.join(webRoot, 'messages');

for (const locale of ['en', 'tr']) {
  const catalogPath = path.join(messagesDir, `${locale}.json`);
  const g7Path = path.join(g7Dir, `i18n-${locale}.json`);
  const catalog = JSON.parse(readFileSync(catalogPath, 'utf8'));
  const g7 = JSON.parse(readFileSync(g7Path, 'utf8'));
  if (!catalog.ai) catalog.ai = {};
  catalog.ai.g7 = g7;
  writeFileSync(catalogPath, `${JSON.stringify(catalog, null, 2)}\n`, 'utf8');
  console.log(`Merged ai.g7 into ${locale}.json`);
}
