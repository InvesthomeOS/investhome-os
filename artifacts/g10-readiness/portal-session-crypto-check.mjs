import { createHmac, timingSafeEqual } from 'crypto';
import assert from 'assert';

const secret = 'test-portal-secret-for-g10-audit-32b';
const payload = {
  investorId: 'portal-inv-a',
  email: 'investor.a@investhome.demo',
  issuedAt: new Date().toISOString(),
};
const payloadJson = JSON.stringify(payload);
const body = Buffer.from(payloadJson, 'utf8').toString('base64url');
const sig = createHmac('sha256', secret).update(payloadJson).digest('base64url');
const token = `${body}.${sig}`;

function decode(raw, sec) {
  const dot = raw.indexOf('.');
  if (dot <= 0) return null;
  const b = raw.slice(0, dot);
  const s = raw.slice(dot + 1);
  const json = Buffer.from(b, 'base64url').toString('utf8');
  const expected = createHmac('sha256', sec).update(json).digest('base64url');
  const a = Buffer.from(s);
  const e = Buffer.from(expected);
  if (a.length !== e.length || !timingSafeEqual(a, e)) return null;
  return JSON.parse(json);
}

assert.ok(token.includes('.'));
assert.deepEqual(decode(token, secret).investorId, 'portal-inv-a');
assert.equal(decode(body, secret), null, 'unsigned rejected');
const forgedBody = Buffer.from(
  JSON.stringify({ ...payload, investorId: 'portal-inv-b' }),
  'utf8',
).toString('base64url');
assert.equal(decode(`${forgedBody}.${sig}`, secret), null, 'forged payload rejected');
console.log('portal-session-crypto: PASS');
